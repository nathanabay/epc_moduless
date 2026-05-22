"""
BOQ Importer for Arat Kilo Building Construction Project.
Parses the bid BOQ CSV and imports into the Custom BOQ doctype.
"""

import frappe
import csv
import re
import os
from frappe import _
from epc_modules.utils import get_epc_logger

logger = get_epc_logger(__name__)


class AratKiloBOQImporter:
    """Parser and importer for Arat Kilo BOQ CSV."""

    COL_ITEM_NO = 0
    COL_DESC = 1
    COL_UNIT = 2
    COL_QTY = 3
    COL_RATE = 4
    COL_TOTAL = 5

    SECTION_MAP = {
        "01": {"name": "Demolishing Work", "wbs_prefix": "DEMO"},
        "02": {"name": "Excavation & Earth Work", "wbs_prefix": "EXCV"},
        "03": {"name": "Concrete Work - Sub Structure", "wbs_prefix": "CONS-SUB"},
        "04": {"name": "Concrete Work - Super Structure", "wbs_prefix": "CONS-SUP"},
        "05": {"name": "Block Works", "wbs_prefix": "BLKW"},
        "06": {"name": "Thermal & Moisture Protection", "wbs_prefix": "THRM"},
    }

    def __init__(self):
        self.items = []
        self.current_section = None

    def parse_csv(self, csv_path):
        """Parse the BOQ CSV file and return a list of BOQ items."""
        # Path traversal protection: validate path stays within site directory
        if not csv_path:
            frappe.throw(_("File path is required"))
        csv_path = os.path.realpath(csv_path)
        site_path = os.path.realpath(frappe.get_site_path())
        if not csv_path.startswith(site_path):
            frappe.throw(_("Invalid file path: path escapes site directory"))
        if not csv_path.endswith('.csv'):
            frappe.throw(_("Only CSV files are allowed"))
        logger.info(f"Parsing BOQ CSV: {csv_path}")
        items = []
        current_section = None
        idx = 0

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        for row_idx, row in enumerate(rows):
            if row_idx < 7:
                continue  # Skip project header

            if len(row) < 6:
                continue

            item_no = self._clean(row[self.COL_ITEM_NO])
            description = self._clean(row[self.COL_DESC])
            unit = self._clean(row[self.COL_UNIT])
            qty = self._parse_num(row[self.COL_QTY])
            rate = self._parse_num(row[self.COL_RATE])
            total = self._parse_num(row[self.COL_TOTAL])

            # Detect section headers in description column (e.g., "01) DEMOLISHING WORK", "A-SUB STRUCTURE")
            section_match = re.match(r'^\s*0?(\d+)\)', description)
            if section_match:
                section_id = section_match.group(1).zfill(2)
                if section_id in self.SECTION_MAP:
                    current_section = section_id
                continue

            # Also check for section patterns like "02. EXCAVATION & EARTH WORK"
            section_pattern_match = re.match(r'^(\d+)\.\s+[A-Z]', description, re.IGNORECASE)
            if section_pattern_match and not qty:
                section_id = section_pattern_match.group(1).zfill(2)
                if section_id in self.SECTION_MAP:
                    current_section = section_id
                continue

            # Handle sub-items: extract the sub-item letter from description when item_no is "a)" or "b)"
            sub_item_letter = None
            if qty is not None and not item_no:
                sub_match = re.match(r'^([a-z])\)\s*(.*)', description)
                if sub_match:
                    sub_item_letter = sub_match.group(1).lower()
                    # Keep description as-is (it's the actual description, not just sub-item label)

            # Skip subsection headers (numeric item_no with no qty, like "3.02")
            if item_no:
                subsection_match = re.match(r'^(\d+\.\d+)\s*,?\s*(.*)', item_no)
                if subsection_match and not qty:
                    continue

            # Skip rows without valid description
            if not description or description in ("Description", "Total Carried To Summary", ""):
                continue

            if "Total Carried To Summary" in description:
                continue

            if qty is None:
                continue

            # Build item_no and wbs_code
            if item_no:
                parsed_item_no = self._parse_item_no(item_no, description, qty)
            elif sub_item_letter:
                parsed_item_no = sub_item_letter
            else:
                parsed_item_no = self._parse_item_no(item_no, description, qty)

            # Skip rows that look like description continuations (no item_no, starts with lowercase or "material")
            if not item_no and not sub_item_letter and parsed_item_no is None:
                # Description-only rows without item number - these are sub-descriptions or section details
                if description.startswith(('material', 'Responsibility', 'Testing')):
                    continue
                # Also skip rows where item_no is empty AND description starts with uppercase letter
                # but parsed_item_no is None (no numeric pattern found) - these are section-level descriptions
                if re.match(r'^[A-Z]', description) and not re.search(r'\d', description[:20]):
                    continue
                # Skip rows with description but no identifiable item_no and no qty was set
                if not description[0].isdigit() if description else True:
                    continue

            # Must have a valid item_no or sub_item_letter
            if not parsed_item_no:
                continue

            wbs_code = self._generate_wbs_code(current_section, parsed_item_no)
            wbs_name = description[:100] if description else ""

            item = {
                "idx": idx,
                "item_no": parsed_item_no,
                "description": description[:500],
                "unit": unit or "NOS",
                "qty": qty,
                "rate": rate if rate and rate > 0 else 0,
                "total": total if total and total > 0 else (qty * rate if qty and rate else 0),
                "section": current_section,
                "wbs_code": wbs_code,
                "wbs_name": wbs_name,
            }
            items.append(item)
            idx += 1

        logger.info(f"Parsed {len(items)} BOQ items from CSV")
        self.items = items
        return items

    def _clean(self, val):
        if not val:
            return ""
        return " ".join(val.split()).strip()

    def _parse_num(self, val):
        if not val:
            return None
        cleaned = re.sub(r'[ETB,₣$\s]', '', str(val).strip())
        if cleaned in ('', '-', '—'):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_item_no(self, item_no, description, qty=None):
        if not item_no:
            return None

        item_no = item_no.strip()

        # Handle sub-items like "a)", "b)" (from item_no column when no qty)
        sub_match = re.match(r'^([a-z])\)\s*$', item_no, re.IGNORECASE)
        if sub_match and not qty:
            return sub_match.group(1).lower()

        # Handle main items like "2.6", "3.01"
        match = re.match(r'^(\d+\.\d+\.?\d*|\d+\.\d+)', item_no)
        if match:
            return match.group(1)

        return item_no if item_no else None

    def _generate_wbs_code(self, section, item_no):
        if not section or section not in self.SECTION_MAP:
            return "MISC"
        prefix = self.SECTION_MAP[section]["wbs_prefix"]

        if item_no:
            # Check if it's a sub-item letter (a, b, c, etc.)
            if re.match(r'^[a-z]$', item_no, re.IGNORECASE):
                return f"{prefix}-{item_no.lower()}"

            # Extract numeric parts from item_no
            item_id = re.sub(r'[^\d.]', '', item_no)
            if item_id:
                parts = item_id.split('.')
                if len(parts) == 2:
                    return f"{prefix}-{parts[0]}{parts[1].zfill(2)}"
                elif len(parts) >= 3:
                    return f"{prefix}-{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
        return prefix

    def import_to_project(self, project_name, items=None):
        """Import parsed items into Custom BOQ doctype."""
        if not frappe.db.exists("Project", project_name):
            raise ValueError(f"Project {project_name} does not exist")

        if items is None:
            items = self.items

        # Check create permission once before the loop
        frappe.has_permission("Custom BOQ", "create", throw=True)

        imported = []
        errors = []
        total_value = 0

        for item in items:
            try:
                # Derive parent_wbs from wbs_code: "DEMO-01" -> "DEMO", "CONS-SUB-a" -> "CONS-SUB"
                wbs_code = item.get("wbs_code", "")
                if wbs_code and "-" in wbs_code:
                    parent_wbs = wbs_code.rsplit("-", 1)[0]
                else:
                    parent_wbs = None

                # Validate required fields before insert
                if not item.get("item_no"):
                    raise ValueError("Missing item_no in BOQ item")
                if item.get("qty") is None:
                    raise ValueError("Missing quantity (qty) in BOQ item")

                doc = frappe.get_doc({
                    "doctype": "Custom BOQ",
                    "parent": project_name,
                    "parent_wbs": parent_wbs,
                    "item_code": item["item_no"],
                    "description": item["description"],
                    "boq_quantity": item["qty"],
                    "uom": item["unit"],
                    "unit_rate": item["rate"],
                    "total_value": item["total"],
                    "wbs_code": wbs_code,
                    "measurement_method": "Unit-Based",
                })
                try:
                    doc.insert()
                except frappe.PermissionError:
                    logger.error(f"Permission denied importing BOQ item {item.get('item_no')} for project {project_name}")
                    raise
                total_value += item["total"]
                imported.append(item["item_no"])
            except frappe.PermissionError:
                errors.append({"item": item.get("item_no"), "error": "Permission denied"})
                logger.warning(f"Permission denied importing BOQ item {item.get('item_no')}")
            except Exception as e:
                errors.append({"item": item.get("item_no"), "error": str(e)})
                logger.warning(f"Failed to import BOQ item {item.get('item_no')}: {e}")

        logger.info(f"Imported {len(imported)} BOQ items, {len(errors)} errors, total: {total_value}")
        return {
            "project": project_name,
            "count": len(imported),
            "errors": len(errors),
            "error_details": errors,
            "total_value": total_value
        }