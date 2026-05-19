# tests/test_boq_import.py
import frappe, unittest, os

class TestBOQImport(unittest.TestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        if not frappe.db.exists("Project", "ARAT-KILO"):
            proj = frappe.get_doc({
                "doctype": "Project",
                "project_name": "Arat Kilo Building",
                "is_epc_project": 1,
                "project_typology": "Civil",
                "billing_track": "RA-Billing",
                "status": "Active",
                "contract_value": 300000000
            })
            proj.insert()

    def test_parse_boq_csv(self):
        """Parse Arat Kilo BOQ CSV and extract line items."""
        from epc_modules.utils.boq_importer import AratKiloBOQImporter

        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "Arat Kilo  BOQ for BID.csv")
        importer = AratKiloBOQImporter()
        items = importer.parse_csv(csv_path)

        self.assertGreater(len(items), 50)
        section2 = [i for i in items if i["section"] == "02" and i["item_no"]]
        self.assertGreater(len(section2), 5)
        rates = [i["rate"] for i in items if i["rate"] and i["rate"] > 0]
        self.assertGreater(len(rates), 10)

    def test_import_boq_to_project(self):
        """Import parsed BOQ items into Custom BOQ doctype."""
        from epc_modules.utils.boq_importer import AratKiloBOQImporter

        csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "Arat Kilo  BOQ for BID.csv")
        importer = AratKiloBOQImporter()
        items = importer.parse_csv(csv_path)

        imported = importer.import_to_project("ARAT-KILO", items)
        self.assertGreater(imported["count"], 50)
        self.assertIn("total_value", imported)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.sql("DELETE FROM `tabCustom BOQ` WHERE project = 'ARAT-KILO'")
        frappe.db.commit()