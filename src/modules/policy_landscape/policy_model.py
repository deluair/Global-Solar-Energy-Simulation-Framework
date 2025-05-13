import datetime

class PolicyModel:
    """Models climate policies, support mechanisms, and their financial impacts."""

    def __init__(self, policies: list = None):
        """
        Initializes the PolicyModel with a list of policy details.
        Policies is a list of dictionaries, e.g.:
        [
            {
                'id': 'US_ITC_SOLAR_2025',
                'type': 'itc',  # Investment Tax Credit
                'value': 0.30,  # 30% of CAPEX
                'region': 'USA',
                'start_year': 2022,
                'end_year': 2032,
                'description': 'US Federal Solar Investment Tax Credit'
            },
            {
                'id': 'EU_CARBON_PRICE_2025',
                'type': 'carbon_price',
                'value': 80,  # 80 USD/ton CO2
                'region': 'EU',
                'start_year': 2025,
                'end_year': 2035,
                'description': 'EU ETS Carbon Price Projection'
            },
            {
                'id': 'GER_SOLAR_GRANT_ROOFTOP',
                'type': 'grant_capex_percentage',
                'value': 0.10, # 10% of CAPEX as an upfront grant
                'region': 'Germany',
                'technology_scope': ['rooftop_pv'],
                'max_system_kw': 100,
                'start_year': 2024,
                'end_year': 2028,
                'description': 'German grant for small rooftop PV systems'
            }
        ]
        """
        self.policies = policies if policies else []
        print(f"PolicyModel initialized with {len(self.policies)} policies.")

    def add_policy(self, policy_dict: dict):
        """Adds a new policy to the model."""
        self.policies.append(policy_dict)
        print(f"Added policy: {policy_dict.get('id', 'Unknown Policy')}")

    def get_active_policies(self, region: str = None, year: int = None, policy_type: str = None, technology: str = None) -> list:
        """Retrieves policies active for a given region, year, type, and technology."""
        active_policies = []
        current_year = year if year is not None else datetime.date.today().year

        for policy in self.policies:
            region_match = (region is None or policy.get('region') is None or policy.get('region') == region or region in policy.get('applicable_regions', []))
            year_match = (policy.get('start_year', -float('inf')) <= current_year <= policy.get('end_year', float('inf')))
            type_match = (policy_type is None or policy.get('type') == policy_type)
            tech_match = (technology is None or 
                          policy.get('technology_scope') is None or 
                          technology in policy.get('technology_scope', []))
            
            if region_match and year_match and type_match and tech_match:
                active_policies.append(policy)
        return active_policies

    def calculate_effective_capex_factor(self, region: str, year: int, technology: str = None) -> float:
        """
        Calculates the effective CAPEX factor after considering financial incentives.
        A factor of 1.0 means no change. A factor of 0.7 means CAPEX is reduced by 30%.
        Considers ITCs and direct CAPEX grants.
        """
        itc_policies = self.get_active_policies(region=region, year=year, policy_type='itc', technology=technology)
        grant_capex_percentage_policies = self.get_active_policies(region=region, year=year, policy_type='grant_capex_percentage', technology=technology)
        
        total_reduction_percentage = 0.0

        # Sum ITCs (assuming they are stackable if multiple apply, though unusual)
        for policy in itc_policies:
            total_reduction_percentage += policy.get('value', 0)
            print(f"  Applying ITC: {policy.get('id')} ({policy.get('value')*100}% reduction)")

        # Sum percentage grants (assuming stackable with ITCs and other grants)
        for policy in grant_capex_percentage_policies:
            total_reduction_percentage += policy.get('value', 0)
            print(f"  Applying CAPEX Grant: {policy.get('id')} ({policy.get('value')*100}% reduction)")
        
        # Ensure reduction doesn't exceed 100%
        total_reduction_percentage = min(total_reduction_percentage, 1.0)
        
        effective_capex_factor = 1.0 - total_reduction_percentage
        print(f"Effective CAPEX factor for {region} in {year} (Tech: {technology if technology else 'Any'}): {effective_capex_factor:.3f}")
        return effective_capex_factor

    def get_carbon_price(self, region: str, year: int) -> float:
        """
        Retrieves the applicable carbon price in USD/ton CO2 for a given region and year.
        If multiple carbon prices are found (e.g., sub-regional), it currently returns the first one found.
        A more sophisticated model might average or prioritize.
        """
        carbon_policies = self.get_active_policies(region=region, year=year, policy_type='carbon_price')
        if carbon_policies:
            # For simplicity, taking the first applicable carbon price found.
            # Real-world scenarios might need weighted averages or more specific targeting.
            price = carbon_policies[0].get('value', 0)
            print(f"Carbon price for {region} in {year}: ${price}/ton CO2 (Policy: {carbon_policies[0].get('id')})")
            return price
        print(f"No active carbon price found for {region} in {year}.")
        return 0.0

    def get_ptc_value(self, region: str, year: int, technology: str = None) -> float:
        """
        Retrieves the applicable Production Tax Credit (PTC) value for a given region, year, and technology.
        The value is typically in currency per unit of energy (e.g., USD/kWh).
        If multiple PTCs are found, it currently returns the first one found.
        A more sophisticated model might average, prioritize, or sum if stackable.
        """
        ptc_policies = self.get_active_policies(region=region, year=year, policy_type='ptc', technology=technology)
        if ptc_policies:
            # For simplicity, taking the first applicable PTC found.
            ptc_policy = ptc_policies[0]
            value = ptc_policy.get('value', 0)
            unit = ptc_policy.get('unit', 'currency/energy_unit') # e.g., USD/kWh
            print(f"PTC for {technology} in {region} ({year}): {value} {unit} (Policy: {ptc_policy.get('id')})")
            return value
        print(f"No active PTC found for {technology} in {region} ({year}).")
        return 0.0

    def get_rps_target(self, region: str, year: int, technology: str = None) -> dict:
        """
        Retrieves the applicable Renewable Portfolio Standard (RPS) target 
        for a given region, year, and optionally specific technology.

        Returns a dictionary with 'target_percentage', 'target_year', and 'policy_id',
        or None if no suitable RPS policy is found.
        It currently returns the first active RPS policy found matching the criteria.
        """
        # RPS policies are relevant if their target_year is in the future or current year
        # and the policy's own start_year has been met.
        rps_policies = []
        for policy in self.get_active_policies(region=region, policy_type='rps', technology=technology):
            # Ensure the policy is still relevant (target year not passed too far, or within its active period)
            # and the 'target_year' for RPS is a key consideration.
            if policy.get('start_year', -float('inf')) <= year <= policy.get('end_year', float('inf')):
                 # For RPS, we are interested if the current year is before or at its target_year
                if year <= policy.get('target_year', float('inf')):
                    rps_policies.append(policy)

        if rps_policies:
            # For simplicity, taking the first applicable RPS policy found.
            # A more complex model might prioritize (e.g., by nearest target_year or highest target_percentage)
            rps_policy = rps_policies[0] 
            target_info = {
                'policy_id': rps_policy.get('id'),
                'target_percentage': rps_policy.get('value'), # 'value' holds the percentage
                'target_year': rps_policy.get('target_year'),
                'eligible_technologies': rps_policy.get('technology_scope') # Re-using technology_scope for eligibility
            }
            print(f"RPS Target for {region} ({year}) (Tech: {technology if technology else 'Any'}): "
                  f"{target_info['target_percentage']*100}% by {target_info['target_year']} "
                  f"(Policy: {target_info['policy_id']})")
            return target_info
        
        print(f"No active RPS target found for {region} ({year}) (Tech: {technology if technology else 'Any'}).")
        return None

