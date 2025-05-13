"""
Models the evolution of manufacturing capacity for solar (ingot/wafer, cell, module)
and batteries, geographic diversification, and critical mineral requirements.
"""

class ManufacturingCapacityModel:
    """A class to model manufacturing capacity and material demands."""
    def __init__(self, capacity_data: dict, mineral_data: dict):
        """
        Initializes with current capacity and mineral intensity data.
        capacity_data: e.g., {'solar_module_gw_2025': {'China': 500, 'ROW': 100}}
        mineral_data: e.g., {'silver_grams_per_cell': 0.1, 'lithium_kg_per_kwh': 0.6}
        """
        self.capacity_data = capacity_data
        self.mineral_data = mineral_data
        print(f"ManufacturingCapacityModel initialized.")

    def project_manufacturing_capacity(self, component: str, year: int, region_projections: dict) -> dict:
        """Projects manufacturing capacity for a component and year based on regional growth.
        component: e.g., 'solar_module_gw', 'battery_gwh'
        region_projections: e.g., {'China': {'growth_rate': 0.1}, 'USA': {'new_capacity_gw': 50}}
        """
        current_capacities = self.capacity_data.get(f"{component}_2025", {})
        projected_capacities = current_capacities.copy()

        for region, proj in region_projections.items():
            current_cap = projected_capacities.get(region, 0)
            if 'growth_rate' in proj:
                projected_capacities[region] = current_cap * (1 + proj['growth_rate']) ** (year - 2025)
            elif 'new_capacity_gw' in proj: # or new_capacity_gwh
                projected_capacities[region] = current_cap + proj['new_capacity_gw']
        
        total_projected = sum(projected_capacities.values())
        print(f"Projected {component} capacity for {year}: {total_projected:.0f} (Details: {projected_capacities})")
        return projected_capacities

    def estimate_critical_mineral_demand(self, technology: str, production_volume: float) -> dict:
        """
        Estimates demand for critical minerals based on production volume.
        technology: e.g., 'silicon_pv_cells', 'lfp_battery_kwh'
        production_volume: e.g., number of cells, or kWh of batteries
        """
        demands = {}
        if technology == 'silicon_pv_cells':
            demands['silver_grams'] = production_volume * self.mineral_data.get('silver_grams_per_cell', 0)
        elif technology == 'lfp_battery_kwh':
            demands['lithium_kg'] = production_volume * self.mineral_data.get('lithium_kg_per_kwh_lfp', 0.5)
            demands['phosphate_kg'] = production_volume * self.mineral_data.get('phosphate_kg_per_kwh_lfp', 1.0)

        print(f"Estimated mineral demand for {production_volume} units of {technology}: {demands}")
        return demands

if __name__ == '__main__':
    # Example Usage
    cap_data = {
        'solar_module_gw_2025': {'China': 600, 'EU': 50, 'USA': 40, 'India': 30, 'SEA': 60},
        'battery_gwh_2025': {'China': 1000, 'EU': 150, 'USA': 100}
    }
    min_data = {
        'silver_grams_per_cell': 0.08, # Assuming approx. 2.5 cells per Watt, and 1GW = 2.5B cells
                                          # This implies per GW: 0.08 * 2.5 * 10^9 grams = 200,000 kg = 200 tonnes.
                                          # More typically, silver is 10-20 tonnes/GW. So, this needs calibration.
                                          # Let's use a more direct tonnes/GW for simplicity in example.
        'silver_tonnes_per_gw_module': 15, 
        'lithium_kg_per_kwh_lfp': 0.55,
        'phosphate_kg_per_kwh_lfp': 0.9
    }
    model = ManufacturingCapacityModel(capacity_data=cap_data, mineral_data=min_data)
    
    projections_solar = {
        'China': {'growth_rate': 0.08},
        'USA': {'new_capacity_gw': 100}, # Cumulative by 'year'
        'EU': {'growth_rate': 0.12}
    }
    model.project_manufacturing_capacity(component='solar_module_gw', year=2030, region_projections=projections_solar)
    
    # Correcting mineral demand to be per GW or GWh for easier use with capacity projections
    # For 100 GW of new silicon PV modules
    mineral_demand_pv = {'silver_tonnes': 100 * min_data['silver_tonnes_per_gw_module']}
    print(f"Mineral demand for 100 GW PV: {mineral_demand_pv}")

    # For 500 GWh of LFP batteries
    mineral_demand_battery = {
        'lithium_tonnes': (500000000 * min_data['lithium_kg_per_kwh_lfp']) / 1000,
        'phosphate_tonnes': (500000000 * min_data['phosphate_kg_per_kwh_lfp']) / 1000
    }
    print(f"Mineral demand for 500 GWh LFP batteries: {mineral_demand_battery}")
