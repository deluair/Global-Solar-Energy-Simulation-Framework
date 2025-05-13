import unittest
from unittest.mock import MagicMock, patch
import math

# Assuming the module structure, adjust if necessary
# If running tests from the root directory, these imports should work.
# You might need to adjust them based on your PYTHONPATH or test runner configuration.
from src.modules.sector_coupling.industrial_decarbonization_model import IndustrialDecarbonizationModel
from src.modules.technological_evolution.solar_tech_model import SolarTechModel
from src.modules.economic_framework.cost_model import CostModel

class TestIndustrialDecarbonizationModel(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.mock_industry_data = {'TestIndustry': {'some_data': 123}}
        self.model = IndustrialDecarbonizationModel(industry_data=self.mock_industry_data)

        # Mock SolarTechModel and CostModel instances
        self.mock_solar_tech_model = MagicMock(spec=SolarTechModel)
        self.mock_cost_model = MagicMock(spec=CostModel)

        # Default parameters for LCOH calculation, can be overridden in tests
        self.default_lcoh_params = {
            'solar_tech_model': self.mock_solar_tech_model,
            'solar_cost_model': self.mock_cost_model,
            'solar_tech_name': 'TestSolarTech',
            'solar_project_year': 2025,
            'solar_project_capacity_factor': 0.25,
            'solar_project_discount_rate': 0.05,
            'solar_project_lifetime_years': 25,
            'electrolyzer_capex_usd_per_kw': 600,
            'electrolyzer_efficiency_kwh_per_kg_h2': 50.0,
            'electrolyzer_capacity_factor': 0.70,
            'electrolyzer_discount_rate': 0.07,
            'electrolyzer_lifetime_years': 20,
            'stack_lifetime_hours': 80000,
            'stack_replacement_cost_pct_capex': 0.35,
            'fixed_om_cost_pct_capex': 0.015,
            'variable_om_cost_usd_per_mwh': 0.5
        }

    def test_estimate_lcoh_valid_scenario(self):
        """Test LCOH calculation for a typical valid scenario."""
        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.return_value = {
            'lcoe_usd_per_mwh': 30.0, 
            'capex_usd_per_kw': 800,
            'efficiency': 0.20,
            'opex_per_kw_year': 15,
            'error': None
        }

        lcoh = self.model.estimate_green_hydrogen_production_cost(**self.default_lcoh_params)
        
        self.assertIsNotNone(lcoh)
        self.assertGreater(lcoh, 1.5) 
        self.assertLess(lcoh, 3.0)

        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.assert_called_once_with(
            solar_tech_model=self.mock_solar_tech_model,
            technology_name='TestSolarTech',
            year=2025,
            capacity_factor=0.25,
            discount_rate=0.05,
            economic_lifetime_years=25
        )

    def test_estimate_lcoh_solar_lcoe_error(self):
        """Test LCOH when internal solar LCOE calculation returns an error message."""
        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.return_value = {
            'lcoe_usd_per_mwh': float('inf'), 
            'error': 'Failed to calculate solar LCOE due to missing data'
        }
        lcoh = self.model.estimate_green_hydrogen_production_cost(**self.default_lcoh_params)
        self.assertEqual(lcoh, float('inf'))

    def test_estimate_lcoh_solar_lcoe_infinite_value(self):
        """Test LCOH when internal solar LCOE calculation returns infinite LCOE without error message."""
        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.return_value = {
            'lcoe_usd_per_mwh': float('inf'),
            'error': None
        }
        lcoh = self.model.estimate_green_hydrogen_production_cost(**self.default_lcoh_params)
        self.assertEqual(lcoh, float('inf'))

    def test_estimate_lcoh_zero_electrolyzer_capacity_factor(self):
        """Test LCOH with zero electrolyzer capacity factor, leading to no H2 production."""
        params = self.default_lcoh_params.copy()
        params['electrolyzer_capacity_factor'] = 0.0
        
        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.return_value = {
            'lcoe_usd_per_mwh': 30.0, 'error': None
        }

        lcoh = self.model.estimate_green_hydrogen_production_cost(**params)
        self.assertEqual(lcoh, float('inf'))

    def test_estimate_lcoh_zero_electrolyzer_lifetime_and_discount_rate(self):
        """Test LCOH with zero electrolyzer lifetime and zero discount rate, causing CRF issues."""
        params = self.default_lcoh_params.copy()
        params['electrolyzer_lifetime_years'] = 0
        params['electrolyzer_discount_rate'] = 0.0

        self.mock_cost_model.calculate_lcoe_for_evolving_solar_tech.return_value = {
            'lcoe_usd_per_mwh': 30.0, 'error': None
        }
        lcoh = self.model.estimate_green_hydrogen_production_cost(**params)
        self.assertEqual(lcoh, float('inf'))

if __name__ == '__main__':
    unittest.main()