if __name__ == '__main__':
    example_policies = [
        {
            'id': 'US_ITC_SOLAR_2025',
            'type': 'itc',
            'value': 0.30,
            'region': 'USA',
            'start_year': 2022,
            'end_year': 2032,
            'technology_scope': ['solar_pv', 'csp'],
            'description': 'US Federal Solar Investment Tax Credit'
        },
        {
            'id': 'US_PTC_WIND_2025',
            'type': 'ptc', # Production Tax Credit
            'value': 0.025, # $/kWh
            'region': 'USA',
            'start_year': 2022,
            'end_year': 2030,
            'technology_scope': ['wind_onshore'],
            'description': 'US Federal Wind Production Tax Credit'
        },
        {
            'id': 'EU_CARBON_PRICE_2028',
            'type': 'carbon_price',
            'value': 95, # 95 USD/ton CO2
            'region': 'EU',
            'start_year': 2028,
            'end_year': 2035,
            'description': 'EU ETS Carbon Price Projection for 2028'
        },
        {
            'id': 'GER_SOLAR_GRANT_LARGE_UTILITY',
            'type': 'grant_capex_percentage',
            'value': 0.05, # 5% of CAPEX as an upfront grant
            'region': 'Germany',
            'technology_scope': ['utility_scale_pv'],
            'start_year': 2025,
            'end_year': 2027,
            'description': 'German grant for utility-scale PV systems'
        },
        {
            'id': 'CAL_RPS_2030',
            'type': 'rps',
            'value': 0.60, # 60% RPS target
            'region': 'USA', # Assuming California is within USA for this model's region filter
            'applicable_regions': ['California'], # More specific regional applicability
            'target_year': 2030,
            'start_year': 2020, # Policy active period
            'end_year': 2030,
            'technology_scope': ['solar_pv', 'wind_onshore', 'geothermal'], # Eligible technologies
            'description': 'California RPS: 60% by 2030'
        }
    ]

    policy_model = PolicyModel(policies=example_policies)

    print("\n--- CAPEX Factor Calculations ---")
    # Test USA Solar PV in 2025 (should get 30% ITC)
    usa_capex_factor_solar_2025 = policy_model.calculate_effective_capex_factor(region='USA', year=2025, technology='solar_pv')
    # Test USA Wind in 2025 (no CAPEX-reducing policy in example)
    usa_capex_factor_wind_2025 = policy_model.calculate_effective_capex_factor(region='USA', year=2025, technology='wind_onshore')
    # Test Germany Utility Scale PV in 2026 (should get 5% grant)
    ger_capex_factor_solar_2026 = policy_model.calculate_effective_capex_factor(region='Germany', year=2026, technology='utility_scale_pv')
    # Test Germany Rooftop PV in 2026 (no specific grant in example, should be 1.0)
    ger_capex_factor_rooftop_2026 = policy_model.calculate_effective_capex_factor(region='Germany', year=2026, technology='rooftop_pv')

    print("\n--- Carbon Price Calculations ---")
    # Test EU Carbon Price in 2028
    eu_carbon_price_2028 = policy_model.get_carbon_price(region='EU', year=2028)
    # Test US Carbon Price in 2028 (no policy in example)
    us_carbon_price_2028 = policy_model.get_carbon_price(region='USA', year=2028)
    # Test EU Carbon Price in 2024 (policy not active yet)
    eu_carbon_price_2024 = policy_model.get_carbon_price(region='EU', year=2024)

    print("\n--- PTC Value Calculations ---")
    # Test USA Wind PTC in 2025 (should get $0.025/kWh)
    usa_ptc_wind_2025 = policy_model.get_ptc_value(region='USA', year=2025, technology='wind_onshore')
    # Test USA Solar PV PTC in 2025 (no PTC policy for solar in example)
    usa_ptc_solar_2025 = policy_model.get_ptc_value(region='USA', year=2025, technology='solar_pv')

    print("\n--- RPS Target Calculations ---")
    # Test California RPS in 2025 for solar
    cal_rps_solar_2025 = policy_model.get_rps_target(region='California', year=2025, technology='solar_pv')
    # Test California RPS in 2031 (target year passed, but policy might still be in effect if end_year is later)
    # The current logic in get_rps_target checks if 'year <= policy.get('target_year')', 
    # and also if 'year <= policy.get('end_year')'. Let's test for 2030 (at target year).
    cal_rps_wind_2030 = policy_model.get_rps_target(region='California', year=2030, technology='wind_onshore')
    # Test for a non-RPS region or technology
    texas_rps_2025 = policy_model.get_rps_target(region='Texas', year=2025, technology='solar_pv')
    # Test California for a non-eligible technology
    cal_rps_nuclear_2025 = policy_model.get_rps_target(region='California', year=2025, technology='nuclear')

    # Example: Adding a new policy dynamically
    print("\n--- Dynamic Policy Addition ---")
    new_china_subsidy = {
        'id': 'CHINA_SOLAR_SUBSIDY_2026',
        'type': 'itc',
        'value': 0.15,
        'region': 'China',
        'start_year': 2026,
        'end_year': 2030,
        'technology_scope': ['solar_pv'],
        'description': 'New Chinese Solar PV Subsidy'
    }
    policy_model.add_policy(new_china_subsidy)
    china_capex_factor_2027 = policy_model.calculate_effective_capex_factor(region='China', year=2027, technology='solar_pv')
