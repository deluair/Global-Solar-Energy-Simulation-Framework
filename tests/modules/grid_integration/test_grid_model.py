import unittest
import sys
import os

# Adjust path to import modules from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root_dir, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from modules.grid_integration.grid_model import GridModel

class TestGridModel(unittest.TestCase):

    def setUp(self):
        """Set up common GridModel instances for testing."""
        self.grid_default = GridModel(
            region_name='TestRegion_Default',
            existing_capacity_mw=1000,
            current_load_mw=600
        )
        self.grid_constrained = GridModel(
            region_name='TestRegion_Constrained',
            existing_capacity_mw=500,
            current_load_mw=400,
            max_solar_penetration_pct=0.10, # Low penetration limit
            base_interconnection_cost_usd_per_mw=150000,
            transmission_constraint_factor=1.5,
            avg_transmission_cost_usd_per_mw_km=2500,
            avg_terrain_factor=1.3
        )

    def test_initialization(self):
        """Test that GridModel initializes with correct default and custom attributes."""
        self.assertEqual(self.grid_default.region_name, 'TestRegion_Default')
        self.assertEqual(self.grid_default.existing_capacity_mw, 1000)
        self.assertEqual(self.grid_default.current_load_mw, 600)
        self.assertEqual(self.grid_default.max_solar_penetration_pct, 0.50) # Default
        self.assertEqual(self.grid_default.current_solar_mw, 0)
        self.assertEqual(self.grid_default.base_interconnection_cost_usd_per_mw, 100000) # Default
        self.assertEqual(self.grid_default.transmission_constraint_factor, 1.0) # Default
        self.assertEqual(self.grid_default.avg_transmission_cost_usd_per_mw_km, 2000.0) # Default
        self.assertEqual(self.grid_default.avg_terrain_factor, 1.0) # Default

        self.assertEqual(self.grid_constrained.max_solar_penetration_pct, 0.10)
        self.assertEqual(self.grid_constrained.transmission_constraint_factor, 1.5)
        self.assertEqual(self.grid_constrained.avg_transmission_cost_usd_per_mw_km, 2500)
        self.assertEqual(self.grid_constrained.avg_terrain_factor, 1.3)

    def test_add_solar_capacity_success(self):
        """Test adding solar capacity within limits."""
        can_add = self.grid_default.add_solar_capacity(100) # 100 MW is 10% of 1000 MW (limit is 50%)
        self.assertTrue(can_add)
        self.assertEqual(self.grid_default.current_solar_mw, 100)

    def test_add_solar_capacity_exceeds_limit(self):
        """Test adding solar capacity that exceeds penetration limits."""
        # For grid_constrained, limit is 0.10 * 500 MW = 50 MW
        can_add_initial = self.grid_constrained.add_solar_capacity(40) # Add 40 MW (ok)
        self.assertTrue(can_add_initial)
        self.assertEqual(self.grid_constrained.current_solar_mw, 40)

        can_add_more = self.grid_constrained.add_solar_capacity(20) # Try to add 20 more (total 60, exceeds 50)
        self.assertFalse(can_add_more)
        self.assertEqual(self.grid_constrained.current_solar_mw, 40) # Should remain unchanged

    def test_add_solar_capacity_exact_limit(self):
        """Test adding solar capacity that exactly meets the penetration limit."""
        limit_mw = self.grid_default.existing_capacity_mw * self.grid_default.max_solar_penetration_pct
        can_add = self.grid_default.add_solar_capacity(limit_mw)
        self.assertTrue(can_add)
        self.assertEqual(self.grid_default.current_solar_mw, limit_mw)

        # Try to add more, should fail
        can_add_tiny_more = self.grid_default.add_solar_capacity(0.1)
        self.assertFalse(can_add_tiny_more)
        self.assertEqual(self.grid_default.current_solar_mw, limit_mw)

    def test_estimate_interconnection_cost(self):
        """Test the interconnection cost estimation."""
        cost_default = self.grid_default.estimate_interconnection_cost(10) # 10 MW
        expected_cost_default = 10 * 100000 * 1.0
        self.assertEqual(cost_default, expected_cost_default)

        cost_constrained = self.grid_constrained.estimate_interconnection_cost(10) # 10 MW
        expected_cost_constrained = 10 * 150000 * 1.5
        self.assertEqual(cost_constrained, expected_cost_constrained)

    def test_estimate_transmission_upgrade_cost(self):
        """Test the enhanced transmission upgrade cost estimation."""
        # Scenario 1: Default grid
        cost1 = self.grid_default.estimate_transmission_upgrade_cost(
            solar_capacity_to_support_mw=100,
            distance_km=50
        )
        # Expected: 100 MW * 50 km * $2000/MW-km * 1.0 (terrain) * 1.0 (constraint)
        expected_cost1 = 100 * 50 * 2000.0 * 1.0 * 1.0
        self.assertEqual(cost1, expected_cost1)

        # Scenario 2: Constrained grid with specific factors
        cost2 = self.grid_constrained.estimate_transmission_upgrade_cost(
            solar_capacity_to_support_mw=50,
            distance_km=30
        )
        # Expected: 50 MW * 30 km * $2500/MW-km * 1.3 (terrain) * 1.5 (constraint)
        expected_cost2 = 50 * 30 * 2500 * 1.3 * 1.5
        self.assertAlmostEqual(cost2, expected_cost2, places=2)

    def test_estimate_transmission_upgrade_cost_zero_distance(self):
        """Test transmission upgrade cost with zero distance."""
        cost = self.grid_default.estimate_transmission_upgrade_cost(
            solar_capacity_to_support_mw=100,
            distance_km=0
        )
        self.assertEqual(cost, 0)

    def test_estimate_transmission_upgrade_cost_zero_capacity(self):
        """Test transmission upgrade cost with zero capacity."""
        cost = self.grid_default.estimate_transmission_upgrade_cost(
            solar_capacity_to_support_mw=0,
            distance_km=50
        )
        self.assertEqual(cost, 0)

if __name__ == '__main__':
    unittest.main()
