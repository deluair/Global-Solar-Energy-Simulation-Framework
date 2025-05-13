import logging
import os
import pandas as pd
from datetime import datetime
import glob

# Module imports (adjust paths if necessary based on execution context)
from src.modules.economic_framework.cost_model import CostModel
from src.modules.policy_landscape.policy_model import PolicyModel
from src.modules.technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology # Assuming SolarTechnology might be needed for config
from src.modules.supply_chain_dynamics.supply_chain_model import SupplyChainModel
from src.modules.decision_making.investment_decision_model import InvestmentDecisionModel
from src.modules.economic_framework.market_model import MarketSimulator # Assuming MarketModel is MarketSimulator
from src.modules.grid_integration.grid_model import GridModel
from src.simulation_engine.engine import SimulationEngine

# Configure basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s')

# Dummy CarbonPricingMechanism for InvestmentDecisionModel
class DummyCarbonPricingMechanism:
    def get_carbon_price(self, region: str, year: int) -> float:
        """Returns a placeholder carbon price."""
        # Example: A simple fixed carbon price, or could vary by region/year
        if region == "EU_Germany":
            return 50.0 # EUR per ton CO2
        return 25.0 # USD per ton CO2 for other regions

def get_sample_simulation_config() -> dict:
    """Prepares a sample configuration for the SimulationEngine."""
    logging.info("Preparing simulation configuration...")

    # --- 1. Initialize Models --- 
    # These are placeholders. Actual initialization will require specific data/parameters.

    # SolarTechModel
    logging.info("Initializing SolarTechModel...")
    solar_tech_model = SolarTechModel() 
    # Add specific technologies for the simulation
    # Parameters are adjusted to match SolarTechnology.__init__ signature
    technologies_to_simulate = {
        "TOPCon_PV": SolarTechnology(
            name="TOPCon_PV", 
            base_efficiency=0.24, 
            projected_efficiency_2035=0.24 + (0.003 * (2035 - 2022)), # Calculate based on old rate
            start_year=2022, 
            commercial_scale_year=2022, 
            degradation_rate_annual=0.004,
            base_capex_usd_per_kw=650,
            annual_capex_reduction_rate=0.02 # Example annual reduction
        ),
        "AdvancedMonocrystallineSilicon": SolarTechnology(
            name="AdvancedMonocrystallineSilicon", 
            base_efficiency=0.23, 
            projected_efficiency_2035=0.23 + (0.005 * (2035 - 2020)),
            start_year=2020, 
            commercial_scale_year=2020, 
            degradation_rate_annual=0.005,
            base_capex_usd_per_kw=700,
            annual_capex_reduction_rate=0.025 # Example
        ),
        "LFP_Battery": SolarTechnology(
            name="LFP_Battery", 
            base_efficiency=0.90, # Assuming round-trip for batteries
            projected_efficiency_2035=0.90 + (0.001 * (2035 - 2018)),
            start_year=2018, 
            commercial_scale_year=2018, 
            degradation_rate_annual=0.01, 
            base_capex_usd_per_kw=400, # Note: Battery costs often also in USD/kWh
            annual_capex_reduction_rate=0.03 # Example
        )
    }
    for tech_name, tech_obj in technologies_to_simulate.items():
        solar_tech_model.add_technology(tech_obj)
    logging.info(f"SolarTechModel populated with: {list(technologies_to_simulate.keys())}")

    # SupplyChainModel
    logging.info("Initializing SupplyChainModel...")
    # Uses default initial_data from its own definition for now
    supply_chain_model = SupplyChainModel()

    # CostModel 
    logging.info("Initializing CostModel...")
    # Initialize CostModel for a primary/reference technology from our list, e.g., TOPCon_PV
    # The CostModel's update_for_year method will need to be robust enough to handle
    # the list of technologies passed by the SimulationEngine, potentially using SolarTechModel
    # to get base parameters for each technology it needs to update costs for.
    primary_tech_for_cost_model = "TOPCon_PV"
    
    # Define values for learning_rate and initial_production_volume separately
    lr_for_primary_tech = 0.20  # Learning rate for TOPCon_PV
    initial_prod_vol_for_primary_tech = 50.0  # Initial cumulative production in GW

    initial_costs_dict_for_primary_tech = {
        'module_usd_per_kw': technologies_to_simulate[primary_tech_for_cost_model].base_capex_usd_per_kw, # Using STM base_capex
        'bos_usd_per_kw': 120, 
        'inverter_usd_per_kw': 80, 
        'installation_usd_per_kw': 150, 
        'opex_per_kw_year': 15
        # learning_rate and initial_cumulative_production_gw are now passed as separate args
    }
    
    cost_model = CostModel(
        technology_name=primary_tech_for_cost_model, 
        initial_costs=initial_costs_dict_for_primary_tech, 
        learning_rate=lr_for_primary_tech,  # Passed as a direct argument
        initial_production_volume=initial_prod_vol_for_primary_tech,  # Passed as a direct argument
        supply_chain_model=supply_chain_model,
        solar_tech_model=solar_tech_model # This will still cause error until CostModel.__init__ is updated
    )

    # PolicyModel
    logging.info("Initializing PolicyModel...")
    policy_model = PolicyModel()
    logging.info(f"PolicyModel initialized with {len(policy_model.policies)} policies.")

    # MarketSimulator (MarketModel) - Initialize before InvestmentDecisionModel
    logging.info("Initializing MarketSimulator...")
    market_designs = {
        'USA': {'type': 'energy_only', 'base_energy_price_usd_per_mwh': 40},
        'China': {'type': 'capacity_market', 'base_energy_price_usd_per_mwh': 35, 'capacity_payment_usd_per_kw_year': 50},
        'EU_Germany': {'type': 'energy_only', 'base_energy_price_usd_per_mwh': 50, 'tou_factors': {'peak': 1.5, 'off_peak': 0.8}}
    }
    market_model = MarketSimulator(market_designs=market_designs)

    # Dummy Carbon Pricing Model instance
    logging.info("Initializing DummyCarbonPricingMechanism...")
    carbon_pricing_model_instance = DummyCarbonPricingMechanism()

    # InvestmentDecisionModel
    logging.info("Initializing InvestmentDecisionModel...")
    investment_decision_model = InvestmentDecisionModel(
        solar_tech_model=solar_tech_model,
        cost_model=cost_model, 
        market_simulator=market_model, # Pass initialized market_model
        carbon_pricing_model=carbon_pricing_model_instance # Pass dummy carbon pricing model
    )

    # GridModel
    logging.info("Initializing GridModel...")
    # Ensure this data structure matches what the new GridModel.__init__ expects
    initial_grid_config_data = {
        'USA': {
            'existing_capacity_mw': 500000, 
            'current_load_mw': 450000, # Example: 90% of capacity
            'max_solar_penetration_pct': 0.6, 
            'base_interconnection_cost_usd_per_mw': 120000 
        },
        'China': {
            'existing_capacity_mw': 1200000, 
            'current_load_mw': 1000000, 
            # Will use default for other params like max_solar_penetration_pct, etc.
        },
        'EU_Germany': {
            'existing_capacity_mw': 150000,
            'current_load_mw': 130000, 
            'base_interconnection_cost_usd_per_mw': 90000,
            'max_solar_penetration_pct': 0.55
        }
        # Add other regions as needed, ensuring 'current_load_mw' is present
    }
    # The argument name here must match what GridModel.__init__ now expects
    grid_model = GridModel(initial_regional_data=initial_grid_config_data) 

    # --- 2. Assemble Configuration for SimulationEngine --- 
    simulation_config = {
        'simulation_period': {'start_year': 2025, 'end_year': 2030}, # Shorter for testing
        'regions': ['USA', 'China', 'EU_Germany'],
        'technologies': list(technologies_to_simulate.keys()), # Use keys from our defined techs
        'models': {
            'cost_model': cost_model,
            'policy_model': policy_model,
            'solar_tech_model': solar_tech_model,
            'supply_chain_model': supply_chain_model,
            'investment_model': investment_decision_model,
            'market_model': market_model,
            'grid_model': grid_model
        },
        'output_path': os.path.join(os.getcwd(), f'full_simulation_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    }

    logging.info("Simulation configuration prepared.")
    return simulation_config

def main():
    """Main function to set up and run the full simulation."""
    try:
        config = get_sample_simulation_config()
        
        logging.info("Initializing SimulationEngine...")
        engine = SimulationEngine(config=config)
        
        logging.info("Starting full simulation run...")
        engine.run_simulation()
        
        logging.info("Verifying existence of results CSV file...")
        output_filename_pattern = f"full_simulation_results_{config['simulation_period']['start_year']}" # More general pattern
        
        cwd = os.getcwd()
        logging.info(f"Checking for results files in: {cwd}")
        
        # Using glob to find files matching the pattern
        found_files = []
        for file_path in glob.glob(os.path.join(cwd, "full_simulation_results_*.csv")):
            found_files.append(os.path.basename(file_path))
            
        if found_files:
            logging.info(f"Found results CSV files: {found_files}")
            for f_name in found_files:
                # Optionally, read and print a few lines if desired for quick verification
                # For now, just confirming existence is enough.
                pass # Placeholder if we want to add reading later
        else:
            logging.warning(f"Could not find any files matching 'full_simulation_results_*.csv' in {cwd}.")

        logging.info(f"Full simulation completed. Results saved to: {config['output_path']}")

    except Exception as e:
        logging.error(f"An error occurred during the simulation setup or run: {e}", exc_info=True)
        # exc_info=True will log the full traceback

if __name__ == '__main__':
    main()
