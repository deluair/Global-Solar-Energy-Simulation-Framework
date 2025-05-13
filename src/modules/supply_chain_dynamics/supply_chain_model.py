import math

# --- Default Initial Supply Chain Data ---
initial_data = {
    'polysilicon': {
        'global_capacity_tons_per_year': 4000000, # Updated based on regional sum
        'regional_capacity_tons_per_year': {'China': 3700000, 'USA': 150000, 'Germany': 100000, 'Rest': 50000},
        'criticality_score': 0.8
    },
    'solar_modules': {
        'global_capacity_gw_per_year': 950, # Updated based on regional sum
        'regional_capacity_gw_per_year': {'China': 750, 'Vietnam': 50, 'India': 40, 'USA': 30, 'EU': 50, 'ROW': 80},
        'components_kg_per_mw': {'polysilicon': 3000, 'silver': 500} # kg per MW for modules
    },
    'lithium_carbonate': {
        'global_capacity_tons_per_year': 1500000, # Updated based on regional sum
        'regional_capacity_tons_per_year': {'Australia': 250000, 'Chile': 200000, 'China': 1100000, 'Argentina': 100000, 'Rest': 50000}
    }
}
# Correct global capacities based on regional sum for consistency in example data
for _item_name_init in list(initial_data.keys()): # Use a different loop variable name to avoid conflicts if run in global scope
    _item_data_init = initial_data[_item_name_init]
    for _key_init in list(_item_data_init.keys()):
        _val_init = _item_data_init[_key_init]
        if _key_init.startswith('regional_capacity_') and isinstance(_val_init, dict):
            _global_key_init = _key_init.replace('regional_capacity_', 'global_capacity_')
            _item_data_init[_global_key_init] = sum(_val_init.values())

