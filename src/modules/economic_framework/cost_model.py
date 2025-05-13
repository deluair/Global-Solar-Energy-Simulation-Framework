"""
Models cost structures, learning curves, and financing mechanisms for solar and storage technologies.
Tracks component costs and region-specific manufacturing advantages.
"""

import math
from typing import Dict, Any, Optional
import logging

# Import SupplyChainModel
from ..supply_chain_dynamics.supply_chain_model import SupplyChainModel

# For type hinting SolarTechModel if it's in a different module
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..technological_evolution.solar_tech_model import SolarTechModel # Adjusted import path

class CostModel:
    """A class to model cost structures, learning curves, and LCOE for energy technologies."""
    CAPEX_COMPONENT_KEYS = ['module_usd_per_kw', 'bos_usd_per_kw', 'inverter_usd_per_kw', 'installation_usd_per_kw']

    # Constants for supply chain adjustment logic
    DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL = 0.5
    MATERIAL_SHORTFALL_LOW_IMPACT_PCT = 0.02
    MATERIAL_SHORTFALL_MEDIUM_IMPACT_PCT = 0.07
    MATERIAL_SHORTFALL_HIGH_IMPACT_PCT = 0.15
    MATERIAL_TIGHT_SURPLUS_IMPACT_PCT = 0.01
    CONCENTRATION_MODERATE_IMPACT_PCT = 0.02
    CONCENTRATION_HIGH_IMPACT_PCT = 0.07

    def __init__(self, technology_name: str, initial_costs: dict, learning_rate: float, initial_production_volume: float = 1.0, supply_chain_model: Optional[SupplyChainModel] = None, solar_tech_model: Optional['SolarTechModel'] = None):
        """
        Initializes CostModel with technology-specific cost data and learning parameters.
        initial_costs: e.g., {'module_usd_per_kw': 300, 'bos_usd_per_kw': 400, ... , 'opex_per_kw_year': 50}
                       It should contain keys from CAPEX_COMPONENT_KEYS.
                       'capex_per_kw' if provided will be overwritten by the sum of components.
        learning_rate: The learning rate (e.g., 0.2 for a 20% cost reduction for every doubling of production).
        initial_production_volume: The production volume corresponding to initial_costs (e.g., GW or units).
        supply_chain_model: An optional instance of SupplyChainModel to consider for cost adjustments.
        solar_tech_model: An optional instance of SolarTechModel for technology-specific parameter lookups.
        """
        self.technology_name = technology_name
        self.current_costs = initial_costs.copy() # Store a mutable copy
        self.learning_rate = learning_rate
        self.current_production_volume = initial_production_volume
        self.initial_production_volume = initial_production_volume
        self.initial_costs_snapshot = initial_costs.copy()
        self.supply_chain_model = supply_chain_model # Store the supply chain model instance
        self.solar_tech_model = solar_tech_model # Store the solar tech model instance

        self._recalculate_total_capex() # Calculate initial total CAPEX
        # Update snapshot with the calculated capex_per_kw if it wasn't there or differed
        self.initial_costs_snapshot['capex_per_kw'] = self.current_costs['capex_per_kw']

        logging.info(f"CostModel initialized for {self.technology_name}.")
        logging.info(f"  Initial Calculated CAPEX/kW: {self.current_costs.get('capex_per_kw', 'N/A')}")
        logging.info(f"  Learning Rate: {self.learning_rate*100}%")

    def _recalculate_total_capex(self):
        """Recalculates 'capex_per_kw' by summing its constituent components."""
        total_capex = 0
        for key in self.CAPEX_COMPONENT_KEYS:
            total_capex += self.current_costs.get(key, 0)
        self.current_costs['capex_per_kw'] = total_capex
        logging.debug(f"  Recalculated capex_per_kw for {self.technology_name}: {total_capex:.2f}")

    def update_cost_component(self, component_name: str, new_value: float):
        """Updates a specific cost component."""
        if component_name in self.current_costs:
            self.current_costs[component_name] = new_value
            logging.info(f"Updated {component_name} for {self.technology_name} to {new_value:.2f}")
            if component_name in self.CAPEX_COMPONENT_KEYS:
                self._recalculate_total_capex()
        else:
            logging.warning(f"Cost component '{component_name}' not found for {self.technology_name}. No update performed.")

    def apply_learning_curve(self, cumulative_production_volume: float) -> dict:
        """Applies the learning curve to CAPEX sub-components based on cumulative production.
        Updates self.current_costs (including recalculating total 'capex_per_kw') 
        and self.current_production_volume.
        Returns the updated current_costs dictionary.
        """
        if cumulative_production_volume <= self.current_production_volume:
            logging.warning(f"New cumulative production ({cumulative_production_volume}) is not greater than current ({self.current_production_volume}). No learning applied.")
            return self.current_costs

        exponent = math.log(1 - self.learning_rate) / math.log(2)

        # Apply learning only to the defined CAPEX sub-components
        for item_key in self.CAPEX_COMPONENT_KEYS:
            if item_key in self.initial_costs_snapshot and item_key in self.current_costs:
                initial_cost_for_item = self.initial_costs_snapshot[item_key]
                # Apply learning based on the ratio of new cumulative volume to *initial* volume
                new_cost = initial_cost_for_item * (cumulative_production_volume / self.initial_production_volume) ** exponent
                self.current_costs[item_key] = new_cost
                logging.info(f"  LC Applied: {item_key} for {self.technology_name} updated to {new_cost:.2f} (from {initial_cost_for_item:.2f} at initial volume {self.initial_production_volume})")
            elif item_key not in self.initial_costs_snapshot:
                logging.warning(f"  LC Warning: Initial cost for '{item_key}' not in snapshot. Cannot apply learning.")

        self._recalculate_total_capex() # Recalculate total CAPEX from updated components
        
        self.current_production_volume = cumulative_production_volume
        logging.info(f"Learning curve applied for {self.technology_name}. New cumulative volume: {cumulative_production_volume}")
        return self.current_costs

    def calculate_lcoe(
        self, 
        capacity_factor: float, 
        discount_rate: float, 
        economic_lifetime_years: int,
        annual_opex_per_kw: float = None, # If None, uses self.current_costs.get('opex_per_kw_year')
        fuel_cost_per_mwh: float = 0 # For technologies like solar, fuel cost is zero
    ) -> float:
        """Calculates Levelized Cost of Energy (LCOE) in USD/MWh."""
        
        capex = self.current_costs.get('capex_per_kw', 0)
        if annual_opex_per_kw is None:
            opex = self.current_costs.get('opex_per_kw_year', 0)
        else:
            opex = annual_opex_per_kw

        if capex == 0:
            logging.warning("Warning: CAPEX is zero. LCOE calculation might be meaningless.")
            return float('inf')

        # Capital Recovery Factor (CRF)
        if discount_rate > 0:
            crf = (discount_rate * (1 + discount_rate) ** economic_lifetime_years) / \
                  ((1 + discount_rate) ** economic_lifetime_years - 1)
        elif economic_lifetime_years > 0:
            crf = 1 / economic_lifetime_years
        else:
            logging.warning("Warning: Discount rate is zero and lifetime is zero. Cannot calculate CRF.")
            return float('inf')

        annualized_capex = capex * crf
        annual_generation_kwh_per_kw = 8760 * capacity_factor # kWh per kW per year
        annual_generation_mwh_per_kw = annual_generation_kwh_per_kw / 1000

        if annual_generation_mwh_per_kw == 0:
            logging.warning("Warning: Annual generation is zero. Cannot calculate LCOE.")
            return float('inf')

        lcoe = (annualized_capex + opex + (fuel_cost_per_mwh * annual_generation_mwh_per_kw)) / annual_generation_mwh_per_kw
        
        logging.info(f"LCOE for {self.technology_name}: ${lcoe:.2f}/MWh")
        logging.info(f"  Inputs: CAPEX=${capex:.2f}/kW, OPEX=${opex:.2f}/kW/yr, CF={capacity_factor*100:.1f}%, DR={discount_rate*100:.1f}%, Life={economic_lifetime_years}yrs")
        return lcoe

    def calculate_lcoe_for_evolving_solar_tech(
        self,
        solar_tech_model: 'SolarTechModel',
        technology_name: str,
        year: int,
        capacity_factor: float,
        discount_rate: float,
        economic_lifetime_years: int,
    ) -> Dict[str, Any]:
        """
        Calculates LCOE using evolving CAPEX and efficiency from SolarTechModel for a specific technology.
        This method now uses the provided 'technology_name' argument for fetching parameters.
        """
        tech_params = solar_tech_model.get_technology_details(technology_name, year)

        if tech_params.get('error'):
            error_msg = tech_params['error']
            logging.error(f"Error fetching technology details for {technology_name} in {year}: {error_msg}")
            return {
                'lcoe_usd_per_mwh': float('inf'), 
                'error': error_msg,
                'capex_usd_per_kw': None,
                'opex_per_kw_year': None, # OPEX might still be from self.initial_costs
                'efficiency': None
            }

        capex_per_kw = tech_params['capex_usd_per_kw']
        efficiency = tech_params['efficiency']
        is_commercially_available = tech_params['is_commercially_available']
        commercial_scale_year = tech_params['commercial_scale_year']

        if not is_commercially_available:
            logging.warning(f"{technology_name} (commercial in {commercial_scale_year}) is not commercially available in {year}. LCOE is speculative.")

        # Use OPEX from the CostModel instance's current_costs, as it's not part of SolarTechModel's dynamic parameters yet.
        # This assumes CostModel is appropriately configured for the technology type regarding OPEX.
        opex_per_kw_year = self.current_costs.get('opex_per_kw_year', 0)

        # Robust CRF Calculation
        crf = 0.0
        if economic_lifetime_years <= 0:
            if capex_per_kw > 0:
                error_msg = f"Lifetime is {economic_lifetime_years} years. LCOE is infinite for {technology_name} in {year} if CAPEX > 0."
                logging.error(f"Error: {error_msg}")
                return {
                    'lcoe_usd_per_mwh': float('inf'), 
                    'error': error_msg,
                    'capex_usd_per_kw': capex_per_kw,
                    'opex_per_kw_year': opex_per_kw_year,
                    'efficiency': efficiency
                }
            # If capex_per_kw is also 0, annualized_capex is 0. crf itself is not strictly needed.
        elif discount_rate == 0:
            crf = 1 / economic_lifetime_years
        else: # discount_rate is non-zero and economic_lifetime_years > 0
            try:
                # Standard CRF formula: DR * (1+DR)^L / ((1+DR)^L - 1)
                numerator = discount_rate * ((1 + discount_rate) ** economic_lifetime_years)
                denominator = ((1 + discount_rate) ** economic_lifetime_years) - 1
                if denominator == 0:
                    # This can happen if (1+discount_rate) is a root of unity for 'economic_lifetime_years'
                    # Or if discount_rate = -1 and economic_lifetime_years = 1 (0/0 case, limit is 1 for L=1, DR=-1)
                    # For simplicity, treat as ill-defined if denominator is zero and capex > 0
                    if capex_per_kw > 0:
                        error_msg = f"CRF denominator is zero for {technology_name} in {year}. DR={discount_rate}, Life={economic_lifetime_years}."
                        logging.error(f"Error: {error_msg}")
                        return {
                            'lcoe_usd_per_mwh': float('inf'), 
                            'error': error_msg,
                            'capex_usd_per_kw': capex_per_kw,
                            'opex_per_kw_year': opex_per_kw_year,
                            'efficiency': efficiency
                        }
                    # if capex_per_kw is 0, annualized_capex is 0.
                else:
                    crf = numerator / denominator
            except OverflowError:
                error_msg = f"OverflowError during CRF calculation for {technology_name} in {year}. DR={discount_rate}, Life={economic_lifetime_years}. Values might be too large."
                logging.error(f"Error: {error_msg}")
                return {
                    'lcoe_usd_per_mwh': float('inf'), 
                    'error': error_msg,
                    'capex_usd_per_kw': capex_per_kw,
                    'opex_per_kw_year': opex_per_kw_year,
                    'efficiency': efficiency
                }

        annualized_capex = capex_per_kw * crf
        annual_generation_kwh_per_kw = 8760 * capacity_factor # kWh per kW per year
        annual_generation_mwh_per_kw = annual_generation_kwh_per_kw / 1000

        if annual_generation_mwh_per_kw == 0:
            if annualized_capex + opex_per_kw_year > 0: # If there are costs but no generation
                error_msg = f"Annual generation is zero for {technology_name} in {year}. LCOE is infinite."
                logging.warning(f"Warning: {error_msg}")
                return {
                    'lcoe_usd_per_mwh': float('inf'), 
                    'error': error_msg,
                    'capex_usd_per_kw': capex_per_kw,
                    'opex_per_kw_year': opex_per_kw_year,
                    'efficiency': efficiency,
                    'annual_generation_mwh_per_kw': 0
                }
            else: # No costs and no generation, LCOE is effectively 0 or undefined, let's choose 0.
                lcoe_usd_per_mwh = 0.0
        else:
            # Assuming fuel_cost_per_mwh is 0 for solar technologies
            lcoe_usd_per_mwh = (annualized_capex + opex_per_kw_year) / annual_generation_mwh_per_kw
        
        result = {
            'technology_name': technology_name,
            'year': year,
            'lcoe_usd_per_mwh': round(lcoe_usd_per_mwh, 2),
            'capex_usd_per_kw': round(capex_per_kw, 2),
            'opex_per_kw_year': round(opex_per_kw_year, 2),
            'efficiency': round(efficiency, 4),
            'capacity_factor': capacity_factor,
            'discount_rate': discount_rate,
            'economic_lifetime_years': economic_lifetime_years,
            'annual_generation_mwh_per_kw': round(annual_generation_mwh_per_kw, 2),
            'crf': round(crf, 4),
            'annualized_capex_per_kw': round(annualized_capex, 2),
            'is_commercially_available': is_commercially_available,
            'error': None
        }
        logging.info(f"LCOE for {result['technology_name']} ({result['year']}): ${result['lcoe_usd_per_mwh']:.2f}/MWh (CAPEX: ${result['capex_usd_per_kw']:.2f}/kW, Eff: {result['efficiency']:.4f})")
        return result

    def update_opex_cost(self, new_opex_per_kw_year: float):
        """Updates the OPEX cost."""
        if 'opex_per_kw_year' in self.current_costs:
            self.current_costs['opex_per_kw_year'] = new_opex_per_kw_year
            logging.info(f"Updated OPEX for {self.technology_name} to {new_opex_per_kw_year:.2f} USD/kW/yr")
        else:
            logging.warning(f"Warning: OPEX not found for {self.technology_name}. No update performed.")

    def adjust_costs_based_on_supply_chain(
        self,
        material_item_name: str = 'polysilicon',
        module_item_name: str = 'solar_modules',
    ):
        """
        Adjusts 'module_usd_per_kw' based on supply chain risks from an associated SupplyChainModel.
        Considers material availability (e.g., polysilicon) and market concentration (e.g., solar modules).
        """
        if not self.supply_chain_model:
            logging.info(f"Info: No SupplyChainModel associated with CostModel for {self.technology_name}. No supply chain adjustments applied.")
            return

        if 'module_usd_per_kw' not in self.current_costs:
            logging.warning(f"Warning: 'module_usd_per_kw' not found in current costs for {self.technology_name}. Cannot apply supply chain adjustments.")
            return

        original_module_cost = self.current_costs['module_usd_per_kw']
        material_adjustment_pct = 0.0
        concentration_adjustment_pct = 0.0

        # 1. Material Availability Risk (e.g., for Polysilicon)
        material_data = self.supply_chain_model.supply_data.get(material_item_name)
        if material_data:
            global_capacity_key_tons = 'global_capacity_tons_per_year' # Assuming tons for materials like polysilicon
            global_capacity_key_gw = 'global_capacity_gw_per_year' # For items measured in GW
            
            # Determine the correct capacity key for the material
            if global_capacity_key_tons in material_data:
                material_global_capacity = material_data[global_capacity_key_tons]
            elif global_capacity_key_gw in material_data: # Should not happen for polysilicon but for generality
                material_global_capacity = material_data[global_capacity_key_gw]
            else:
                material_global_capacity = 0

            if material_global_capacity > 0:
                # Simplified assumption for required quantity
                required_quantity = material_global_capacity * self.DEFAULT_REQUIRED_MATERIAL_FRACTION_OF_GLOBAL
                availability = self.supply_chain_model.get_material_availability(material_item_name, required_annual_quantity=required_quantity)

                if not availability['available']:
                    shortfall_percentage = availability.get('shortfall', 0) / required_quantity if required_quantity > 0 else 1.0
                    if shortfall_percentage > 0.5:
                        material_adjustment_pct = self.MATERIAL_SHORTFALL_HIGH_IMPACT_PCT
                    elif shortfall_percentage > 0.2:
                        material_adjustment_pct = self.MATERIAL_SHORTFALL_MEDIUM_IMPACT_PCT
                    else:
                        material_adjustment_pct = self.MATERIAL_SHORTFALL_LOW_IMPACT_PCT
                elif availability.get('surplus', 0) / material_global_capacity < 0.10: # Surplus less than 10% of global capacity
                    material_adjustment_pct = self.MATERIAL_TIGHT_SURPLUS_IMPACT_PCT
            else:
                logging.warning(f"Warning: Global capacity for material '{material_item_name}' is zero or not found. Cannot assess material availability risk.")
        else:
            logging.warning(f"Warning: Material '{material_item_name}' not found in SupplyChainModel. Cannot assess material availability risk.")

        # 2. Market Concentration Risk (e.g., for Solar Modules)
        # Assuming module concentration is based on GW capacity
        concentration_risk_modules = self.supply_chain_model.get_concentration_risk(module_item_name, capacity_key='regional_capacity_gw_per_year')
        if concentration_risk_modules and 'assessment' in concentration_risk_modules:
            assessment = concentration_risk_modules['assessment']
            if assessment == 'Highly concentrated':
                concentration_adjustment_pct = self.CONCENTRATION_HIGH_IMPACT_PCT
            elif assessment == 'Moderately concentrated':
                concentration_adjustment_pct = self.CONCENTRATION_MODERATE_IMPACT_PCT
        else:
            logging.warning(f"Warning: Could not assess concentration risk for '{module_item_name}'. Details: {concentration_risk_modules.get('error', 'No assessment provided')}")

        total_adjustment_factor = material_adjustment_pct + concentration_adjustment_pct

        if total_adjustment_factor > 0:
            new_module_cost = original_module_cost * (1 + total_adjustment_factor)
            self.update_cost_component('module_usd_per_kw', new_module_cost)
            logging.info(f"Applied supply chain adjustment to '{self.technology_name}'. Material risk: {material_adjustment_pct*100:.1f}%, Concentration risk: {concentration_adjustment_pct*100:.1f}%. Module cost changed from {original_module_cost:.2f} to {new_module_cost:.2f}.")
        else:
            logging.info(f"No supply chain risk adjustments applied to '{self.technology_name}'. Module cost remains {original_module_cost:.2f}.")

    def update_for_year(self, year: int, cumulative_production_volume_for_tech: float = None, solar_tech_model: 'SolarTechModel' = None, **kwargs):
        """
        Updates the cost model for a given year.
        This can include applying learning curves, adjusting for supply chain issues,
        and potentially other year-specific updates.

        Args:
            year (int): The simulation year for which to update the costs.
            cumulative_production_volume_for_tech (float, optional): 
                The new total cumulative production volume for this specific technology.
                Used to apply learning curves. If None, learning curve is not applied based on new volume.
            solar_tech_model (SolarTechModel, optional): 
                An instance of SolarTechModel. If provided, could be used for more
                advanced cost adjustments based on technological evolution (e.g., efficiency changes
                affecting BoS or installation, though this is not implemented in detail yet).
            **kwargs: Additional keyword arguments for future extensions.
        """
        logging.info(f"Updating CostModel for {self.technology_name} for year {year}.")

        # 1. Apply learning curve if new cumulative production volume is provided
        if cumulative_production_volume_for_tech is not None and cumulative_production_volume_for_tech > self.current_production_volume:
            logging.debug(f"  Applying learning curve for {self.technology_name} due to new cumulative production: {cumulative_production_volume_for_tech}")
            self.apply_learning_curve(cumulative_production_volume_for_tech)
        else:
            logging.debug(f"  Learning curve not applied for {self.technology_name}: cumulative_production_volume_for_tech ({cumulative_production_volume_for_tech}) not greater than current ({self.current_production_volume}).")

        # 2. Adjust costs based on supply chain model (if available)
        if self.supply_chain_model:
            logging.debug(f"  Adjusting costs for {self.technology_name} based on supply chain model for year {year}.")
            self.adjust_costs_based_on_supply_chain()
        # 3. Placeholder for other yearly updates based on solar_tech_model
        if solar_tech_model:
            # tech_params = solar_tech_model.get_technology_parameters(self.technology_name, year)
            # if tech_params:
            #     logging.debug(f"  Considering SolarTechModel parameters for {self.technology_name} for year {year}: {tech_params}")
            pass
            
        logging.info(f"CostModel for {self.technology_name} updated for year {year}. Current CAPEX/kW: {self.current_costs.get('capex_per_kw', 'N/A'):.2f}")
        return self.current_costs

