import unittest
import sys
import os

# Adjust path to import modules from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
src_path = os.path.join(project_root_dir, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

from modules.policy_landscape.policy_model import PolicyModel

class TestPolicyModel(unittest.TestCase):

    def setUp(self):
        """Set up a PolicyModel instance with a diverse set of example policies."""
        self.example_policies = [
            {
                'id': 'US_ITC_SOLAR_2025',
                'type': 'itc',
                'value': 0.30,
                'region': 'USA',
                'start_year': 2022,
                'end_year': 2032,
                'technology_scope': ['solar_pv', 'csp'],
                'description': 'US Federal Solar Investment Tax Credit'
            },
            {
                'id': 'EU_CARBON_PRICE_2028',
                'type': 'carbon_price',
                'value': 95, # 95 USD/ton CO2
                'region': 'EU',
                'start_year': 2028,
                'end_year': 2035,
                'description': 'EU ETS Carbon Price Projection for 2028'
            },
            {
                'id': 'GER_SOLAR_GRANT_UTILITY',
                'type': 'grant_capex_percentage',
                'value': 0.05, # 5% of CAPEX as an upfront grant
                'region': 'Germany',
                'technology_scope': ['utility_scale_pv'],
                'start_year': 2025,
                'end_year': 2027,
                'description': 'German grant for utility-scale PV systems'
            },
            {
                'id': 'US_PTC_WIND_2025',
                'type': 'ptc', 
                'value': 0.025, # $/kWh
                'unit': 'USD/kWh',
                'region': 'USA',
                'start_year': 2022,
                'end_year': 2030,
                'technology_scope': ['wind_onshore'],
                'description': 'US Federal Wind Production Tax Credit'
            },
            {
                'id': 'CAL_RPS_2030',
                'type': 'rps',
                'value': 0.60, # 60% RPS target
                'region': 'USA', 
                'applicable_regions': ['California'],
                'target_year': 2030,
                'start_year': 2020,
                'end_year': 2030,
                'technology_scope': ['solar_pv', 'wind_onshore', 'geothermal'],
                'description': 'California RPS: 60% by 2030'
            }
        ]
        self.policy_model = PolicyModel(policies=self.example_policies)

    def test_initialization_and_add_policy(self):
        model = PolicyModel()
        self.assertEqual(len(model.policies), 0)
        test_policy = {'id': 'Test1', 'type': 'test', 'value': 0.1, 'region': 'Global', 'start_year': 2020, 'end_year': 2030}
        model.add_policy(test_policy)
        self.assertEqual(len(model.policies), 1)
        self.assertEqual(model.policies[0]['id'], 'Test1')
        self.assertEqual(len(self.policy_model.policies), 5) # From setUp

    def test_get_active_policies(self):
        # Test active ITC for USA, 2025, solar_pv
        active = self.policy_model.get_active_policies(region='USA', year=2025, policy_type='itc', technology='solar_pv')
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]['id'], 'US_ITC_SOLAR_2025')

        # Test inactive policy (wrong year)
        active_wrong_year = self.policy_model.get_active_policies(region='EU', year=2025, policy_type='carbon_price')
        self.assertEqual(len(active_wrong_year), 0)

        # Test policy with specific applicable_region (California)
        active_cal = self.policy_model.get_active_policies(region='California', year=2025, policy_type='rps')
        self.assertEqual(len(active_cal), 1)
        self.assertEqual(active_cal[0]['id'], 'CAL_RPS_2030')
        
        # Test a general USA policy (US_ITC_SOLAR_2025) when querying for a specific region 'California'.
        # This policy only has region: 'USA' and no 'applicable_regions'.
        # According to current logic, it should NOT be found for 'California' because the model
        # does not infer geographical hierarchy (USA contains California) unless 'California'
        # is explicitly in 'applicable_regions' or the policy's region is 'California' or None.
        active_usa_for_cal = self.policy_model.get_active_policies(region='California', year=2025, policy_type='itc', technology='solar_pv')
        self.assertEqual(len(active_usa_for_cal), 0) # Expect 0, as 'USA' does not automatically cover 'California' here.

    def test_calculate_effective_capex_factor(self):
        # USA Solar PV in 2025 (30% ITC)
        factor = self.policy_model.calculate_effective_capex_factor(region='USA', year=2025, technology='solar_pv')
        self.assertAlmostEqual(factor, 0.70)

        # Germany Utility Scale PV in 2026 (5% grant)
        factor_ger = self.policy_model.calculate_effective_capex_factor(region='Germany', year=2026, technology='utility_scale_pv')
        self.assertAlmostEqual(factor_ger, 0.95)

        # No applicable CAPEX policy
        factor_none = self.policy_model.calculate_effective_capex_factor(region='USA', year=2025, technology='wind_onshore')
        self.assertAlmostEqual(factor_none, 1.0)

    def test_get_carbon_price(self):
        # EU Carbon Price in 2028
        price = self.policy_model.get_carbon_price(region='EU', year=2028)
        self.assertEqual(price, 95)

        # No carbon price (wrong year or region)
        price_none = self.policy_model.get_carbon_price(region='USA', year=2028)
        self.assertEqual(price_none, 0.0)
        price_early = self.policy_model.get_carbon_price(region='EU', year=2027)
        self.assertEqual(price_early, 0.0)

    def test_get_ptc_value(self):
        # USA Wind PTC in 2025
        ptc = self.policy_model.get_ptc_value(region='USA', year=2025, technology='wind_onshore')
        self.assertEqual(ptc, 0.025)

        # No PTC (e.g., for solar)
        ptc_none = self.policy_model.get_ptc_value(region='USA', year=2025, technology='solar_pv')
        self.assertEqual(ptc_none, 0.0)

    def test_get_rps_target(self):
        # California RPS for solar_pv in 2025
        rps = self.policy_model.get_rps_target(region='California', year=2025, technology='solar_pv')
        self.assertIsNotNone(rps)
        self.assertEqual(rps['policy_id'], 'CAL_RPS_2030')
        self.assertEqual(rps['target_percentage'], 0.60)
        self.assertEqual(rps['target_year'], 2030)

        # RPS target year met
        rps_met = self.policy_model.get_rps_target(region='California', year=2030, technology='wind_onshore')
        self.assertIsNotNone(rps_met)
        self.assertEqual(rps_met['target_percentage'], 0.60)

        # No RPS (wrong region or technology not in scope or year out of policy active range)
        rps_none_region = self.policy_model.get_rps_target(region='Texas', year=2025, technology='solar_pv')
        self.assertIsNone(rps_none_region)
        
        rps_none_tech = self.policy_model.get_rps_target(region='California', year=2025, technology='nuclear')
        self.assertIsNone(rps_none_tech)

        # Year after policy end_year
        rps_expired = self.policy_model.get_rps_target(region='California', year=2031, technology='solar_pv')
        self.assertIsNone(rps_expired)
        
        # Year before policy start_year
        rps_too_early = self.policy_model.get_rps_target(region='California', year=2019, technology='solar_pv')
        self.assertIsNone(rps_too_early)

if __name__ == '__main__':
    unittest.main()
