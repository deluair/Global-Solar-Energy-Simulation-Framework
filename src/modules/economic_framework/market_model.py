"""
Models energy market structures, revenue streams (including ancillary services and ESG premiums),
and their evolution across different regions.
"""

import logging

logger = logging.getLogger(__name__)

class MarketSimulator:
    """Simulates energy market dynamics, including energy prices and ancillary service revenues.

    The simulator uses market design configurations for different regions to calculate
    potential revenue streams for energy projects. These designs can specify base
    energy prices, time-of-use (TOU) multipliers, and details for various
    ancillary services, including their prices and availability.
    """
    def __init__(self, market_designs: dict):
        """Initializes MarketSimulator with market configurations for various regions.

        Args:
            market_designs (dict): A dictionary where keys are region names (str) and
                values are dictionaries defining the market structure for that region.
                Each region's design can include:
                - 'type' (str): Type of market (e.g., 'energy_only', 'capacity_market').
                - 'base_energy_price_usd_per_mwh' (float): Base price for energy.
                - 'tou_factors' (dict): Time-of-use multipliers, where keys are time
                  periods (e.g., 'on_peak') and values are multipliers (float).
                - 'ancillary_services' (dict): Configuration for ancillary services.
                  Keys are service types (e.g., 'frequency_response'), and values are
                  dictionaries with:
                  - 'price_usd_per_mw_year' (float): Annual price per MW for the service.
                  - 'availability_factor' (float, optional): A factor (0.0 to 1.0)
                    representing the proportion of the service's nominal price that
                    can be realized. Defaults to 1.0 if not specified.
                    This factor accounts for market limitations, participation caps,
                    or intermittent availability of the service opportunity.
                  - Other service-specific notes or parameters.

        Example:
            {
                'RegionA': {
                    'type': 'energy_only',
                    'base_energy_price_usd_per_mwh': 50,
                    'tou_factors': {'off_peak': 0.8, 'mid_peak': 1.0, 'on_peak': 1.5},
                    'ancillary_services': {
                        'frequency_response': {
                            'price_usd_per_mw_year': 5000,
                            'availability_factor': 0.9 
                        },
                        'voltage_support': {'price_usd_per_mw_year': 3000}
                    }
                }
            }
        """
        self.market_designs = market_designs
        logger.info(f"MarketSimulator initialized with {len(self.market_designs)} market designs.")

    def simulate_dispatch_for_year(self, 
                                   year: int, 
                                   regions: list, # List[str]
                                   new_investments: dict, # Dict[str, Dict[str, float]]
                                   # Type hints for models can be more specific
                                   solar_tech_model: any, # SolarTechModel instance
                                   grid_model: any, # GridModel instance
                                   cost_model: any # CostModel instance (though not used for var OPEX yet)
                                  ) -> dict: # Dict[str, Any]
        """Simulates market dispatch for the given year and investments.

        This method implements simplified dispatch logic.

        Args:
            year (int): The current simulation year.
            regions (list): List of region names.
            new_investments (dict): Investments made in the current year, structured as:
                                {'RegionA': {'Tech1': Capacity_MW, 'Tech2': Capacity_MW}}.
            solar_tech_model: Instance of SolarTechModel.
            grid_model: Instance of GridModel.
            cost_model: Instance of CostModel.

        Returns:
            dict: A dictionary containing market outcomes for the year. 
                  Example: {'RegionA': {'total_generation_gwh': 1000, 'avg_price_usd_mwh': 50}}
                  This structure needs to be aligned with what SimulationEngine expects to collect.
        """
        # In a real implementation, you'd use: from typing import Dict, List, Any
        # For now, keeping it simple for placeholder.
        logger.info(f"MarketSimulator.simulate_dispatch_for_year called for year {year}, regions: {regions}, investments: {new_investments}.")
        
        market_outcomes = {}
        HOURS_PER_YEAR = 8760
        DEFAULT_PV_CAPACITY_FACTOR = 0.20  # General assumption for PV-like technologies
        DEFAULT_BATTERY_EFFECTIVE_CF = 0.10 # General assumption for battery annual energy contribution

        for region_name in regions:
            logger.info(f"Simulating dispatch for region: {region_name} in year {year}")
            market_outcomes[region_name] = {
                'total_generation_mwh': {},
                'annual_demand_mwh': 0,
                'total_dispatched_generation_mwh': 0,
                'unmet_demand_mwh': 0
            }

            # 1. Get Regional Demand
            if region_name not in grid_model.regional_data or 'current_load_mw' not in grid_model.regional_data[region_name]:
                logger.warning(f"  Region {region_name} or its 'current_load_mw' not found in grid_model. Skipping dispatch for this region.")
                continue
        
            regional_peak_load_mw = grid_model.regional_data[region_name]['current_load_mw']
            # Simplistic annual demand calculation (flat load profile)
            annual_demand_mwh = regional_peak_load_mw * HOURS_PER_YEAR 
            market_outcomes[region_name]['annual_demand_mwh'] = annual_demand_mwh
            logger.info(f"  Annual demand for {region_name}: {annual_demand_mwh:.2f} MWh (based on peak load: {regional_peak_load_mw:.2f} MW)")

            # 2. Get Installed Capacities & Prepare Dispatchable Tech List
            installed_capacities = grid_model.get_current_capacity_by_tech(region_name)
            if not installed_capacities:
                logger.info(f"  No installed capacities found in {region_name} for year {year}. No dispatch possible.")
                market_outcomes[region_name]['unmet_demand_mwh'] = annual_demand_mwh
                continue

            dispatchable_techs = []
            for tech_name, capacity_mw in installed_capacities.items():
                if capacity_mw <= 0:
                    continue

                tech_details = solar_tech_model.get_technology_details(tech_name, year)
                if 'error' in tech_details:
                    logger.warning(f"    Error retrieving details for {tech_name} in {region_name}: {tech_details['error']}. Skipping for dispatch.")
                    continue
            
                if not tech_details.get('is_commercially_available', True): # Assume available if key missing (for older configs)
                    logger.info(f"    Technology {tech_name} in {region_name} is not commercially available in {year}. Skipping for dispatch.")
                    continue

                potential_annual_generation_mwh = 0
                # Marginal cost assumed to be 0 for renewables/storage in this simplified model
                marginal_cost = 0 

                if "BATTERY" in tech_name.upper():
                    # Using a default effective capacity factor for battery's annual energy contribution
                    potential_annual_generation_mwh = capacity_mw * DEFAULT_BATTERY_EFFECTIVE_CF * HOURS_PER_YEAR
                    logger.debug(f"    {tech_name} (Battery) in {region_name}: Capacity={capacity_mw:.2f} MW, Potential Annual Gen (eff_CF={DEFAULT_BATTERY_EFFECTIVE_CF})={potential_annual_generation_mwh:.2f} MWh")
                else: # Assume PV-like
                    # Using SolarTechnology efficiency to modulate a base capacity factor is complex without irradiance data.
                    # For now, using a default capacity factor for all PV.
                    # Future: capacity_factor = tech_details.get('capacity_factor', DEFAULT_PV_CAPACITY_FACTOR) 
                    # - efficiency from tech_details could be used if solar irradiance data for the region was available.
                    potential_annual_generation_mwh = capacity_mw * DEFAULT_PV_CAPACITY_FACTOR * HOURS_PER_YEAR
                    logger.debug(f"    {tech_name} (PV-like) in {region_name}: Capacity={capacity_mw:.2f} MW, Potential Annual Gen (CF={DEFAULT_PV_CAPACITY_FACTOR})={potential_annual_generation_mwh:.2f} MWh")

                if potential_annual_generation_mwh > 0:
                    dispatchable_techs.append({
                        'name': tech_name,
                        'potential_mwh': potential_annual_generation_mwh,
                        'marginal_cost': marginal_cost # Currently 0 for all
                    })
        
            # 3. Perform Simplified Merit-Order Dispatch (Order doesn't matter much with MC=0)
            # Sorting by marginal cost (though all are 0 for now)
            dispatchable_techs.sort(key=lambda x: x['marginal_cost'])
        
            dispatched_generation_for_region_mwh = 0
            for tech in dispatchable_techs:
                if dispatched_generation_for_region_mwh >= annual_demand_mwh:
                    break # Demand met
            
                generation_to_dispatch = min(tech['potential_mwh'], annual_demand_mwh - dispatched_generation_for_region_mwh)
            
                if generation_to_dispatch > 0:
                    market_outcomes[region_name]['total_generation_mwh'][tech['name']] = generation_to_dispatch
                    dispatched_generation_for_region_mwh += generation_to_dispatch
                    logger.info(f"    Dispatching {generation_to_dispatch:.2f} MWh from {tech['name']} in {region_name}.")

            market_outcomes[region_name]['total_dispatched_generation_mwh'] = dispatched_generation_for_region_mwh
            market_outcomes[region_name]['unmet_demand_mwh'] = max(0, annual_demand_mwh - dispatched_generation_for_region_mwh)
            logger.info(f"  Dispatch summary for {region_name}: Total Dispatched={dispatched_generation_for_region_mwh:.2f} MWh, Unmet Demand={market_outcomes[region_name]['unmet_demand_mwh']:.2f} MWh")

        logger.info(f"MarketSimulator.simulate_dispatch_for_year completed for year {year}. Market Outcomes: {market_outcomes}")
        return market_outcomes

    def get_energy_price(self, region: str, time_of_day: str, default_base_price: float = 50) -> float:
        """Calculates the energy price for a given region and time of day.

        The price is determined by the region's base energy price and any applicable
        time-of-use (TOU) multipliers defined in its market design. If TOU factors
        are not specified for the region, or if the specific time_of_day is not
        listed, a multiplier of 1.0 is used. If the region itself is not found
        in the market designs, the `default_base_price` is used with a TOU
        multiplier of 1.0.

        Args:
            region (str): The market region (e.g., 'California_ISO').
            time_of_day (str): The specific time of day for price calculation
                (e.g., 'off_peak', 'mid_peak', 'on_peak').
            default_base_price (float, optional): The base energy price to use if the
                region is not found or does not specify a base price. Defaults to 50.

        Returns:
            float: The calculated energy price in USD per MWh.
        """
        region_design = self.market_designs.get(region, {})
        base_price = region_design.get('base_energy_price_usd_per_mwh', default_base_price)
        
        tou_factors = region_design.get('tou_factors', {})
        # Default multiplier is 1 if time_of_day key is missing or tou_factors itself is missing
        tou_multiplier = tou_factors.get(time_of_day, 1.0) 
        
        price = base_price * tou_multiplier
        logger.info(f"Energy price in {region} at {time_of_day}: ${price:.2f}/MWh (Base: ${base_price:.2f}, TOU x{tou_multiplier:.2f})")
        return price

    def estimate_ancillary_revenue(self, capacity_mw: float, service_type: str, region: str) -> float:
        """Estimates potential annual revenue from a specific ancillary service.

        The revenue is calculated based on the project's capacity, the service's
        price per MW per year, and an availability factor. The availability factor
        (0.0 to 1.0) represents the realizable portion of the nominal revenue for
        that service, accounting for market rules or operational constraints.
        If the service type or region is not defined, or if the service has no price,
        the estimated revenue is zero.

        Args:
            capacity_mw (float): The capacity of the asset in MW eligible for the service.
            service_type (str): The type of ancillary service (e.g., 'frequency_response',
                'voltage_support').
            region (str): The market region where the service is provided.

        Returns:
            float: Estimated total annual revenue from the specified ancillary service in USD.
        """
        region_design = self.market_designs.get(region, {})
        ancillary_services_config = region_design.get('ancillary_services', {})
        service_config = ancillary_services_config.get(service_type, {})
        
        revenue_per_mw_year = service_config.get('price_usd_per_mw_year', 0)
        availability_factor = service_config.get('availability_factor', 1.0) # Default to 1.0 if not specified
        
        total_revenue = capacity_mw * revenue_per_mw_year * availability_factor
        if revenue_per_mw_year > 0: # Only print if there's a base rate, even if availability makes it zero
            logger.info(f"Estimated ancillary service ({service_type}) revenue in {region} for {capacity_mw}MW: ${total_revenue:.2f}/year (Rate: ${revenue_per_mw_year}/MW/year, Availability: {availability_factor*100:.0f}%)")
        else:
            logger.info(f"Ancillary service ({service_type}) not defined or no revenue in {region}.")
        return total_revenue

