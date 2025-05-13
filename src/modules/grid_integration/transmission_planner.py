"""
Models transmission expansion planning, including costs, timelines, and constraints
for major grid regions and cross-border interconnections.
"""

class TransmissionPlanner:
    """A class to model and plan transmission infrastructure expansion."""
    def __init__(self, regional_grid_data: dict):
        """Initializes TransmissionPlanner with regional grid data.
        regional_grid_data: e.g., {'RegionA': {'capacity_gw': 100, 'expansion_cost_per_gw_mile': 1M}}
        """
        self.regional_grid_data = regional_grid_data
        print(f"TransmissionPlanner initialized for {len(self.regional_grid_data)} regions.")

    def evaluate_expansion_project(self, region: str, new_capacity_gw: float, distance_miles: float) -> dict:
        """Evaluates a potential transmission expansion project."""
        region_data = self.regional_grid_data.get(region)
        if not region_data:
            print(f"Warning: Grid data not found for region '{region}'.")
            return {'cost_estimate_usd': float('inf'), 'status': 'failed_no_data'}

        cost_per_gw_mile = region_data.get('expansion_cost_per_gw_mile', 1000000) # Default 1M USD
        estimated_cost = new_capacity_gw * distance_miles * cost_per_gw_mile
        
        # Placeholder for timeline and constraint checks
        estimated_timeline_years = 3 + (new_capacity_gw * distance_miles) / 1000 # Simplified

        print(f"Project Evaluation for {region}: Add {new_capacity_gw}GW over {distance_miles} miles.")
        print(f"  Estimated Cost: ${estimated_cost:,.0f} USD")
        print(f"  Estimated Timeline: {estimated_timeline_years:.1f} years")
        return {
            'region': region,
            'new_capacity_gw': new_capacity_gw,
            'distance_miles': distance_miles,
            'cost_estimate_usd': estimated_cost,
            'timeline_years': estimated_timeline_years
        }

    def assess_interconnection_viability(self, region_a: str, region_b: str, capacity_gw: float) -> str:
        """Assesses the viability of a cross-border interconnection."""
        # Placeholder for more complex viability assessment
        print(f"Assessing interconnection: {region_a} <-> {region_b} ({capacity_gw} GW).")
        if self.regional_grid_data.get(region_a) and self.regional_grid_data.get(region_b):
            # Simplistic check: e.g. based on existing capacities or policies
            return "Potentially Viable (Further study needed)"
        return "Likely Not Viable (Missing regional data or major constraints)"

if __name__ == '__main__':
    # Example Usage
    grid_data = {
        'North_Zone': {'capacity_gw': 150, 'expansion_cost_per_gw_mile': 800000},
        'South_Zone': {'capacity_gw': 120, 'expansion_cost_per_gw_mile': 1200000}
    }
    planner = TransmissionPlanner(regional_grid_data=grid_data)
    planner.evaluate_expansion_project(region='North_Zone', new_capacity_gw=20, distance_miles=100)
    planner.assess_interconnection_viability(region_a='North_Zone', region_b='South_Zone', capacity_gw=10)
