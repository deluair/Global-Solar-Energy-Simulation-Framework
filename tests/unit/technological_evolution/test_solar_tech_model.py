import unittest
import sys
import os

# Add src directory to Python path to import modules
# __file__ is .../tests/unit/technological_evolution/test_solar_tech_model.py
# os.path.dirname(__file__) is .../tests/unit/technological_evolution
# os.path.join(os.path.dirname(__file__), '..', '..', '..') navigates up to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(project_root, 'src'))

from modules.technological_evolution.solar_tech_model import SolarTechnology, SolarTechModel

class TestSolarTechnology(unittest.TestCase):

    def setUp(self):
        self.tech_topcon = SolarTechnology(
            name='TestTOPCon',
            base_efficiency=0.22,
            projected_efficiency_2035=0.26,
            start_year=2023,
            commercial_scale_year=2022,
            degradation_rate_annual=0.004,
            base_capex_usd_per_kw=700,
            annual_capex_reduction_rate=0.03
        )
        self.tech_emerging = SolarTechnology(
            name='EmergingTech',
            base_efficiency=0.30,
            projected_efficiency_2035=0.40, # High projection
            start_year=2028,
            commercial_scale_year=2030,
            degradation_rate_annual=0.008,
            base_capex_usd_per_kw=1200,
            annual_capex_reduction_rate=0.05
        )

    def test_initialization(self):
        self.assertEqual(self.tech_topcon.name, 'TestTOPCon')
        self.assertEqual(self.tech_topcon.base_efficiency, 0.22)
        self.assertEqual(self.tech_topcon.annual_capex_reduction_rate, 0.03)
        # Check annual_efficiency_improvement calculation (2035-2023 = 12 years)
        # (0.26 - 0.22) / 12 = 0.04 / 12 
        self.assertAlmostEqual(self.tech_topcon.annual_efficiency_improvement, 0.04 / 12, places=6)

    def test_get_params_for_year_efficiency(self):
        # Before start year
        params_2022 = self.tech_topcon.get_params_for_year(2022)
        self.assertEqual(params_2022['efficiency'], 0.22) # Uses base_efficiency

        # At start year
        params_2023 = self.tech_topcon.get_params_for_year(2023)
        self.assertEqual(params_2023['efficiency'], 0.22)

        # Mid-range year (2023 + 5 = 2028)
        expected_eff_2028 = 0.22 + ( (0.04/12) * 5 )
        params_2028 = self.tech_topcon.get_params_for_year(2028)
        self.assertAlmostEqual(params_2028['efficiency'], expected_eff_2028, places=4)

        # At 2035 (projected_efficiency_2035)
        params_2035 = self.tech_topcon.get_params_for_year(2035)
        self.assertEqual(params_2035['efficiency'], 0.26)

        # After 2035 (should be capped at projected_efficiency_2035)
        params_2040 = self.tech_topcon.get_params_for_year(2040)
        self.assertEqual(params_2040['efficiency'], 0.26)

    def test_get_params_for_year_capex(self):
        # Before start year
        params_2022 = self.tech_topcon.get_params_for_year(2022)
        self.assertEqual(params_2022['capex_usd_per_kw'], 700) # Uses base_capex

        # At start year (0 years reduction)
        params_2023 = self.tech_topcon.get_params_for_year(2023)
        self.assertEqual(params_2023['capex_usd_per_kw'], 700)

        # Mid-range year (2023 + 5 = 2028)
        expected_capex_2028 = 700 * ((1 - 0.03) ** 5)
        params_2028 = self.tech_topcon.get_params_for_year(2028)
        self.assertAlmostEqual(params_2028['capex_usd_per_kw'], expected_capex_2028, places=2)

        # Capex for emerging tech
        params_emerging_2030 = self.tech_emerging.get_params_for_year(2030)
        # 2030 is 2 years after start_year 2028
        expected_capex_emerging_2030 = 1200 * ((1-0.05)**2)
        self.assertAlmostEqual(params_emerging_2030['capex_usd_per_kw'], expected_capex_emerging_2030, places=2)

    def test_commercial_availability(self):
        self.assertFalse(self.tech_emerging.get_params_for_year(2029)['is_commercially_available'])
        self.assertTrue(self.tech_emerging.get_params_for_year(2030)['is_commercially_available'])
        self.assertTrue(self.tech_topcon.get_params_for_year(2022)['is_commercially_available'])


class TestSolarTechModel(unittest.TestCase):

    def setUp(self):
        self.stm = SolarTechModel()
        self.tech1 = SolarTechnology(
            name='TechA',
            base_efficiency=0.20, projected_efficiency_2035=0.25, start_year=2024,
            commercial_scale_year=2024, base_capex_usd_per_kw=800, annual_capex_reduction_rate=0.02
        )
        self.tech2 = SolarTechnology(
            name='TechB_Future',
            base_efficiency=0.28, projected_efficiency_2035=0.35, start_year=2027,
            commercial_scale_year=2029, base_capex_usd_per_kw=1000, annual_capex_reduction_rate=0.04
        )
        self.stm.add_technology(self.tech1)
        self.stm.add_technology(self.tech2)

    def test_add_technology(self):
        self.assertIn('TechA', self.stm.technologies)
        self.assertEqual(self.stm.technologies['TechA'].name, 'TechA')

    def test_get_technology_details_exists(self):
        details = self.stm.get_technology_details('TechA', 2025)
        self.assertEqual(details['name'], 'TechA')
        self.assertEqual(details['year'], 2025)
        self.assertTrue(details['is_commercially_available'])
        # Expected efficiency for TechA in 2025 (1 year after start)
        # 0.20 + ( (0.25-0.20)/(2035-2024) * 1 )
        # (0.05 / 11) * 1 = 0.004545...
        expected_eff_2025_tech_a = 0.20 + (0.05/11.0)
        self.assertAlmostEqual(details['efficiency'], expected_eff_2025_tech_a, places=4)
        # Expected CAPEX for TechA in 2025 (1 year after start)
        expected_capex_2025_tech_a = 800 * (0.98**1)
        self.assertAlmostEqual(details['capex_usd_per_kw'], expected_capex_2025_tech_a, places=2)

    def test_get_technology_details_not_exists(self):
        details = self.stm.get_technology_details('NonExistentTech', 2025)
        self.assertIn('error', details)
        self.assertEqual(details['error'], "Technology 'NonExistentTech' not found.")

    def test_list_technologies_all(self):
        tech_list = self.stm.list_technologies()
        self.assertIn('TechA', tech_list)
        self.assertIn('TechB_Future', tech_list)
        self.assertEqual(len(tech_list), 2)

    def test_list_technologies_commercially_available(self):
        # Year 2025: TechA available, TechB_Future not
        available_2025 = self.stm.list_technologies(year=2025)
        self.assertIn('TechA', available_2025)
        self.assertNotIn('TechB_Future', available_2025)
        self.assertEqual(len(available_2025), 1)

        # Year 2029: Both available
        available_2029 = self.stm.list_technologies(year=2029)
        self.assertIn('TechA', available_2029)
        self.assertIn('TechB_Future', available_2029)
        self.assertEqual(len(available_2029), 2)

        # Year 2023: None available by commercial_scale_year criteria
        # TechA commercial_scale_year=2024, TechB_Future commercial_scale_year=2029
        available_2023 = self.stm.list_technologies(year=2023)
        self.assertEqual(len(available_2023), 0)

if __name__ == '__main__':
    unittest.main()
