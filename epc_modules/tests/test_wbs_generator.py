"""
WBS Generator Tests

Tests for Work Breakdown Structure generation.
"""

import unittest
import frappe
from frappe.utils import flt
from epc_modules.utils.wbs_generator import (
    WBSGenerator,
    WBSNode,
    CostBreakdownWBSGenerator,
    HierarchicalWBSGenerator
)


class TestWBSNode(unittest.TestCase):
    """Test WBS Node structure."""

    def test_node_creation(self):
        """Test creating a WBS node."""
        node = WBSNode(
            code="1",
            name="Project",
            level=0,
            cost_code="PRJ-001"
        )

        self.assertEqual(node.code, "1")
        self.assertEqual(node.name, "Project")
        self.assertEqual(node.level, 0)

    def test_node_children(self):
        """Test node children management."""
        parent = WBSNode(code="1", name="Project", level=0)
        child1 = WBSNode(code="1.1", name="Phase 1", level=1)
        child2 = WBSNode(code="1.2", name="Phase 2", level=1)

        parent.add_child(child1)
        parent.add_child(child2)

        self.assertEqual(len(parent.children), 2)
        self.assertIn(child1, parent.children)
        self.assertIn(child2, parent.children)

    def test_node_cost_aggregation(self):
        """Test cost aggregation up the tree."""
        parent = WBSNode(code="1", name="Project", level=0, budget=0)
        child1 = WBSNode(code="1.1", name="Phase 1", level=1, budget=1000)
        child2 = WBSNode(code="1.2", name="Phase 2", level=1, budget=2000)

        parent.add_child(child1)
        parent.add_child(child2)

        self.assertEqual(parent.get_total_cost(), 3000)

    def test_node_tree_depth(self):
        """Test tree depth calculation."""
        root = WBSNode(code="1", name="Project", level=0)
        level1 = WBSNode(code="1.1", name="Phase 1", level=1)
        level2 = WBSNode(code="1.1.1", name="Task 1", level=2)

        level1.add_child(level2)
        root.add_child(level1)

        self.assertEqual(root.get_max_depth(), 3)


class TestWBSGenerator(unittest.TestCase):
    """Test base WBS Generator."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_generate_wbs_structure(self):
        """Test generating WBS structure."""
        project_data = {
            "name": "Test Project",
            "project_name": "Test Project",
            "total_contract_value": 10000000
        }

        generator = WBSGenerator(project_data)
        structure = generator.generate()

        self.assertIn("nodes", structure)
        self.assertIn("hierarchy", structure)

    def test_wbs_code_format(self):
        """Test WBS code format validation."""
        generator = WBSGenerator({})
        codes = ["1", "1.1", "1.1.1", "2.3.4.5"]

        for code in codes:
            self.assertTrue(generator.is_valid_code_format(code))

    def test_invalid_wbs_code(self):
        """Test invalid WBS code detection."""
        generator = WBSGenerator({})
        invalid_codes = ["1.", ".1", "1..1", "a.1", "1.1.1.1.1.1.1"]

        for code in invalid_codes:
            self.assertFalse(generator.is_valid_code_format(code))


class TestCostBreakdownWBSGenerator(unittest.TestCase):
    """Test cost breakdown WBS generator (for Civil)."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_civil_wbs_cost_categories(self):
        """Test civil WBS has cost categories."""
        project_data = {
            "name": "Test Civil Project",
            "project_name": "Test Civil Project",
            "typology": "Civil",
            "total_contract_value": 25000000
        }

        generator = CostBreakdownWBSGenerator(project_data)
        structure = generator.generate()

        # Should have cost breakdown categories
        self.assertIn("cost_categories", structure)

    def test_generate_cost_breakdown(self):
        """Test cost breakdown generation."""
        project_data = {
            "name": "Test Civil Project",
            "project_name": "Test Civil Project",
            "typology": "Civil",
            "total_contract_value": 10000000
        }

        generator = CostBreakdownWBSGenerator(project_data)
        breakdown = generator.generate_cost_breakdown()

        # Should have standard civil categories
        expected_categories = ["Direct Costs", "Indirect Costs", "Contingency"]
        for cat in expected_categories:
            self.assertIn(cat, breakdown)

    def test_wbs_structure_for_civil(self):
        """Test WBS structure for civil projects."""
        project_data = {
            "name": "Test Civil Project",
            "typology": "Civil",
            "total_contract_value": 15000000
        }

        generator = CostBreakdownWBSGenerator(project_data)
        structure = generator.generate()

        # Verify standard civil categories
        nodes = structure.get("nodes", [])
        category_names = [n.get("name") for n in nodes]

        self.assertTrue(any("Direct" in name for name in category_names))

    def test_boq_integration(self):
        """Test BOQ item linking in WBS."""
        project_data = {
            "name": "Test Civil Project",
            "typology": "Civil",
            "total_contract_value": 10000000
        }

        generator = CostBreakdownWBSGenerator(project_data)
        boq_mapping = generator.get_boq_wbs_mapping()

        self.assertIsInstance(boq_mapping, dict)


