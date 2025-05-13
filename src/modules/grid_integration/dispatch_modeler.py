"""
Handles sub-hourly dispatch modeling, system inertia evolution tracking,
and the adoption of grid-forming inverters.
"""

class DispatchModeler:
    """A class for modeling power system dispatch and inertia characteristics."""
    def __init__(self, system_parameters: dict):
        """Initializes DispatchModeler with system parameters.
        system_parameters: e.g., {'initial_inertia_gws': 200, 'gf_inverter_adoption_rate': 0.05}
        """
        self.system_parameters = system_parameters
        self.current_inertia_gws = system_parameters.get('initial_inertia_gws', 0)
        print(f"DispatchModeler initialized. Initial system inertia: {self.current_inertia_gws} GWs.")

    def simulate_dispatch(self, demand_profile_mw: list, solar_profile_mw: list, other_generation_mw: list) -> dict:
        """Simulates dispatch for a given period (e.g., 24 hours, sub-hourly steps).
        Profiles are lists of power values for each time step.
        """
        # Highly simplified dispatch logic
        curtailment_mwh = 0
        unmet_demand_mwh = 0
        time_steps = len(demand_profile_mw)

        for i in range(time_steps):
            available_supply = solar_profile_mw[i] + other_generation_mw[i]
            demand = demand_profile_mw[i]
            if available_supply > demand:
                curtailment_mwh += (available_supply - demand) # Assuming 1-hour steps for MWh
            elif available_supply < demand:
                unmet_demand_mwh += (demand - available_supply)
        
        print(f"Dispatch simulation over {time_steps} steps:")
        print(f"  Total curtailment: {curtailment_mwh:.2f} MWh")
        print(f"  Total unmet demand: {unmet_demand_mwh:.2f} MWh")
        return {'curtailment_mwh': curtailment_mwh, 'unmet_demand_mwh': unmet_demand_mwh}

    def project_system_inertia(self, year: int, conventional_retirements_gw: float, gf_inverters_added_gw: float) -> float:
        """Projects system inertia based on generator retirements and grid-forming inverter additions."""
        # Simplified inertia calculation
        # Assume conventional plants contribute significantly more inertia per GW than inverters initially
        inertia_loss_from_retirements = conventional_retirements_gw * 5 # Example factor: 5 GWs of inertia per GW capacity
        inertia_gain_from_gfi = gf_inverters_added_gw * 1 # Example factor
        
        self.current_inertia_gws = self.current_inertia_gws - inertia_loss_from_retirements + inertia_gain_from_gfi
        self.current_inertia_gws = max(0, self.current_inertia_gws) # Inertia cannot be negative

        print(f"Projected system inertia for year {year}: {self.current_inertia_gws:.2f} GWs")
        return self.current_inertia_gws

if __name__ == '__main__':
    # Example Usage
    params = {'initial_inertia_gws': 250, 'gf_inverter_adoption_rate': 0.05}
    modeler = DispatchModeler(system_parameters=params)
    
    demand = [100, 110, 120, 150, 160, 155, 140, 120] # MW for 8 time steps
    solar =  [0,   5,   20,  50,  60,  55,  30,  0]   # MW
    other  = [100, 100, 100, 100, 100, 100, 100, 100] # MW (baseload/dispatchable)
    modeler.simulate_dispatch(demand_profile_mw=demand, solar_profile_mw=solar, other_generation_mw=other)
    
    modeler.project_system_inertia(year=2030, conventional_retirements_gw=10, gf_inverters_added_gw=5)
