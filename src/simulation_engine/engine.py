# Main simulation engine for the Global Solar Energy Simulation Framework
import pandas as pd
import logging
from typing import Dict, Any, List

# Configure basic logging
# Removed logging.basicConfig call

# Assuming other necessary models are imported from their respective modules
# from ..modules.economic_framework.cost_model import CostModel
# from ..modules.policy_landscape.policy_model import PolicyModel
# from ..modules.technological_evolution.solar_tech_model import SolarTechModel
# from ..modules.supply_chain_dynamics.supply_chain_model import SupplyChainModel
# from ..modules.decision_making.investment_decision_model import InvestmentDecisionModel
# from ..modules.economic_framework.market_model import MarketModel
# from ..modules.grid_integration.grid_model import GridModel
# from ..modules.foundation_elements.data_models import Country # Example data model

class SimulationEngine:
    """
    Manages the overall simulation process, orchestrating interactions between
    various models (economic, technological, policy, etc.) to simulate
    the evolution of the global solar energy landscape over time.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the SimulationEngine with a configuration dictionary.
        The configuration should include:
        - simulation_period (Dict): {'start_year': int, 'end_year': int}
        - regions (List[str]): List of regions to simulate.
        - technologies (List[str]): List of technologies to consider.
        - models (Dict[str, Any]): Pre-initialized instances of all required component models.
        - output_path (str): Path to save simulation results.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SimulationEngine...")
        self.config = config
        self.start_year = config['simulation_period']['start_year']
        self.end_year = config['simulation_period']['end_year']
        self.regions = config['regions']
        self.technologies = config['technologies']

        # Store references to the pre-initialized models
        self.cost_model = config['models'].get('cost_model')
        self.policy_model = config['models'].get('policy_model')
        self.solar_tech_model = config['models'].get('solar_tech_model')
        self.supply_chain_model = config['models'].get('supply_chain_model')
        self.investment_model = config['models'].get('investment_model')
        self.market_model = config['models'].get('market_model')
        self.grid_model = config['models'].get('grid_model')
        # Add other models as needed

        self.output_path = config.get('output_path', 'simulation_results.csv')
        self.results: List[Dict[str, Any]] = [] # To store results from each year

        self._validate_config()
        self.logger.info("SimulationEngine initialized successfully.")

    def _validate_config(self):
        """
        Validates the presence of essential configuration components.
        """
        self.logger.info("Validating configuration...")
        required_models = [
            'cost_model', 'policy_model', 'solar_tech_model',
            'supply_chain_model', 'investment_model', 'market_model', 'grid_model'
        ]
        if not all(model_name in self.config['models'] for model_name in required_models):
            missing = [m for m in required_models if m not in self.config['models']]
            self.logger.error(f"Missing essential models in configuration: {missing}")
            raise ValueError(f"Missing essential models in configuration: {missing}")

        if not self.regions:
            self.logger.error("No regions specified in configuration.")
            raise ValueError("No regions specified in configuration.")

        if not self.technologies:
            self.logger.error("No technologies specified in configuration.")
            raise ValueError("No technologies specified in configuration.")
        self.logger.info("Configuration validated.")


    def run_simulation(self):
        """
        Runs the main simulation loop from the start year to the end year.
        """
        self.logger.info(f"Starting simulation from {self.start_year} to {self.end_year}.")

        for year in range(self.start_year, self.end_year + 1):
            self.logger.info(f"--- Simulating Year: {year} ---")

            # 1. Update all relevant models for the current year
            self._update_models_for_year(year)

            # 2. Make investment decisions for new capacity
            yearly_investments = self._make_investment_decisions(year)

            # 3. Simulate market operations and energy dispatch
            market_outcomes = self._simulate_market_and_dispatch(year, yearly_investments)

            # 4. Update the overall system state based on decisions and market outcomes
            self._update_system_state(year, yearly_investments, market_outcomes)

            # 5. Collect results for the current year
            self._collect_yearly_results(year, yearly_investments, market_outcomes)

            self.logger.info(f"--- Completed Year: {year} ---")

        # 6. Finalize and save all results
        self._finalize_and_save_results()
        self.logger.info("Simulation completed.")

    def _update_models_for_year(self, year: int):
        """
        Updates all component models (costs, tech parameters, policies, etc.)
        for the current simulation year.
        """
        self.logger.info(f"Updating models for year {year}...")

        # These checks ensure that the models exist and have the update method.
        # In a production system, interfaces or base classes might enforce this.

        if self.cost_model and hasattr(self.cost_model, 'update_for_year'):
            self.logger.debug(f"Updating CostModel for year {year}")
            self.cost_model.update_for_year(year, regions=self.regions, technologies=self.technologies)

        if self.policy_model and hasattr(self.policy_model, 'update_for_year'):
            self.logger.debug(f"Updating PolicyModel for year {year}")
            # Policy model might primarily need year and regions, not specific tech details for general updates.
            self.policy_model.update_for_year(year, regions=self.regions)

        if self.solar_tech_model and hasattr(self.solar_tech_model, 'update_for_year'):
            self.logger.debug(f"Updating SolarTechModel for year {year}")
            # Solar tech model updates might be per technology, possibly influenced by global or regional trends.
            self.solar_tech_model.update_for_year(year, technologies=self.technologies)

        if self.supply_chain_model and hasattr(self.supply_chain_model, 'update_for_year'):
            self.logger.debug(f"Updating SupplyChainModel for year {year}")
            self.supply_chain_model.update_for_year(year, regions=self.regions, technologies=self.technologies)

        if self.market_model and hasattr(self.market_model, 'update_for_year'):
            self.logger.debug(f"Updating MarketModel for year {year}")
            # Market model might update demand forecasts, fuel prices, etc.
            self.market_model.update_for_year(year, regions=self.regions)

        if self.grid_model and hasattr(self.grid_model, 'update_for_year'):
            self.logger.debug(f"Updating GridModel for year {year}")
            # Grid model might update existing non-solar capacities, transmission constraints, etc.
            self.grid_model.update_for_year(year, regions=self.regions)

        # TODO: Add calls for other specific models as they are integrated and require annual updates.
        # For example, a ClimateModel for weather data, or a SocioEconomicModel for demographic shifts.

        self.logger.info(f"Model updates for year {year} complete.")

    def _make_investment_decisions(self, year: int) -> Dict[str, Any]:
        """
        Orchestrates investment decisions for new solar and storage capacity
        across regions for the given year.
        Returns a dictionary summarizing investments made, e.g.:
        {'region_x': {'tech_a_mw': 100, 'tech_b_mw': 50}, ...}
        """
        self.logger.info(f"Making investment decisions for year {year}...")

        if self.investment_model and hasattr(self.investment_model, 'decide_investments'):
            try:
                investments = self.investment_model.decide_investments(
                    year=year,
                    regions=self.regions,
                    technologies=self.technologies,
                    cost_model=self.cost_model,
                    policy_model=self.policy_model,
                    solar_tech_model=self.solar_tech_model,
                    market_model=self.market_model, # For demand signals, price forecasts
                    grid_model=self.grid_model,     # For existing capacity, connection constraints
                    supply_chain_model=self.supply_chain_model # For manufacturing capacity limits
                )
                self.logger.info(f"Investment decisions for year {year}: {investments}")
                return investments if investments is not None else {}
            except Exception as e:
                self.logger.error(f"Error during investment decision making for year {year}: {e}", exc_info=True)
                return {}
        else:
            self.logger.warning(
                f"InvestmentModel not found or 'decide_investments' method missing. "
                f"No investment decisions will be made for year {year}."
            )
            return {}

    def _simulate_market_and_dispatch(self, year: int, investments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates energy market operations, dispatch, and determines outcomes
        like generation mix, prices, curtailment, etc., for the given year
        considering new investments.
        Returns a dictionary of market outcomes, e.g.:
        {'region_x': {'total_generation_gwh': 5000, 'avg_price_mwh': 45}, ...}
        """
        self.logger.info(f"Simulating market and dispatch for year {year} with investments: {investments}")

        if self.market_model and hasattr(self.market_model, 'simulate_dispatch_for_year'):
            try:
                market_outcomes = self.market_model.simulate_dispatch_for_year(
                    year=year,
                    regions=self.regions,
                    grid_model=self.grid_model, # Provides current grid state
                    new_investments=investments, # New capacities to be considered in dispatch
                    solar_tech_model=self.solar_tech_model,
                    cost_model=self.cost_model # Added cost_model instance
                )
                self.logger.info(f"Market outcomes for year {year}: {market_outcomes}")
                return market_outcomes if market_outcomes is not None else {}
            except TypeError as e:
                self.logger.error(f"Error during market simulation for year {year}: {e}", exc_info=True)
                return {}
        else:
            self.logger.warning(
                f"MarketModel not found or 'simulate_dispatch_for_year' method missing. "
                f"Market simulation will be skipped for year {year}."
            )
            return {}

    def _update_system_state(self, year: int, investments: Dict[str, Any], market_outcomes: Dict[str, Any]):
        """
        Updates the overall system state after investments and market simulation.
        This includes adding new capacities to the grid and updating cumulative metrics.
        """
        self.logger.info(f"Updating system state for year {year}...")

        # 1. Update GridModel with new capacities
        if self.grid_model and hasattr(self.grid_model, 'add_new_capacity'):
            if investments: # Only if there are actual investments
                try:
                    # Assuming 'investments' is structured appropriately for add_new_capacity
                    # e.g., {'region_A': {'tech_X_mw': 100, 'tech_Y_mw': 50}, ...}
                    self.grid_model.add_new_capacity(year=year, new_capacity_details=investments)
                    self.logger.info(f"GridModel updated with new capacities from year {year} investments.")
                except Exception as e:
                    self.logger.error(f"Error updating GridModel with new capacity for year {year}: {e}", exc_info=True)
            else:
                self.logger.info(f"No new investments in year {year} to add to GridModel.")
        elif investments:
            self.logger.warning(
                f"GridModel not found or 'add_new_capacity' method missing, but investments were made. "
                f"New capacities for year {year} cannot be added to the grid state."
            )

        # 2. Update other cumulative system state variables (examples)
        # These would typically be attributes of SimulationEngine or managed by dedicated state trackers.
        # For example, if tracking cumulative capacity:
        # if not hasattr(self, 'cumulative_capacity_mw'):
        #     self.cumulative_capacity_mw: Dict[str, Dict[str, float]] = {r: {t: 0.0 for t in self.technologies} for r in self.regions}
        # for region, tech_investments in investments.items():
        #     for tech, mw_added in tech_investments.items():
        #         if region in self.cumulative_capacity_mw and tech in self.cumulative_capacity_mw[region]:
        #             self.cumulative_capacity_mw[region][tech] += mw_added
        #         else:
        #             self.logger.warning(f"Could not update cumulative capacity for unknown region/tech: {region}/{tech}")

        # For example, if tracking cumulative emissions based on market_outcomes:
        # if 'emissions_tons_co2' in market_outcomes:
        #     if not hasattr(self, 'total_emissions_tons_co2'):
        #         self.total_emissions_tons_co2 = 0.0
        #     self.total_emissions_tons_co2 += market_outcomes['emissions_tons_co2']
        #     self.logger.info(f"Cumulative CO2 emissions updated: {self.total_emissions_tons_co2} tons.")

        self.logger.info(f"System state update for year {year} complete.")

    def _collect_yearly_results(self, year: int, investments: Dict[str, Any], market_outcomes: Dict[str, Any]):
        """
        Gathers key metrics from the year's simulation and appends to self.results.
        """
        self.logger.info(f"Collecting results for year {year}...")

        # Basic structure for yearly results
        yearly_data = {
            "year": year,
            "investments": investments,  # Contains detailed investment breakdown
            "market_outcomes": market_outcomes  # Contains detailed market simulation results
        }

        # --- Example: Add specific metrics from component models ---
        # You might want to extract and flatten specific important metrics here
        # for easier analysis later, rather than just storing the whole dictionaries.

        # From CostModel (example - assuming such methods exist)
        # if self.cost_model and hasattr(self.cost_model, 'get_LCOE_summary'):
        #     yearly_data['lcoe_summary'] = self.cost_model.get_LCOE_summary(year, self.regions, self.technologies)

        # From GridModel (example)
        # if self.grid_model and hasattr(self.grid_model, 'get_capacity_summary'):
        #     yearly_data['grid_capacity_summary'] = self.grid_model.get_capacity_summary(year, self.regions)
        
        # From SupplyChainModel (example)
        # if self.supply_chain_model and hasattr(self.supply_chain_model, 'get_material_shortfall_summary'):
        #     yearly_data['material_shortfalls'] = self.supply_chain_model.get_material_shortfall_summary(year)

        # From PolicyModel (example)
        # if self.policy_model and hasattr(self.policy_model, 'get_active_incentives_summary'):
        #     yearly_data['active_incentives'] = self.policy_model.get_active_incentives_summary(year, self.regions)
            
        # Append the structured yearly data to the main results list
        self.results.append(yearly_data)
        self.logger.debug(f"Collected data for year {year}: {yearly_data}")

    def _finalize_and_save_results(self):
        """
        Processes all collected results and saves them, e.g., to a CSV file.
        """
        self.logger.info("Finalizing and saving simulation results...")
        self.logger.debug(f"Number of records in self.results before saving: {len(self.results)}")
        if not self.results:
            self.logger.warning("No results to save.")
            return
        
        try:
            results_df = pd.DataFrame(self.results)
            self.logger.debug(f"DataFrame created with shape: {results_df.shape}")
            results_df.to_csv(self.output_path, index=False)
            self.logger.info(f"Results saved to {self.output_path}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            # Optionally, try to save as a different format or log the data directly
            # print("Raw results data:", self.results)

if __name__ == '__main__':
    # This is an example of how the SimulationEngine might be configured and run.
    # In a real scenario, model instances would be properly initialized with data.
    
    # --- Mock Model Classes (for demonstration purposes) ---
    class MockModel:
        def __init__(self, name="MockModel"):
            self.name = name
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"{self.name} initialized.")
        def update_for_year(self, year, *args, **kwargs):
            self.logger.info(f"{self.name} updated for year {year}.")
        def decide_investments(self, year, *args, **kwargs):
            self.logger.info(f"{self.name} making investment decisions for year {year}.")
            # Example: return {region: {tech: val} for region in kwargs.get('regions', []) for tech in kwargs.get('technologies', [])} # More detailed placeholder
            return {f"{self.name.lower().replace('model', '')}_invest_mw_region_{region.split('_')[-1].lower()}_tech_generic": (100 + year % 10) for region in kwargs.get('regions', ['default_region'])}

        def simulate_dispatch_for_year(self, year, regions, grid_model, new_investments, *args, **kwargs):
            self.logger.info(f"{self.name} simulating dispatch for year {year} in regions {regions} considering investments {new_investments} and grid: {grid_model.name if grid_model else 'N/A'}.")
            # Example: return {region: {'generated_gwh': (500 + year % 10), 'avg_price_mwh': (40 + year % 5)} for region in regions}
            return {f"market_gen_gwh_region_{region.split('_')[-1].lower()}": (500 + year % 10) for region in regions}

        def add_new_capacity(self, year, new_capacity_details, *args, **kwargs):
            self.logger.info(f"{self.name} (as GridModel) adding new capacity for year {year}: {new_capacity_details}")
            # This method would typically update internal state of the GridModel
            # For MockModel, just log the action.
            pass

        # Kept simulate_year for other potential uses or if some mock models use it generically
        def simulate_year(self, year, *args, **kwargs):
            self.logger.info(f"{self.name} (generic simulate_year) simulating for year {year}.")
            return {f"{self.name.lower()}_energy_gwh": 500 * year} 

    logging.info("--- Setting up Example Simulation ---")
    example_config = {
        'simulation_period': {'start_year': 2025, 'end_year': 2027}, # Short period for example
        'regions': ['USA_California', 'EU_Germany', 'China_Jiangsu'],
        'technologies': ['SolarPV_Utility_TOPCon', 'Storage_LiIon_4hr'],
        'models': {
            'cost_model': MockModel(name="CostModel"),
            'policy_model': MockModel(name="PolicyModel"),
            'solar_tech_model': MockModel(name="SolarTechModel"),
            'supply_chain_model': MockModel(name="SupplyChainModel"),
            'investment_model': MockModel(name="InvestmentModel"),
            'market_model': MockModel(name="MarketModel"),
            'grid_model': MockModel(name="GridModel")
        },
        'output_path': 'example_simulation_results.csv'
    }
    
    try:
        engine = SimulationEngine(config=example_config)
        engine.run_simulation()
        logging.info("--- Example Simulation Finished ---")
    
        # Verify if results file was created (optional)
        try:
            results_data = pd.read_csv(example_config['output_path'])
            logging.info(f"Successfully read back results from {example_config['output_path']}:\n{results_data.head()}")
        except FileNotFoundError:
            logging.error(f"Output file {example_config['output_path']} not found after simulation.")
        except Exception as e:
            logging.error(f"Error reading output file: {e}")
    
    except ValueError as ve:
        logging.error(f"Configuration error: {ve}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during the example simulation: {e}", exc_info=True)
    
    print("Simulation finished.")

if __name__ == '__main__':
    # Example usage (to be expanded based on actual configuration needs)
    print("Attempting to run SimulationEngine example...")
    # This is a placeholder. Actual configuration will be more complex.
    example_config = {
        'simulation_period': (2023, 2050),
        'time_step_years': 1,
        'technologies': ['MonocrystallineSilicon', 'ThinFilmCadTel'],
        'regions': ['USA', 'China']
    }
    engine = SimulationEngine(config=example_config)
    engine.run_simulation()
    print("SimulationEngine example completed.")