if __name__ == '__main__':
    # Example Usage
    example_designs = {
        'California_ISO': {
            'type': 'capacity_market',
            'base_energy_price_usd_per_mwh': 60,
            'tou_factors': {'off_peak': 0.7, 'mid_peak': 1.0, 'on_peak': 1.8},
            'ancillary_services': {
                'frequency_response': {'price_usd_per_mw_year': 6000, 'notes': 'Primary frequency control', 'availability_factor': 0.95},
                'voltage_support': {'price_usd_per_mw_year': 2500, 'availability_factor': 0.9}
            }
        },
        'Germany': {
            'type': 'energy_only',
            'base_energy_price_usd_per_mwh': 45,
            'tou_factors': {'off_peak': 0.9, 'mid_peak': 1.0, 'on_peak': 1.3},
            'ancillary_services': {
                'frequency_response': {'price_usd_per_mw_year': 5000, 'availability_factor': 1.0}
            }
        },
        'Texas_ERCOT': {
            'type': 'energy_only_plus',
            'base_energy_price_usd_per_mwh': 35,
            # No TOU factors defined, should default to 1x
            'ancillary_services': {
                'spinning_reserve': {'price_usd_per_mw_year': 7000, 'availability_factor': 0.85}
            }
        }
    }
    simulator = MarketSimulator(market_designs=example_designs)
    
    logger.info("--- Energy Price Calculations ---")
    simulator.get_energy_price(region='California_ISO', time_of_day='on_peak')
    simulator.get_energy_price(region='California_ISO', time_of_day='off_peak')
    simulator.get_energy_price(region='Germany', time_of_day='mid_peak')
    simulator.get_energy_price(region='Texas_ERCOT', time_of_day='on_peak') # Should use base_price for Texas with default TOU
    simulator.get_energy_price(region='Unknown_Region', time_of_day='on_peak', default_base_price=40) # Test default base price

    logger.info("--- Ancillary Revenue Estimations ---")
    simulator.estimate_ancillary_revenue(capacity_mw=100, service_type='frequency_response', region='Germany')
    simulator.estimate_ancillary_revenue(capacity_mw=50, service_type='voltage_support', region='California_ISO')
    simulator.estimate_ancillary_revenue(capacity_mw=100, service_type='spinning_reserve', region='Texas_ERCOT')
    simulator.estimate_ancillary_revenue(capacity_mw=100, service_type='non_existent_service', region='Germany')
    simulator.estimate_ancillary_revenue(capacity_mw=100, service_type='frequency_response', region='Unknown_Region')