class SupplyChainModel:
    """Models manufacturing capacity, material availability, and supply chain risks."""

    def __init__(self, initial_supply_data: dict = None):
        """
        Initializes the SupplyChainModel with data on materials, components, and capacities.
        initial_supply_data: e.g.,
        {
            'polysilicon': {
                'global_capacity_tons_per_year': 1200000,
                'regional_capacity_tons_per_year': {'China': 900000, 'USA': 150000, 'Germany': 100000, 'Rest': 50000},
                'criticality_score': 0.8 # Subjective score 0-1
            },
            'solar_modules': {
                'global_capacity_gw_per_year': 800,
                'regional_capacity_gw_per_year': {'China': 600, 'Vietnam': 50, 'India': 40, 'USA': 30, 'EU': 40, 'Rest': 40},
                'components': {'polysilicon_kg_per_kw': 3.0, 'silver_g_per_kw': 0.5}
            }
        }
        """
        if initial_supply_data is None:
            # Use a deep copy of the global initial_data to avoid modifying it inadvertently
            import copy
            self.supply_data = copy.deepcopy(initial_data)
        else:
            self.supply_data = initial_supply_data
        print(f"SupplyChainModel initialized with {len(self.supply_data)} primary items.")

    def add_supply_item(self, item_name: str, data: dict):
        """Adds or updates a supply chain item (material, component)."""
        self.supply_data[item_name] = data
        print(f"Supply item '{item_name}' added/updated.")

    def get_material_availability(self, material_name: str, required_annual_quantity: float) -> dict:
        """
        Checks if a sufficient annual quantity of a material is available based on global capacity.
        Returns a dict with availability status and details.
        This is a simplification; a real model would track inventory, production rates, and lead times.
        """
        item = self.supply_data.get(material_name)
        if not item or 'global_capacity_tons_per_year' not in item: # Assuming tons for raw materials for now
            print(f"Warning: Data or global capacity not found for material '{material_name}'.")
            return {'available': False, 'reason': f"Data or global capacity not found for '{material_name}'", 'shortfall': required_annual_quantity}

        global_capacity = item['global_capacity_tons_per_year']
        if global_capacity >= required_annual_quantity:
            return {'available': True, 'global_capacity': global_capacity, 'required': required_annual_quantity, 'surplus': global_capacity - required_annual_quantity}
        else:
            return {'available': False, 'global_capacity': global_capacity, 'required': required_annual_quantity, 'shortfall': required_annual_quantity - global_capacity, 'reason': 'Required quantity exceeds global capacity'}

    def calculate_hhi(self, shares: list) -> float:
        """Calculates the Herfindahl-Hirschman Index (HHI). Shares should be percentages (0-100)."""
        if not shares or sum(shares) == 0:
            return 0.0 # Or handle as an error/undefined
        # Ensure shares sum to roughly 100 if they are market shares
        # For simplicity, we assume the input 'shares' are correct market shares.
        hhi = sum(s**2 for s in shares)
        return hhi

    def get_concentration_risk(self, item_name: str, capacity_key: str = 'regional_capacity_tons_per_year') -> dict:
        """
        Calculates concentration risk for a component/material using HHI based on regional capacities.
        capacity_key: The dictionary key that holds the regional capacity data (e.g., '_tons_per_year' or '_gw_per_year').
        Returns HHI score and a qualitative assessment.
        HHI < 1500: Unconcentrated
        1500 <= HHI <= 2500: Moderately concentrated
        HHI > 2500: Highly concentrated
        """
        item = self.supply_data.get(item_name)
        if not item or capacity_key not in item:
            return {'hhi': -1, 'assessment': 'Data not found', 'error': f"Item or capacity key '{capacity_key}' not found for '{item_name}'."}

        regional_capacities = item[capacity_key]
        if not isinstance(regional_capacities, dict) or not regional_capacities:
             return {'hhi': -1, 'assessment': 'Regional capacity data invalid', 'error': f"Regional capacity data for '{item_name}' is missing or not a dict."}

        total_capacity = sum(regional_capacities.values())
        if total_capacity == 0:
            return {'hhi': 0, 'assessment': 'No capacity', 'details': 'Total regional capacity is zero.'}

        market_shares_pct = [(capacity / total_capacity) * 100 for capacity in regional_capacities.values()]
        hhi_score = self.calculate_hhi(market_shares_pct)

        assessment = "Highly concentrated"
        if hhi_score < 1500:
            assessment = "Unconcentrated (Competitive)"
        elif hhi_score <= 2500:
            assessment = "Moderately concentrated"
        
        return {
            'item_name': item_name,
            'hhi': round(hhi_score, 2),
            'assessment': assessment,
            'regional_shares_pct': {region: round((cap/total_capacity)*100, 2) for region, cap in regional_capacities.items()}
        }

    def model_capacity_expansion(self, item_name: str, region: str, additional_capacity: float, year: int, capacity_key_suffix: str = '_tons_per_year'):
        """
        Placeholder to model future capacity expansions for a material/component in a region.
        capacity_key_suffix: e.g., '_tons_per_year' or '_gw_per_year'
        """
        # This is a simplified model. A real model would involve investment, lead times, etc.
        regional_capacity_key = 'regional_capacity' + capacity_key_suffix
        global_capacity_key = 'global_capacity' + capacity_key_suffix

        if item_name not in self.supply_data:
            print(f"Warning: Item '{item_name}' not found. Cannot expand capacity.")
            return
        
        item = self.supply_data[item_name]
        if regional_capacity_key not in item:
            item[regional_capacity_key] = {}
        if global_capacity_key not in item:
            item[global_capacity_key] = 0

        item[regional_capacity_key][region] = item[regional_capacity_key].get(region, 0) + additional_capacity
        item[global_capacity_key] = sum(item[regional_capacity_key].values()) # Recalculate global from regional

        print(f"Capacity expansion for '{item_name}' in {region} by {additional_capacity} in {year} modeled.")
        print(f"  New regional capacity for {region}: {item[regional_capacity_key][region]}")
        print(f"  New global capacity for {item_name}: {item[global_capacity_key]}")


