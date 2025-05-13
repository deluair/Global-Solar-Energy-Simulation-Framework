"""
Models various carbon pricing mechanisms, including carbon taxes, emissions trading systems (ETS),
and carbon border adjustment mechanisms (CBAMs).
"""

class CarbonPricingMechanism:
    """A class to model the impact of different carbon pricing schemes."""
    def __init__(self, schemes: dict):
        """Initializes with details of various carbon pricing schemes.
        schemes: e.g., {'EU_ETS': {'type': 'cap_and_trade', 'price_per_ton_co2': 80}}
        """
        self.schemes = schemes
        print(f"CarbonPricingMechanism initialized with {len(self.schemes)} schemes.")

    def get_carbon_cost(self, emissions_tons_co2: float, region_scheme_name: str) -> float:
        """Calculates the cost of carbon emissions under a specific regional scheme."""
        scheme = self.schemes.get(region_scheme_name)
        if not scheme:
            print(f"Warning: Carbon pricing scheme '{region_scheme_name}' not found. Assuming $0 cost.")
            return 0.0
        
        price_per_ton = scheme.get('price_per_ton_co2', 0)
        total_cost = emissions_tons_co2 * price_per_ton
        print(f"Carbon cost for {emissions_tons_co2:.2f} tons CO2 under {region_scheme_name}: ${total_cost:.2f}")
        return total_cost

    def apply_cbam(self, product_embodied_carbon_tons: float, import_region: str, export_region_carbon_price: float = 0) -> float:
        """Applies a Carbon Border Adjustment Mechanism (CBAM) cost.
        Assumes import region has a CBAM and export region may or may not have a carbon price.
        """
        cbam_scheme = self.schemes.get(f"CBAM_{import_region}")
        if not cbam_scheme:
            # print(f"No CBAM found for import region '{import_region}'. Assuming $0 CBAM cost.")
            return 0.0
        
        import_region_carbon_price = cbam_scheme.get('reference_carbon_price_per_ton_co2', 0)
        price_difference = max(0, import_region_carbon_price - export_region_carbon_price)
        cbam_cost = product_embodied_carbon_tons * price_difference
        
        print(f"CBAM cost for product imported to {import_region} (Embodied: {product_embodied_carbon_tons}t CO2, Export Price: ${export_region_carbon_price}/t): ${cbam_cost:.2f}")
        return cbam_cost

if __name__ == '__main__':
    # Example Usage
    carbon_schemes = {
        'EU_ETS': {'type': 'cap_and_trade', 'price_per_ton_co2': 85},
        'California_CCA': {'type': 'cap_and_trade', 'price_per_ton_co2': 30},
        'CBAM_EU': {'type': 'cbam', 'reference_carbon_price_per_ton_co2': 85} # EU's internal price for CBAM
    }
    pricing_model = CarbonPricingMechanism(schemes=carbon_schemes)
    pricing_model.get_carbon_cost(emissions_tons_co2=1000, region_scheme_name='EU_ETS')
    # Simulate CBAM for a product with 50 tons embodied carbon imported into EU from a region with $10/ton carbon price
    pricing_model.apply_cbam(product_embodied_carbon_tons=50, import_region='EU', export_region_carbon_price=10)
    # Simulate CBAM for a product from a region with no carbon price
    pricing_model.apply_cbam(product_embodied_carbon_tons=50, import_region='EU', export_region_carbon_price=0)
