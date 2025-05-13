import logging
from typing import Dict, Any, List

class GridModel:
    """
    Models grid capacity, constraints, and integration costs for multiple regions.
    """
    def __init__(self, initial_regional_data: Dict[str, Dict[str, Any]]):
        """
        Initializes the GridModel with data for multiple regions.

        Args:
            initial_regional_data (Dict[str, Dict[str, Any]]): 
                A dictionary where keys are region names (e.g., 'USA', 'China') 
                and values are dictionaries containing grid parameters for that region.
                Expected keys in the inner dictionary include:
                - 'existing_capacity_mw' (float): Total existing generation capacity.
                - 'current_load_mw' (float): Current peak or average electricity load.
                Optional keys (will use defaults if not provided):
                - 'max_solar_penetration_pct' (float, default 0.50)
                - 'base_interconnection_cost_usd_per_mw' (float, default 100000)
                - 'transmission_constraint_factor' (float, default 1.0)
                - 'avg_transmission_cost_usd_per_mw_km' (float, default 2000.0)
                - 'avg_terrain_factor' (float, default 1.0)
                - 'current_solar_mw' (float, default 0)
        """
        self.regional_data: Dict[str, Dict[str, Any]] = {}
        self.default_grid_params = {
            'max_solar_penetration_pct': 0.50,
            'base_interconnection_cost_usd_per_mw': 100000,
            'transmission_constraint_factor': 1.0,
            'avg_transmission_cost_usd_per_mw_km': 2000.0,
            'avg_terrain_factor': 1.0,
            'current_solar_mw': 0.0,
            'capacities_mw_by_tech': {} # New: Initialize for storing capacity by tech
        }

        for region_name, data in initial_regional_data.items():
            if 'existing_capacity_mw' not in data or 'current_load_mw' not in data:
                logging.error(f"GridModel: Missing 'existing_capacity_mw' or 'current_load_mw' for region '{region_name}'. Skipping region.")
                continue
            
            region_params = self.default_grid_params.copy()
            region_params.update(data)
            
            # Ensure capacities_mw_by_tech is initialized for each region if not already present
            if 'capacities_mw_by_tech' not in region_params:
                region_params['capacities_mw_by_tech'] = {}
                
            self.regional_data[region_name] = region_params
            
            logging.info(f"GridModel: Loaded configuration for region '{region_name}'.")
            logging.debug(f"  Region '{region_name}' data: {self.regional_data[region_name]}")

        if not self.regional_data:
            logging.warning("GridModel initialized, but no valid regional data was loaded.")
        else:
            logging.info(f"GridModel initialized for regions: {list(self.regional_data.keys())}")

    def update_for_year(self, year: int, regions: List[str], **kwargs):
        """Updates grid parameters for the specified regions for a given year."""
        logging.info(f"GridModel updating for year {year} across regions: {regions}")
        for region_name in regions:
            if region_name not in self.regional_data:
                logging.warning(f"GridModel: Region '{region_name}' not found during update for year {year}.")
                continue
            # Placeholder for any year-specific updates to grid parameters for this region
            # e.g., self.regional_data[region_name]['current_load_mw'] *= 1.01 # Example: 1% load growth
            logging.debug(f"  GridModel: Updated region '{region_name}' for year {year}.")
        logging.info(f"GridModel yearly update for {year} complete.")

    def get_max_solar_penetration_mw(self, region_name: str) -> float:
        """Calculates the maximum allowable solar capacity in MW for a region based on penetration limits."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for get_max_solar_penetration_mw.")
            return 0.0
        
        region_info = self.regional_data[region_name]
        # Max solar penetration is a % of existing total capacity (simplification)
        max_solar_mw = region_info['existing_capacity_mw'] * region_info['max_solar_penetration_pct']
        return max_solar_mw

    def get_current_solar_mw(self, region_name: str) -> float:
        """Returns the current installed solar capacity in MW for a specific region."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for get_current_solar_mw.")
            return 0.0
        return self.regional_data[region_name].get('current_solar_mw', 0.0)

    def add_solar_capacity(self, region_name: str, new_capacity_mw: float):
        """Adds newly installed solar capacity to a region's total."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for add_solar_capacity.")
            return
        
        self.regional_data[region_name]['current_solar_mw'] = self.regional_data[region_name].get('current_solar_mw', 0.0) + new_capacity_mw
        logging.info(f"GridModel: Added {new_capacity_mw} MW of solar to {region_name}. New total: {self.regional_data[region_name]['current_solar_mw']} MW.")

    def add_new_capacity(self, year: int, new_capacity_details: Dict[str, Dict[str, float]]):
        """
        Adds new generation capacities from investments to the grid model for a given year.
        Updates both the technology-specific capacities and the total solar capacity.

        Args:
            year (int): The simulation year for which these capacities are being added.
            new_capacity_details (Dict[str, Dict[str, float]]):
                A dictionary where keys are region names, and values are dictionaries
                mapping technology names to the new capacity in MW.
                Example: {'USA': {'AdvancedMonocrystallineSilicon': 50.0, 'LFP_Battery': 20.0}}
        """
        logging.info(f"GridModel: Updating new capacities for year {year} from investments.")
        for region_name, tech_investments in new_capacity_details.items():
            if region_name not in self.regional_data:
                logging.warning(f"GridModel: Region '{region_name}' not found. Cannot add new capacities: {tech_investments}")
                continue

            if 'capacities_mw_by_tech' not in self.regional_data[region_name]:
                self.regional_data[region_name]['capacities_mw_by_tech'] = {}

            for tech_name, capacity_mw in tech_investments.items():
                if capacity_mw <= 0:
                    continue # Skip non-positive investments

                # Update technology-specific capacity
                current_tech_capacity = self.regional_data[region_name]['capacities_mw_by_tech'].get(tech_name, 0.0)
                self.regional_data[region_name]['capacities_mw_by_tech'][tech_name] = current_tech_capacity + capacity_mw
                logging.info(f"  GridModel: Added {capacity_mw:.2f} MW of {tech_name} to {region_name}. New total for tech: {self.regional_data[region_name]['capacities_mw_by_tech'][tech_name]:.2f} MW.")

                # Heuristic to identify solar PV technologies and update 'current_solar_mw'
                # This helps maintain compatibility with existing solar-specific logic (e.g., penetration checks)
                is_solar_pv = False
                if "PV" in tech_name.upper() or \
                   "SOLAR" in tech_name.upper() or \
                   "SILICON" in tech_name.upper() or \
                   "TOPCON" in tech_name.upper() or \
                   "PEROVSKITE" in tech_name.upper():
                    if "BATTERY" not in tech_name.upper(): # Exclude solar+storage if 'Battery' is in name
                        is_solar_pv = True
                
                if is_solar_pv:
                    self.regional_data[region_name]['current_solar_mw'] = self.regional_data[region_name].get('current_solar_mw', 0.0) + capacity_mw
                    logging.info(f"    (Solar PV identified) GridModel: Updated total solar capacity in {region_name} by {capacity_mw:.2f} MW. New total solar: {self.regional_data[region_name]['current_solar_mw']:.2f} MW.")
        logging.info(f"GridModel: Finished updating new capacities for year {year}.")

    def get_current_capacity_by_tech(self, region_name: str) -> Dict[str, float]:
        """Returns the current installed capacity by technology in MW for a specific region."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for get_current_capacity_by_tech.")
            return {}
        return self.regional_data[region_name].get('capacities_mw_by_tech', {})

    def calculate_interconnection_costs(self, region_name: str, new_capacity_mw: float, distance_km: float = 10.0) -> float:
        """Calculates interconnection costs for new capacity in a region."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for calculate_interconnection_costs.")
            return float('inf') # Return a high cost if region not found

        region_info = self.regional_data[region_name]
        base_cost = region_info['base_interconnection_cost_usd_per_mw'] * new_capacity_mw
        transmission_cost = region_info['avg_transmission_cost_usd_per_mw_km'] * new_capacity_mw * distance_km * region_info['avg_terrain_factor']
        total_cost = (base_cost + transmission_cost) * region_info['transmission_constraint_factor']
        return total_cost

    def check_grid_constraints(self, region_name: str, additional_capacity_mw: float) -> bool:
        """Checks if adding new capacity violates grid constraints (e.g., max solar penetration)."""
        if region_name not in self.regional_data:
            logging.warning(f"GridModel: Region '{region_name}' not found for check_grid_constraints.")
            return False # Cannot add if region doesn't exist
        
        current_solar = self.get_current_solar_mw(region_name)
        max_solar = self.get_max_solar_penetration_mw(region_name)
        
        if current_solar + additional_capacity_mw > max_solar:
            logging.info(f"GridModel Constraint: Adding {additional_capacity_mw} MW to {region_name} (current: {current_solar} MW) would exceed max penetration ({max_solar} MW).")
            return False
        return True

# Example Usage (for testing purposes, can be removed or commented out)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sample_grid_data = {
        'USA': {
            'existing_capacity_mw': 500000, 
            'current_load_mw': 450000,
            'max_solar_penetration_pct': 0.6, 
            'base_interconnection_cost_usd_per_mw': 120000 
        },
        'China': {
            'existing_capacity_mw': 1200000, 
            'current_load_mw': 1000000,
            'current_solar_mw': 50000 # Has some solar already
        }
    }
    grid_model_instance = GridModel(initial_regional_data=sample_grid_data)
    grid_model_instance.update_for_year(2025, regions=['USA', 'China'])
    
    print(f"Max solar for USA: {grid_model_instance.get_max_solar_penetration_mw('USA')} MW")
    print(f"Can add 10000 MW solar to USA: {grid_model_instance.check_grid_constraints('USA', 10000)}")
    grid_model_instance.add_solar_capacity('USA', 10000)
    print(f"Interconnection cost for 10000 MW in USA (10km): ${grid_model_instance.calculate_interconnection_costs('USA', 10000, 10):,.2f}")
    
    print(f"Max solar for China: {grid_model_instance.get_max_solar_penetration_mw('China')} MW")
    print(f"Current solar for China: {grid_model_instance.get_current_solar_mw('China')} MW")
    grid_model_instance.add_solar_capacity('China', 200000)
    print(f"Can add 200000 MW solar to China: {grid_model_instance.check_grid_constraints('China', 200000)}") # Should be true if limit allows
