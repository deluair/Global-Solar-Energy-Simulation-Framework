import unittest
from unittest.mock import MagicMock, patch
import copy

from src.modules.economic_framework.cost_model import CostModel
# We might need SupplyChainModel for type hinting or if we pass a real one in some tests,
# but mostly we'll mock its methods where CostModel interacts with it.
from src.modules.supply_chain_dynamics.supply_chain_model import SupplyChainModel, initial_data as scm_initial_data

class TestCostModel(unittest.TestCase):

    def setUp(self):
        self.initial_costs_pv = {
            'module_usd_per_kw': 200,
            'bos_usd_per_kw': 150,
            'inverter_usd_per_kw': 100,
            'installation_usd_per_kw': 150,
            'opex_per_kw_year': 20
        }
        # Cost model calculates capex_per_kw initially: 200+150+100+150 = 600
        self.cost_model_pv = CostModel(
            technology_name='TestSolarPV',
            initial_costs=self.initial_costs_pv,
            learning_rate=0.1,
            initial_production_volume=10
        )

        # A mock SupplyChainModel instance
        self.mock_scm = MagicMock(spec=SupplyChainModel)
        # Setup some default return values for mocked SCM methods to avoid NoneErrors if not overridden by a specific test
        self.mock_scm.supply_data = copy.deepcopy(scm_initial_data) # Give it some data to look up items
        self.mock_scm.get_material_availability.return_value = {'available': True, 'surplus': 1000000}
        self.mock_scm.get_concentration_risk.return_value = {'hhi': 1000, 'assessment': 'Unconcentrated'}

    def test_cost_model_initialization(self):
        self.assertEqual(self.cost_model_pv.technology_name, 'TestSolarPV')
        self.assertEqual(self.cost_model_pv.current_costs['module_usd_per_kw'], 200)
        self.assertEqual(self.cost_model_pv.current_costs['capex_per_kw'], 600)
        self.assertIsNone(self.cost_model_pv.supply_chain_model)

    def test_cost_model_initialization_with_scm(self):
        cost_model_with_scm = CostModel(
            technology_name='TestSolarPVSCM',
            initial_costs=self.initial_costs_pv,
            learning_rate=0.1,
            supply_chain_model=self.mock_scm
        )
        self.assertIsNotNone(cost_model_with_scm.supply_chain_model)
        self.assertEqual(cost_model_with_scm.supply_chain_model, self.mock_scm)

    def test_adjust_costs_no_scm_associated(self):
        initial_module_cost = self.cost_model_pv.current_costs['module_usd_per_kw']
        self.cost_model_pv.adjust_costs_based_on_supply_chain()
        self.assertEqual(self.cost_model_pv.current_costs['module_usd_per_kw'], initial_module_cost)
        # Check logs or print statements if important, though direct state change is primary here

    def test_adjust_costs_module_cost_key_missing(self):
        cm_no_module = CostModel(
            technology_name='TestNoModule',
            initial_costs={'bos_usd_per_kw': 100, 'opex_per_kw_year': 10},
            learning_rate=0.1,
            supply_chain_model=self.mock_scm
        )
        # Store a copy of costs because adjust_costs might try to update capex if module_usd_per_kw was there
        original_costs_copy = copy.deepcopy(cm_no_module.current_costs)
        cm_no_module.adjust_costs_based_on_supply_chain()
        self.assertEqual(cm_no_module.current_costs, original_costs_copy)

    def test_adjust_costs_material_not_in_scm_data(self):
        cost_model_with_scm = CostModel(
            technology_name='TestSolarPVSCM',
            initial_costs=self.initial_costs_pv,
            learning_rate=0.1,
            supply_chain_model=self.mock_scm
        )
        initial_module_cost = cost_model_with_scm.current_costs['module_usd_per_kw']
        
        # Make mock_scm.supply_data not contain 'non_existent_material'
        self.mock_scm.supply_data = {}

        cost_model_with_scm.adjust_costs_based_on_supply_chain(material_item_name='non_existent_material')
        self.assertEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], initial_module_cost)

    def test_adjust_costs_module_item_not_in_scm_data_for_concentration(self):
        cost_model_with_scm = CostModel(
            technology_name='TestSolarPVSCM',
            initial_costs=self.initial_costs_pv,
            learning_rate=0.1,
            supply_chain_model=self.mock_scm
        )
        initial_module_cost = cost_model_with_scm.current_costs['module_usd_per_kw']
        
        # Mock get_concentration_risk to simulate item not found
        self.mock_scm.get_concentration_risk.return_value = {'hhi': -1, 'assessment': 'Data not found', 'error': 'Item not found'}

        cost_model_with_scm.adjust_costs_based_on_supply_chain(module_item_name='non_existent_module')
        # Even if material check passes, concentration check fails gracefully
        self.assertEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], initial_module_cost)

    # --- Tests for Material Availability Risk --- 
    def test_adjust_costs_material_shortfall_low_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        self.mock_scm.get_material_availability.return_value = {'available': False, 'shortfall': 0.1 * (scm_initial_data['polysilicon']['global_capacity_tons_per_year'] * CostModel.DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL)}
        expected_increase = CostModel.MATERIAL_SHORTFALL_LOW_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))

    def test_adjust_costs_material_shortfall_medium_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        self.mock_scm.get_material_availability.return_value = {'available': False, 'shortfall': 0.3 * (scm_initial_data['polysilicon']['global_capacity_tons_per_year'] * CostModel.DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL)}
        expected_increase = CostModel.MATERIAL_SHORTFALL_MEDIUM_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))

    def test_adjust_costs_material_shortfall_high_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        self.mock_scm.get_material_availability.return_value = {'available': False, 'shortfall': 0.6 * (scm_initial_data['polysilicon']['global_capacity_tons_per_year'] * CostModel.DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL)}
        expected_increase = CostModel.MATERIAL_SHORTFALL_HIGH_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))

    def test_adjust_costs_material_tight_surplus_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        # Surplus is less than 10% of global capacity (e.g. 5%)
        self.mock_scm.get_material_availability.return_value = {'available': True, 'surplus': 0.05 * scm_initial_data['polysilicon']['global_capacity_tons_per_year']}
        expected_increase = CostModel.MATERIAL_TIGHT_SURPLUS_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))
    
    def test_adjust_costs_material_zero_global_capacity(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        # Modify mock_scm.supply_data for this test case
        self.mock_scm.supply_data['polysilicon']['global_capacity_tons_per_year'] = 0
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        # Expect no change as material availability cannot be assessed, warning printed
        self.assertEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost)
        # Restore for other tests (though setUp does this, good practice if tests run in non-guaranteed order)
        self.mock_scm.supply_data = copy.deepcopy(scm_initial_data)

    # --- Tests for Market Concentration Risk --- 
    def test_adjust_costs_concentration_moderate_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        self.mock_scm.get_concentration_risk.return_value = {'hhi': 2000, 'assessment': 'Moderately concentrated'}
        expected_increase = CostModel.CONCENTRATION_MODERATE_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))

    def test_adjust_costs_concentration_high_impact(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        self.mock_scm.get_concentration_risk.return_value = {'hhi': 3000, 'assessment': 'Highly concentrated'}
        expected_increase = CostModel.CONCENTRATION_HIGH_IMPACT_PCT
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_increase))

    # --- Test for Combined Risks --- 
    def test_adjust_costs_combined_material_shortfall_and_high_concentration(self):
        cost_model_with_scm = CostModel('TestPV', self.initial_costs_pv, 0.1, supply_chain_model=self.mock_scm)
        # High material shortfall
        self.mock_scm.get_material_availability.return_value = {'available': False, 'shortfall': 0.6 * (scm_initial_data['polysilicon']['global_capacity_tons_per_year'] * CostModel.DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL)}
        material_increase = CostModel.MATERIAL_SHORTFALL_HIGH_IMPACT_PCT
        # High concentration risk
        self.mock_scm.get_concentration_risk.return_value = {'hhi': 3000, 'assessment': 'Highly concentrated'}
        concentration_increase = CostModel.CONCENTRATION_HIGH_IMPACT_PCT
        
        expected_total_increase = material_increase + concentration_increase
        original_cost = self.initial_costs_pv['module_usd_per_kw']
        
        cost_model_with_scm.adjust_costs_based_on_supply_chain()
        self.assertAlmostEqual(cost_model_with_scm.current_costs['module_usd_per_kw'], original_cost * (1 + expected_total_increase))

if __name__ == '__main__':
    unittest.main()
