"""
Handles calculations related to carbon emissions, life-cycle carbon accounting,
and the impact of carbon pricing mechanisms.
"""

class CarbonCalculator:
    """A class for calculating carbon footprints and mitigation effects."""
    def __init__(self, emission_factors: dict):
        """Initializes the CarbonCalculator with emission factors."""
        self.emission_factors = emission_factors # e.g., {'coal': 900, 'gas': 450, 'solar': 20} gCO2e/kWh
        print(f"CarbonCalculator initialized with {len(self.emission_factors)} emission factors.")

    def calculate_lifecycle_carbon(self, technology: str, energy_kwh: float) -> float:
        """Calculates the life-cycle carbon emissions for a given technology and energy output."""
        factor = self.emission_factors.get(technology.lower(), 0)
        carbon_grams = factor * energy_kwh
        print(f"Life-cycle carbon for {energy_kwh} kWh of {technology}: {carbon_grams:.2f} gCO2e")
        return carbon_grams

    def calculate_emissions_displacement(self, solar_kwh: float, displaced_tech_kwh_mix: dict) -> float:
        """Calculates displaced emissions by solar energy replacing other technologies."""
        displaced_emissions = 0
        solar_emissions_factor = self.emission_factors.get('solar', 20) # Default for solar

        for tech, kwh in displaced_tech_kwh_mix.items():
            tech_emissions_factor = self.emission_factors.get(tech.lower(), 0)
            displaced_emissions += (tech_emissions_factor - solar_emissions_factor) * kwh
        
        print(f"Total displaced emissions by {solar_kwh} kWh of solar: {displaced_emissions:.2f} gCO2e")
        return displaced_emissions

if __name__ == '__main__':
    # Example usage
    factors = {
        'coal': 950, # gCO2e/kWh
        'natural_gas': 480, # gCO2e/kWh
        'solar': 15, # gCO2e/kWh (updated for future tech)
        'wind': 12 # gCO2e/kWh
    }
    calculator = CarbonCalculator(emission_factors=factors)
    calculator.calculate_lifecycle_carbon(technology='solar', energy_kwh=1000)
    calculator.calculate_lifecycle_carbon(technology='coal', energy_kwh=1000)

    displaced_mix = {'coal': 600, 'natural_gas': 400} # kWh replaced by 1000 kWh solar
    calculator.calculate_emissions_displacement(solar_kwh=1000, displaced_tech_kwh_mix=displaced_mix)
