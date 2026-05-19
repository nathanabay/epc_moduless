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

            # Detect section headers
            section_match = re.match(r'^\s*0?(\d+)\)', description)
            if section_match and not item_no:
                section_id = section_match.group(1).zfill(2)
                if section_id in self.SECTION_MAP:
                    current_section = section_id
                continue

            # Also check for section patterns like "3. CONCRETE WORK"
            section_pattern_match = re.match(r'^(\d+)\.\s+[A-Z]', description, re.IGNORECASE)
            if section_pattern_match and not qty:
                section_id = section_pattern_match.group(1).zfill(2)
                if section_id in self.SECTION_MAP:
                    current_section = section_id
                continue

            # Skip subsection headers without quantities
            subsection_match = re.match(r'^(\d+\.\d+)\s*,?\s*(.*)', item_no or description)
            if subsection_match and not qty:
                continue

            # Skip rows without valid description
            if not description or description in ("Description", "Total Carried To Summary", ""):
                continue

            if "Total Carried To Summary" in description:
                continue

            parsed_item_no = self._parse_item_no(item_no, description)

            if parsed_item_no and qty is not None:
                item = {
                    "idx": idx,
                    "item_no": parsed_item_no,
                    "description": description[:500],
                    "unit": unit or "NOS",
                    "qty": qty,
                    "rate": rate if rate and rate > 0 else 0,
                    "total": total if total and total > 0 else (qty * rate if qty and rate else 0),
                    "section": current_section,
                    "wbs_code": self._generate_wbs_code(current_section, parsed_item_no),
                    "wbs_name": description[:100],
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

    def _parse_item_no(self, item_no, description):
        if not item_no:
            # Try to extract from description
            match = re.match(r'^(\d+\.\d+\.?\d*)\s*,?\s*(.*)', description)
            if match:
                return match.group(1)
            match = re.match(r'^(\d+\.\d+)\s*,?\s*(.*)', description)
            if match:
                return match.group(1)
            return None

        item_no = item_no.strip()

        # Handle sub-items like "a)", "b)"
        sub_match = re.match(r'^([a-z])\)\s*(.*)', item_no, re.IGNORECASE)
        if sub_match:
            return sub_match.group(1)

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
            # Extract numeric parts from item_no
            item_id = re.sub(r'[^\d.]', '', item_no)
            if item_id:
                parts = item_id.split('.')
                if len(parts) == 2:
                    return f"{prefix}-{parts[0]}{parts[1].zfill(2)}"
                elif len(parts) == 3:
                    return f"{prefix}-{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
        return prefix

    def import_to_project(self, project_name, items=None):
        """Import parsed items into Custom BOQ doctype."""
        if not frappe.db.exists("Project", project_name):
            raise ValueError(f"Project {project_name} does not exist")

        if items is None:
            items = self.items

        imported = []
        errors = []
        total_value = 0

        for item in items:
            try:
                doc = frappe.get_doc({
                    "doctype": "Custom BOQ",
                    "project": project_name,
                    "item_code": item["item_no"],
                    "description": item["description"],
                    "boq_quantity": item["qty"],
                    "uom": item["unit"],
                    "unit_rate": item["rate"],
                    "total_value": item["total"],
                    "wbs_code": item["wbs_code"],
                    "measurement_method": "Unit-Based",
                })
                doc.insert(ignore_permissions=True, ignore_links=True)
                total_value += item["total"]
                imported.append(item["item_no"])
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