class TestHierarchicalWBSGenerator(unittest.TestCase):
    """Test hierarchical WBS generator (for Electromechanical)."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_electromechanical_wbs_hierarchy(self):
        """Test electromechanical WBS has hierarchical structure."""
        project_data = {
            "name": "Test EM Project",
            "project_name": "Test EM Project",
            "typology": "Electromechanical",
            "total_contract_value": 50000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        structure = generator.generate()

        self.assertIn("hierarchy", structure)

    def test_generate_phase_structure(self):
        """Test phase-based structure generation."""
        project_data = {
            "name": "Test EM Project",
            "typology": "Electromechanical",
            "total_contract_value": 20000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        phases = generator.generate_phase_structure()

        # Should have standard project phases
        expected_phases = ["Engineering", "Procurement", "Construction", "Commissioning"]
        for phase in expected_phases:
            self.assertIn(phase, phases)

    def test_wbs_levels(self):
        """Test WBS level definitions."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical",
            "total_contract_value": 10000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        levels = generator.get_wbs_levels()

        # Standard 4-level WBS
        self.assertEqual(len(levels), 4)
        self.assertEqual(levels[0]["name"], "Project")
        self.assertEqual(levels[1]["name"], "Phase")
        self.assertEqual(levels[2]["name"], "Package")
        self.assertEqual(levels[3]["name"], "Activity")

    def test_generate_package_breakdown(self):
        """Test package breakdown generation."""
        project_data = {
            "name": "Test EM Project",
            "typology": "Electromechanical",
            "total_contract_value": 30000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        packages = generator.generate_package_breakdown("Engineering")

        self.assertIsInstance(packages, list)
        # Should have engineering packages
        self.assertGreater(len(packages), 0)

    def test_equipment_wbs_category(self):
        """Test equipment category in WBS."""
        project_data = {
            "name": "Test EM Project",
            "typology": "Electromechanical",
            "total_contract_value": 10000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        structure = generator.generate()

        nodes = structure.get("nodes", [])
        has_equipment = any("Equipment" in n.get("name", "") for n in nodes)

        self.assertTrue(has_equipment)


class TestWBSCalculations(unittest.TestCase):
    """Test WBS-based calculations."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_calculate_level_costs(self):
        """Test level cost calculation."""
        project_data = {
            "name": "Test Project",
            "total_contract_value": 10000000
        }

        generator = WBSGenerator(project_data)
        costs = generator.calculate_level_costs()

        self.assertIsInstance(costs, dict)
        # Level 0 should be total contract value
        self.assertEqual(costs.get(0), 10000000)

    def test_cost_distribution(self):
        """Test cost distribution across WBS."""
        project_data = {
            "name": "Test Project",
            "total_contract_value": 10000000
        }

        generator = WBSGenerator(project_data)
        distribution = generator.calculate_cost_distribution()

        self.assertIsInstance(distribution, dict)
        total_pct = sum(distribution.values())
        self.assertAlmostEqual(total_pct, 100, places=2)

    def test_earned_value_at_node(self):
        """Test earned value calculation at node."""
        node = WBSNode(
            code="1.1",
            name="Phase 1",
            level=1,
            budget=5000000
        )

        # Simulate 50% progress
        node.actual_progress = 50

        earned_value = node.get_earned_value()
        self.assertEqual(earned_value, 2500000)

    def test_variance_calculation(self):
        """Test cost/SCHEDULE variance calculation."""
        node = WBSNode(
            code="1.1",
            name="Phase 1",
            level=1,
            budget=1000000
        )
        node.actual_cost = 600000
        node.earned_value = 500000

        cv = node.get_cost_variance()
        self.assertEqual(cv, -100000)  # Over budget

        sv = node.get_schedule_variance()
        self.assertIsNotNone(sv)


class TestWBSExport(unittest.TestCase):
    """Test WBS export functionality."""

    def setUp(self):
        """Set up test environment."""
        frappe.set_user("Administrator")

    def test_export_to_excel_format(self):
        """Test Excel export format."""
        project_data = {
            "name": "Test Project",
            "total_contract_value": 10000000
        }

        generator = WBSGenerator(project_data)
        export_data = generator.export_data()

        self.assertIn("columns", export_data)
        self.assertIn("rows", export_data)
        self.assertIn("WBS Code", export_data["columns"])
        self.assertIn("Description", export_data["columns"])

    def test_export_costs(self):
        """Test cost data in export."""
        project_data = {
            "name": "Test Project",
            "total_contract_value": 10000000
        }

        generator = WBSGenerator(project_data)
        export_data = generator.export_data()

        rows = export_data.get("rows", [])
        self.assertGreater(len(rows), 0)

        # Check total row
        total_row = [r for r in rows if r.get("WBS Code") == "Total"]
        self.assertEqual(len(total_row), 1)
        self.assertEqual(total_row[0].get("Budget"), 10000000)

    def test_hierarchy_export(self):
        """Test hierarchy preservation in export."""
        project_data = {
            "name": "Test Project",
            "typology": "Electromechanical",
            "total_contract_value": 20000000
        }

        generator = HierarchicalWBSGenerator(project_data)
        export_data = generator.export_data()

        # Check hierarchy column exists
        self.assertIn("Parent Code", export_data["columns"])


if __name__ == "__main__":
    unittest.main()