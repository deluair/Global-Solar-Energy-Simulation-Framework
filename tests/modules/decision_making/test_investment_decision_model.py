import unittest
import sys
import os

# Adjust path to import modules from src
current_dir = os.path.dirname(os.path.abspath(__file__))
# tests/modules/decision_making -> tests/modules -> tests -> project_root
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root_dir, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from modules.economic_framework.cost_model import CostModel
from modules.technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology
from modules.decision_making.investment_decision_model import InvestmentDecisionModel, TONS_CO2_AVOIDED_PER_MWH # Import constant
from modules.economic_framework.market_model import MarketSimulator
from modules.economic_framework.carbon_pricing_model import CarbonPricingMechanism # Added import

class TestInvestmentDecisionModel(unittest.TestCase):
    def setUp(self):
        """Set up common resources for tests."""
        self.stm = SolarTechModel()
        self.tech_pv = SolarTechnology(
            name='TestSiliconPV',
            base_efficiency=0.20, projected_efficiency_2035=0.25, start_year=2023,
            commercial_scale_year=2020, base_capex_usd_per_kw=1000, annual_capex_reduction_rate=0.02
        )
        self.stm.add_technology(self.tech_pv)

        # Corrected CostModel instantiation using initial_costs dictionary
        cost_settings_pv = {
            'module_usd_per_kw': self.tech_pv.base_capex_usd_per_kw, # Assign total base capex to module for simplicity
            'bos_usd_per_kw': 0, 
            'inverter_usd_per_kw': 0, 
            'installation_usd_per_kw': 0,
            'opex_per_kw_year': 20  # Example OPEX
        }
        self.cost_model_pv = CostModel(
            technology_name='TestSiliconPV', 
            initial_costs=cost_settings_pv, 
            learning_rate=0.0 # Assuming no learning for these tests or handled by SolarTechModel's capex evolution
        )
        
        self.test_market_designs = {
            'TestRegionA': {
                'type': 'energy_only',
                'base_energy_price_usd_per_mwh': 70.0, 
                'tou_factors': {'peak': 1.2, 'mid_peak': 1.0, 'off_peak': 0.8},
                'ancillary_services': {
                    'frequency_response': {'price_usd_per_mw_year': 5000, 'availability_factor': 0.9},
                    'voltage_support': {'price_usd_per_mw_year': 3000, 'availability_factor': 0.8}
                }
            },
            'TestRegionB_LowPrice': {
                'type': 'energy_only',
                'base_energy_price_usd_per_mwh': 20.0, 
                'tou_factors': {'peak': 1.0, 'mid_peak': 1.0, 'off_peak': 1.0},
                'ancillary_services': {}
            }
        }
        self.market_simulator = MarketSimulator(market_designs=self.test_market_designs)

        # Setup CarbonPricingMechanism
        self.test_carbon_schemes = {
            'HighCarbonTax': {'type': 'tax', 'price_per_ton_co2': 75.0},
            'ZeroCarbonTax': {'type': 'tax', 'price_per_ton_co2': 0.0},
            'EU_ETS_Test': {'type': 'cap_and_trade', 'price_per_ton_co2': 90.0}
        }
        self.carbon_pricing_model = CarbonPricingMechanism(schemes=self.test_carbon_schemes)

        self.investment_model = InvestmentDecisionModel(
            cost_model=self.cost_model_pv, 
            solar_tech_model=self.stm, 
            market_simulator=self.market_simulator,
            carbon_pricing_model=self.carbon_pricing_model # Pass instance
        )

    def test_evaluate_project_attractiveness_valid_scenario(self):
        """Test project evaluation with a standard, valid scenario."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',             
            time_of_day='peak',               
            ancillary_service_types=['frequency_response'],
            region_carbon_scheme_name='HighCarbonTax' # Added carbon scheme
        )

        self.assertIsNotNone(results)
        self.assertNotIn('error', results, msg=f"Evaluation returned an error: {results.get('error')}")
        self.assertEqual(results['technology_name'], 'TestSiliconPV')
        self.assertEqual(results['year'], 2025)
        self.assertEqual(results['project_capacity_mw'], 10.0)
        self.assertEqual(results['region_evaluated'], 'TestRegionA')
        self.assertEqual(results['time_of_day_evaluated'], 'peak')
        self.assertIn('frequency_response', results['ancillary_service_types_evaluated'])

        expected_keys = [
            'lcoe_data', 'market_price_from_simulator_usd_per_mwh', 
            'total_ancillary_revenue_usd_per_year', 'profit_margin_usd_per_mwh',
            'initial_investment_usd', 'annual_net_cash_flow_usd',
            'simple_payback_period_years', 'npv_usd', 'attractiveness_score',
            'carbon_credit_revenue_usd_per_year', 'region_carbon_scheme_name_used' # Added keys
        ]
        for key in expected_keys:
            self.assertIn(key, results, msg=f"Key '{key}' not found in results")

        self.assertIsInstance(results['lcoe_data'].get('lcoe_usd_per_mwh'), float)
        self.assertGreater(results['lcoe_data'].get('lcoe_usd_per_mwh'), 0)

        self.assertIsInstance(results['market_price_from_simulator_usd_per_mwh'], float)
        self.assertGreater(results['market_price_from_simulator_usd_per_mwh'], 0)
        self.assertAlmostEqual(results['market_price_from_simulator_usd_per_mwh'], 70.0 * 1.2, places=2)

        self.assertIsInstance(results['total_ancillary_revenue_usd_per_year'], float)
        self.assertGreaterEqual(results['total_ancillary_revenue_usd_per_year'], 0)
        self.assertAlmostEqual(results['total_ancillary_revenue_usd_per_year'], 10.0 * 5000 * 0.9, places=1)
        
        self.assertIsInstance(results['carbon_credit_revenue_usd_per_year'], float)
        self.assertGreaterEqual(results['carbon_credit_revenue_usd_per_year'], 0)
        self.assertEqual(results['region_carbon_scheme_name_used'], 'HighCarbonTax')

        # Calculate expected carbon revenue for assertion
        tech_data = self.stm.get_technology_details('TestSiliconPV', 2025)
        efficiency = tech_data['efficiency'] if tech_data and 'efficiency' in tech_data else self.tech_pv.base_efficiency # Fallback
        # Annual Generation MWh = Capacity (MW) * Capacity Factor * 8760 hours/year
        annual_generation_mwh = 10.0 * 0.18 * 8760
        annual_co2_avoided = annual_generation_mwh * TONS_CO2_AVOIDED_PER_MWH
        expected_carbon_revenue = annual_co2_avoided * self.test_carbon_schemes['HighCarbonTax']['price_per_ton_co2']
        self.assertAlmostEqual(results['carbon_credit_revenue_usd_per_year'], expected_carbon_revenue, places=1)

        self.assertIsInstance(results['initial_investment_usd'], float)
        self.assertGreater(results['initial_investment_usd'], 0)

        self.assertIsInstance(results['annual_net_cash_flow_usd'], float) 

        if isinstance(results['simple_payback_period_years'], str):
             self.assertIn(results['simple_payback_period_years'], ['N/A (negative or zero cash flow)', 'N/A (initial investment is zero)'])
        else:
            self.assertIsInstance(results['simple_payback_period_years'], float)
            self.assertGreaterEqual(results['simple_payback_period_years'], 0)

        self.assertIsInstance(results['npv_usd'], float) 

    def test_evaluate_project_attractiveness_negative_cash_flow(self):
        """Test project evaluation with parameters leading to negative annual net cash flow."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18, 
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionB_LowPrice', 
            time_of_day='mid_peak',       
            ancillary_service_types=[],
            region_carbon_scheme_name='ZeroCarbonTax' # Test with zero carbon price
        )

        self.assertIsNotNone(results)
        self.assertNotIn('error', results, msg=f"Evaluation returned an error: {results.get('error')}")
        
        self.assertLess(results['annual_net_cash_flow_usd'], 0, msg="Annual net cash flow should be negative.")
        self.assertEqual(results['simple_payback_period_years'], 'N/A (negative or zero cash flow)', msg="Payback period should be N/A for negative cash flow.")
        self.assertLess(results['npv_usd'], 0, msg="NPV should be negative for consistently negative cash flow projects.")
        self.assertLess(results['profit_margin_usd_per_mwh'], 0, msg="Profit margin per MWh should be negative.")

    def test_evaluate_project_attractiveness_lcoe_error(self):
        """Test project evaluation when LCOE calculation encounters an error (e.g., tech not found)."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='NonExistentTech',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA', 
            time_of_day='mid_peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='HighCarbonTax'
        )

        self.assertIsNotNone(results)
        self.assertIn('error', results, msg="Results should contain an 'error' key when LCOE calculation fails.")
        self.assertIn('Technology \'NonExistentTech\' not found', results['error'], msg="Error message should indicate technology not found.")
        self.assertNotIn('attractiveness_score', results, msg="Attractiveness score should not be present on LCOE error if returned early.")

    def test_evaluate_project_attractiveness_zero_capacity_factor(self):
        """Test project evaluation with zero capacity factor."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.0,  
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='mid_peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='HighCarbonTax'
        )

        self.assertIsNotNone(results)
        self.assertIn('error', results, msg="Results should contain an 'error' key for zero capacity factor if costs > 0.")
        self.assertIn('Annual generation is zero', results['lcoe_data'].get('error', ''), msg="LCOE error message should indicate zero annual generation.")
        self.assertEqual(results['lcoe_data'].get('lcoe_usd_per_mwh'), float('inf'), msg="LCOE should be infinite with zero capacity factor and positive costs.")
        self.assertNotIn('attractiveness_score', results, msg="Attractiveness score should not be present if LCOE error leads to early return.")

    def test_evaluate_project_attractiveness_zero_lifetime(self):
        """Test project evaluation with zero economic lifetime."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.15, 
            discount_rate=0.05,
            economic_lifetime_years=0,  
            region='TestRegionA',
            time_of_day='mid_peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='HighCarbonTax'
        )

        self.assertIsNotNone(results)
        self.assertIn('error', results, msg="Results should contain an 'error' key for zero lifetime if costs > 0.")
        self.assertIn('Lifetime is 0 years', results['lcoe_data'].get('error', ''), msg="LCOE error message should indicate zero lifetime.")
        self.assertEqual(results['lcoe_data'].get('lcoe_usd_per_mwh'), float('inf'), msg="LCOE should be infinite with zero lifetime and positive costs.")
        self.assertNotIn('attractiveness_score', results, msg="Attractiveness score should not be present if LCOE error leads to early return.")

    def test_evaluate_project_attractiveness_zero_project_capacity(self):
        """Test project evaluation with zero project capacity."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=0.0,  
            capacity_factor=0.15,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='mid_peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='HighCarbonTax'
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results, msg="Should not be an error state for zero capacity if LCOE is valid.")
        self.assertGreater(results['lcoe_data'].get('lcoe_usd_per_mwh', 0), 0, msg="LCOE should be a valid positive number.")
        self.assertEqual(results['initial_investment_usd'], 0.0, msg="Initial investment should be zero.")
        self.assertEqual(results['annual_net_cash_flow_usd'], 0.0, msg="Annual net cash flow should be zero.")
        self.assertEqual(results['total_ancillary_revenue_usd_per_year'], 0.0, msg="Total ancillary revenue should be zero for zero capacity.")
        self.assertEqual(results['simple_payback_period_years'], 0.0, msg="Payback period should be 0.0 for zero capacity and zero investment.")
        self.assertEqual(results['npv_usd'], 0.0, msg="NPV should be zero.")

    def test_evaluate_project_attractiveness_zero_discount_rate(self):
        """Test project evaluation with zero discount rate."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18, 
            discount_rate=0.0,  # Zero discount rate
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=['frequency_response'],
            region_carbon_scheme_name='HighCarbonTax'
        )

        self.assertIsNotNone(results)
        self.assertNotIn('error', results, msg=f"Evaluation returned an error: {results.get('error')}")
        self.assertGreaterEqual(results['npv_usd'], 0, msg="NPV should be non-negative for zero discount rate if cash flows are positive or zero.")

    def test_evaluate_project_attractiveness_multiple_ancillary_services(self):
        """Test with multiple ancillary services."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=['frequency_response', 'voltage_support'],
            region_carbon_scheme_name='HighCarbonTax'
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results, msg=f"Evaluation returned an error: {results.get('error')}")
        self.assertAlmostEqual(results['total_ancillary_revenue_usd_per_year'], 69000, places=1)

    def test_evaluate_project_attractiveness_non_existent_ancillary_service(self):
        """Test with a non-existent ancillary service type."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=['non_existent_service'],
            region_carbon_scheme_name='HighCarbonTax'
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results)
        self.assertAlmostEqual(results['total_ancillary_revenue_usd_per_year'], 0.0, places=2)

    # --- New tests for Carbon Pricing Integration --- 

    def test_carbon_pricing_significant_revenue(self):
        """Test scenario where carbon pricing provides significant revenue."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.20, # Slightly higher CF for more pronounced effect
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=[], # No ancillary to isolate carbon revenue
            region_carbon_scheme_name='EU_ETS_Test' # High carbon price
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results)
        self.assertEqual(results['region_carbon_scheme_name_used'], 'EU_ETS_Test')
        self.assertGreater(results['carbon_credit_revenue_usd_per_year'], 0)

        annual_generation_mwh = 10.0 * 0.20 * 8760
        annual_co2_avoided = annual_generation_mwh * TONS_CO2_AVOIDED_PER_MWH
        expected_carbon_revenue = annual_co2_avoided * self.test_carbon_schemes['EU_ETS_Test']['price_per_ton_co2']
        self.assertAlmostEqual(results['carbon_credit_revenue_usd_per_year'], expected_carbon_revenue, places=1)
        
        # Check impact on overall financials
        # Example: Ensure NPV is higher than without carbon revenue (requires baseline or more complex check)
        self.assertTrue(results['annual_net_cash_flow_usd'] > results['projected_annual_profit_usd'])

    def test_carbon_pricing_zero_price(self):
        """Test scenario with a carbon scheme that has a zero price."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='ZeroCarbonTax'
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results)
        self.assertEqual(results['region_carbon_scheme_name_used'], 'ZeroCarbonTax')
        self.assertAlmostEqual(results['carbon_credit_revenue_usd_per_year'], 0.0, places=2)

    def test_carbon_pricing_no_scheme_provided(self):
        """Test scenario where no carbon scheme name is provided."""
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=[],
            region_carbon_scheme_name=None # Explicitly None
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results)
        self.assertIsNone(results['region_carbon_scheme_name_used'])
        self.assertAlmostEqual(results['carbon_credit_revenue_usd_per_year'], 0.0, places=2)

    def test_carbon_pricing_invalid_scheme_name(self):
        """Test scenario with an invalid/non-existent carbon scheme name."""
        # CarbonPricingMechanism.get_carbon_cost currently prints a warning and returns 0 for unknown schemes.
        results = self.investment_model.evaluate_project_attractiveness(
            technology_name='TestSiliconPV',
            year=2025,
            project_capacity_mw=10.0,
            capacity_factor=0.18,
            discount_rate=0.05,
            economic_lifetime_years=25,
            region='TestRegionA',
            time_of_day='peak',
            ancillary_service_types=[],
            region_carbon_scheme_name='NonExistentScheme'
        )
        self.assertIsNotNone(results)
        self.assertNotIn('error', results)
        self.assertEqual(results['region_carbon_scheme_name_used'], 'NonExistentScheme') # Model stores what's passed
        self.assertAlmostEqual(results['carbon_credit_revenue_usd_per_year'], 0.0, places=2, msg="Carbon revenue should be 0 for unknown scheme.")


if __name__ == '__main__':
    unittest.main()