if __name__ == '__main__':
    # The initial_data is now defined globally and used by default in the constructor.
    # So, we can directly instantiate scm without passing initial_data, 
    # or pass a custom one if needed for this specific test.
    scm = SupplyChainModel() # Uses global initial_data by default

    # Test with a custom, minimal dataset if needed for a specific __main__ test:
    # custom_test_data = { 
    #     'polysilicon': {
    #         'global_capacity_tons_per_year': 1200000,
    #         'regional_capacity_tons_per_year': {'China': 900000, 'USA': 150000, 'Germany': 100000, 'Rest': 50000},
    #         'criticality_score': 0.8
    #     },
    #     'solar_modules': {
    #         'global_capacity_gw_per_year': 800,
    #         'regional_capacity_gw_per_year': {'China': 600, 'Vietnam': 50, 'India': 40, 'USA': 30, 'EU': 40, 'Rest': 40},
    #         'components': {'polysilicon_kg_per_kw': 3.0, 'silver_g_per_kw': 0.5}
    #     }
    # }
    # scm = SupplyChainModel(initial_supply_data=custom_test_data)

    print("\n--- Material Availability Check (using default global data) ---")
    poly_needed_tons = 1000000 # Request 1M tons
    availability_poly = scm.get_material_availability('polysilicon', poly_needed_tons)
    print(f"Polysilicon (need {poly_needed_tons} tons): Available - {availability_poly['available']}, Shortfall/Surplus: {availability_poly.get('shortfall', -availability_poly.get('surplus',0))}")

    li_needed_tons = 800000 # Request 0.8M tons
    availability_li = scm.get_material_availability('lithium_carbonate', li_needed_tons)
    print(f"Lithium Carbonate (need {li_needed_tons} tons): Available - {availability_li['available']}, Shortfall/Surplus: {availability_li.get('shortfall', -availability_li.get('surplus',0))}")

    print("\n--- Concentration Risk (HHI) ---")
    hhi_polysilicon = scm.get_concentration_risk('polysilicon', 'regional_capacity_tons_per_year')
    print(f"Polysilicon HHI: {hhi_polysilicon.get('hhi')} ({hhi_polysilicon.get('assessment')})")
    print(f"  Shares: {hhi_polysilicon.get('regional_shares_pct')}")
    
    hhi_modules = scm.get_concentration_risk('solar_modules', 'regional_capacity_gw_per_year')
    print(f"Solar Modules HHI: {hhi_modules.get('hhi')} ({hhi_modules.get('assessment')})")
    print(f"  Shares: {hhi_modules.get('regional_shares_pct')}")

    hhi_lithium = scm.get_concentration_risk('lithium_carbonate', 'regional_capacity_tons_per_year')
    print(f"Lithium Carbonate HHI: {hhi_lithium.get('hhi')} ({hhi_lithium.get('assessment')})")
    print(f"  Shares: {hhi_lithium.get('regional_shares_pct')}")

    print("\n--- Capacity Expansion Modeling ---")
    scm.model_capacity_expansion('polysilicon', 'USA', additional_capacity=100000, year=2028, capacity_key_suffix='_tons_per_year')
    hhi_polysilicon_after_expansion = scm.get_concentration_risk('polysilicon', 'regional_capacity_tons_per_year')
    print(f"Polysilicon HHI after US expansion: {hhi_polysilicon_after_expansion.get('hhi')} ({hhi_polysilicon_after_expansion.get('assessment')})")
    print(f"  New Shares: {hhi_polysilicon_after_expansion.get('regional_shares_pct')}")

    scm.model_capacity_expansion('solar_modules', 'EU', additional_capacity=50, year=2027, capacity_key_suffix='_gw_per_year')
    hhi_modules_after_expansion = scm.get_concentration_risk('solar_modules', 'regional_capacity_gw_per_year')
    print(f"Solar Modules HHI after EU expansion: {hhi_modules_after_expansion.get('hhi')} ({hhi_modules_after_expansion.get('assessment')})")
    print(f"  New Shares: {hhi_modules_after_expansion.get('regional_shares_pct')}")