if __name__ == "__main__":
    # Setup basic logging for the example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Import SolarTechModel and SolarTechnology for the example
    from ..technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology
    # SupplyChainModel should be imported at the top level of the file if needed by the class itself
    # from ..supply_chain_dynamics.supply_chain_model import SupplyChainModel # This might be redundant if imported globally

    # --- Example Usage of CostModel --- 
    # 1. Initialize CostModel for a technology (e.g., standard silicon PV)
    initial_solar_costs = {
        'module_usd_per_kw': 280, 
        'bos_usd_per_kw': 150,
        'inverter_usd_per_kw': 100,
        'installation_usd_per_kw': 200,
        'opex_per_kw_year': 20
    }
    solar_cost_model = CostModel(
        technology_name='StandardSiliconPV',
        initial_costs=initial_solar_costs,
        learning_rate=0.18, # 18% learning rate
        initial_production_volume=100 # GW
    )

    # Demonstrate cost component update
    solar_cost_model.update_cost_component('module_usd_per_kw', 270)

    # Apply learning curve
    solar_cost_model.apply_learning_curve(cumulative_production_volume=200) # Double the production
    logging.info(f"Costs after learning (200 GW): {solar_cost_model.current_costs}")
    solar_cost_model.apply_learning_curve(cumulative_production_volume=400) # Double again
    logging.info(f"Costs after learning (400 GW): {solar_cost_model.current_costs}")

    # LCOE Calculation
    lcoe_solar = solar_cost_model.calculate_lcoe(
        capacity_factor=0.18, # Typical for some European locations
        discount_rate=0.05,   # 5% WACC
        economic_lifetime_years=25
    )
    logging.info(f"LCOE for StandardSiliconPV (direct from var): {lcoe_solar:.2f} USD/MWh")

    # --- Supply Chain Integration Example ---
    logging.info("\n--- Supply Chain Integration Example ---")
    # 1. Initialize SupplyChainModel (it uses its own default/updated initial_data)
    # Note: The supply_chain_model.py now has updated China capacities from previous steps.
    scm = SupplyChainModel()

    # 2. Create a new CostModel instance for a technology, passing the scm
    solar_panel_costs_for_scm_test = {
        'module_usd_per_kw': 220, # Starting module cost before supply chain impact
        'bos_usd_per_kw': 140,
        'inverter_usd_per_kw': 90,
        'installation_usd_per_kw': 180,
        'opex_per_kw_year': 22
    }
    cost_model_with_scm = CostModel(
        technology_name='UtilitySolarSCM',
        initial_costs=solar_panel_costs_for_scm_test,
        learning_rate=0.15,
        initial_production_volume=50,
        supply_chain_model=scm # Pass the initialized SupplyChainModel
    )
    logging.info(f"Initial module_usd_per_kw for UtilitySolarSCM: {cost_model_with_scm.current_costs['module_usd_per_kw']:.2f}")

    # 3. Apply supply chain adjustments
    cost_model_with_scm.adjust_costs_based_on_supply_chain(
        material_item_name='polysilicon', 
        module_item_name='solar_modules'
    )
    logging.info(f"Adjusted module_usd_per_kw for UtilitySolarSCM after supply chain assessment: {cost_model_with_scm.current_costs['module_usd_per_kw']:.2f}")

    # Recalculate LCOE to see impact (optional demonstration)
    lcoe_scm_adjusted = cost_model_with_scm.calculate_lcoe(
        capacity_factor=0.22, 
        discount_rate=0.05, 
        economic_lifetime_years=25
    )
    logging.info(f"LCOE for UtilitySolarSCM (SCM adjusted, direct from var): {lcoe_scm_adjusted:.2f} USD/MWh")

    # --- CostModel with SolarTechModel Integration Example (Advanced Silicon PV) ---
    logging.info("\n--- CostModel with SolarTechModel Integration Example (Advanced Silicon PV) ---")
    # 1. Setup SolarTechModel
    stm = SolarTechModel()
    # Add a technology that matches a CostModel instance name
    adv_si_pv_tech = SolarTechnology(
        name='AdvancedSiliconPV_Evolving',
        base_efficiency=0.22, # 22% in start_year
        projected_efficiency_2035=0.26, # 26% by 2035
        start_year=2023,
        commercial_scale_year=2020,
        degradation_rate_annual=0.005,
        base_capex_usd_per_kw=900, # USD/kW in start_year
        annual_capex_reduction_rate=0.03 # 3% annual reduction
    )
    stm.add_technology(adv_si_pv_tech)

    # 2. Setup CostModel for this technology (mainly for OPEX, learning rate not directly used by new LCOE method)
    # The initial_costs' CAPEX components in CostModel will be IGNORED by the new LCOE method,
    # as it fetches CAPEX from SolarTechModel. However, OPEX is still taken from CostModel.
    evolving_solar_opex_costs = {
        'opex_per_kw_year': 18, # Example OPEX for this evolving tech
        # CAPEX components here are not strictly needed for the new LCOE method, but CostModel expects them for initialization.
        'module_usd_per_kw': 0, 
        'bos_usd_per_kw': 0, 
        'inverter_usd_per_kw': 0,
        'installation_usd_per_kw': 0
    }
    evolving_solar_cost_model = CostModel(technology_name='AdvancedSiliconPV_Evolving',
                                        initial_costs=evolving_solar_opex_costs,
                                        learning_rate=0, # Not used by calculate_lcoe_for_evolving_solar_tech
                                        initial_production_volume=1 # Not used by calculate_lcoe_for_evolving_solar_tech
                                        )

    # 3. Calculate LCOE for different years using the new method
    logging.info("\nCalculating LCOE for AdvancedSiliconPV_Evolving using SolarTechModel:")
    years_to_test = [2023, 2025, 2030, 2035]
    for year in years_to_test:
        logging.info(f"\n--- Year {year} ---")
        lcoe_results = evolving_solar_cost_model.calculate_lcoe_for_evolving_solar_tech(
            solar_tech_model=stm,
            technology_name='AdvancedSiliconPV_Evolving',
            year=year,
            capacity_factor=0.20,
            discount_rate=0.05,
            economic_lifetime_years=25
        )
        if lcoe_results and lcoe_results.get('error') is None:
            logging.info(f"  LCOE: {lcoe_results['lcoe_usd_per_mwh']:.2f} USD/MWh")
            logging.info(f"  CAPEX: {lcoe_results['capex_usd_per_kw']:.2f} USD/kW")
            logging.info(f"  Efficiency: {lcoe_results['efficiency']:.4f}")
            logging.info(f"  OPEX: {lcoe_results['opex_per_kw_year']:.2f} USD/kW/yr")
        else:
            logging.info(f"  Could not calculate LCOE: {lcoe_results.get('error') if lcoe_results else 'Unknown error'}")

    # Example with a technology not yet commercially available
    future_tech = SolarTechnology(
        name='FutureX',
        base_efficiency=0.30, # 30% in start_year
        projected_efficiency_2035=0.40, # 40% by 2035
        start_year=2028,
        commercial_scale_year=2030, 
        degradation_rate_annual=0.005,
        base_capex_usd_per_kw=1200, # USD/kW in start_year
        annual_capex_reduction_rate=0.05 # 5% annual reduction
    )
    stm.add_technology(future_tech)

    future_tech_opex_costs = {'opex_per_kw_year': 25}
    future_tech_cost_model = CostModel(technology_name='FutureX',
                                       initial_costs=future_tech_opex_costs,
                                       learning_rate=0)

    logging.info("\nCalculating LCOE for FutureX (not yet commercial in 2028):")
    lcoe_future_tech_2028 = future_tech_cost_model.calculate_lcoe_for_evolving_solar_tech(
        solar_tech_model=stm,
        technology_name='FutureX',
        year=2028, 
        capacity_factor=0.25, 
        discount_rate=0.06, 
        economic_lifetime_years=20
    )
    logging.info(lcoe_future_tech_2028)

    logging.info("\nCalculating LCOE for FutureX (commercial in 2030):")
    lcoe_future_tech_2030 = future_tech_cost_model.calculate_lcoe_for_evolving_solar_tech(
        solar_tech_model=stm,
        technology_name='FutureX',
        year=2030, 
        capacity_factor=0.25, 
        discount_rate=0.06, 
        economic_lifetime_years=20
    )
    logging.info(lcoe_future_tech_2030)

    # Example of tech not in SolarTechModel
    logging.info("\nCalculating LCOE for a technology not in SolarTechModel:")
    non_existent_cost_model = CostModel(technology_name='PhantomTech', initial_costs={'opex_per_kw_year':10}, learning_rate=0)
    lcoe_phantom = non_existent_cost_model.calculate_lcoe_for_evolving_solar_tech(
        solar_tech_model=stm, 
        technology_name='PhantomTech', 
        year=2030, 
        capacity_factor=0.2, 
        discount_rate=0.05, 
        economic_lifetime_years=25
    )
    logging.info(lcoe_phantom)
