import datetime

class SolarTechnology:
    """Represents a specific solar photovoltaic technology and its parameters."""
    def __init__(self, name: str, 
                 base_efficiency: float, # Efficiency at commercial_scale_year or start_year
                 projected_efficiency_2035: float, 
                 start_year: int, # Year for base_efficiency
                 commercial_scale_year: int, 
                 degradation_rate_annual: float = 0.005, # 0.5% per year default
                 base_capex_usd_per_kw: float = 1000,
                 annual_capex_reduction_rate: float = 0.02): # Default 2% annual CAPEX reduction
        self.name = name
        self.base_efficiency = base_efficiency
        self.projected_efficiency_2035 = projected_efficiency_2035
        self.start_year = start_year
        self.commercial_scale_year = commercial_scale_year
        self.degradation_rate_annual = degradation_rate_annual
        self.base_capex_usd_per_kw = base_capex_usd_per_kw
        self.annual_capex_reduction_rate = annual_capex_reduction_rate

        if self.start_year > 2035:
            # If start_year is beyond 2035, the annual improvement rate calculation would be problematic.
            # For simplicity, assume projected_efficiency_2035 is the efficiency for start_year if start_year > 2035.
            self.annual_efficiency_improvement = 0
        elif self.projected_efficiency_2035 <= self.base_efficiency or self.start_year == 2035:
            self.annual_efficiency_improvement = 0
        else:
            # Linear interpolation for annual improvement
            self.annual_efficiency_improvement = (self.projected_efficiency_2035 - self.base_efficiency) / (2035 - self.start_year)

    def get_params_for_year(self, year: int) -> dict:
        """Calculates technology parameters for a given year using linear interpolation for efficiency."""
        if year < self.start_year:
            # Technology not yet available or using base_efficiency if before official start
            current_efficiency = self.base_efficiency 
        elif year >= 2035:
            current_efficiency = self.projected_efficiency_2035
        else:
            years_since_start = year - self.start_year
            current_efficiency = self.base_efficiency + (self.annual_efficiency_improvement * years_since_start)
            current_efficiency = min(current_efficiency, self.projected_efficiency_2035) # Cap at projected max

        # Apply CAPEX learning curve
        if year < self.start_year:
            current_capex = self.base_capex_usd_per_kw
        else:
            years_for_capex_reduction = year - self.start_year
            current_capex = self.base_capex_usd_per_kw * ((1 - self.annual_capex_reduction_rate) ** years_for_capex_reduction)
            current_capex = max(current_capex, 0) # Ensure CAPEX doesn't go negative

        return {
            'name': self.name,
            'year': year,
            'efficiency': round(current_efficiency, 4),
            'degradation_rate_annual': self.degradation_rate_annual,
            'capex_usd_per_kw': round(current_capex, 2),
            'is_commercially_available': year >= self.commercial_scale_year,
            'commercial_scale_year': self.commercial_scale_year
        }

    def __repr__(self):
        return f"SolarTechnology({self.name}, BaseEff: {self.base_efficiency}, ProjEff2035: {self.projected_efficiency_2035}, StartYr: {self.start_year}, CapexReduction: {self.annual_capex_reduction_rate*100}%)"

class SolarTechModel:
    """Manages a portfolio of solar technologies and their evolution."""
    def __init__(self):
        self.technologies = {}
        print("SolarTechModel initialized.")

    def add_technology(self, tech: SolarTechnology):
        self.technologies[tech.name] = tech
        print(f"Added technology: {tech.name}")

    def get_technology_details(self, tech_name: str, year: int) -> dict:
        if tech_name not in self.technologies:
            return {'error': f"Technology '{tech_name}' not found."}
        
        tech = self.technologies[tech_name]
        return tech.get_params_for_year(year)

    def list_technologies(self, year: int = None) -> list:
        """Lists available technologies. If year is provided, lists only commercially available ones."""
        if year is None:
            return list(self.technologies.keys())
        else:
            available_techs = []
            for name, tech in self.technologies.items():
                if year >= tech.commercial_scale_year:
                    available_techs.append(name)
            return available_techs

if __name__ == '__main__':
    stm = SolarTechModel()

    # Data based on project description (adjust as needed)
    # Silicon Technologies
    topcon = SolarTechnology(
        name='TOPCon',
        base_efficiency=0.225, # Assuming 2023/2024 base
        projected_efficiency_2035=0.265, # Slightly adjusted from 25.5% by 2030 to a 2035 value
        start_year=2023,
        commercial_scale_year=2022, # Already commercial
        degradation_rate_annual=0.004,
        base_capex_usd_per_kw=700,
        annual_capex_reduction_rate=0.03 # 3% per year for TOPCon
    )
    stm.add_technology(topcon)

    hjt = SolarTechnology(
        name='HJT',
        base_efficiency=0.235, # Assuming 2023/2024 base
        projected_efficiency_2035=0.275, # Slightly adjusted from 26.8% by 2030 to a 2035 value
        start_year=2023,
        commercial_scale_year=2023,
        degradation_rate_annual=0.003,
        base_capex_usd_per_kw=750,
        annual_capex_reduction_rate=0.035 # 3.5% per year for HJT
    )
    stm.add_technology(hjt)

    # Tandem Architectures
    si_perovskite_tandem = SolarTechnology(
        name='Silicon-Perovskite Tandem',
        base_efficiency=0.280, # Assuming a near-term commercial efficiency
        projected_efficiency_2035=0.350, # Based on 34.6% demonstrated, targeting 35% by 2035
        start_year=2026, # Projected start for wider commercial availability
        commercial_scale_year=2028, # As per project description
        degradation_rate_annual=0.007, # Higher initially for perovskites
        base_capex_usd_per_kw=900,
        annual_capex_reduction_rate=0.05 # 5% per year for Tandems, aggressive learning
    )
    stm.add_technology(si_perovskite_tandem)

    print("\n--- Technology Details for 2025 ---")
    for tech_name in stm.list_technologies():
        details = stm.get_technology_details(tech_name, 2025)
        print(details)

    print("\n--- Technology Details for 2030 ---")
    for tech_name in stm.list_technologies():
        details = stm.get_technology_details(tech_name, 2030)
        print(details)
    
    print("\n--- Commercially Available Technologies in 2027 ---")
    print(stm.list_technologies(year=2027))

    print("\n--- Details for Silicon-Perovskite Tandem over time ---")
    print(stm.get_technology_details('Silicon-Perovskite Tandem', 2026))
    print(stm.get_technology_details('Silicon-Perovskite Tandem', 2028))
    print(stm.get_technology_details('Silicon-Perovskite Tandem', 2035))
