"""
Models the integration of solar energy with transportation electrification, including
EV smart charging, solar-powered charging infrastructure, and Vehicle-to-Grid (V2G) services.
"""

class TransportationElectrificationModel:
    """A class to model solar integration in the transportation sector."""
    def __init__(self, ev_fleet_data: dict, charging_infra_data: dict):
        """
        Initializes with EV fleet projections and charging infrastructure data.
        ev_fleet_data: e.g., {'RegionA': {'ev_penetration_2030': 0.3}}
        charging_infra_data: e.g., {'solar_powered_stations_pct_2025': 0.07}
        """
        self.ev_fleet_data = ev_fleet_data
        self.charging_infra_data = charging_infra_data
        print(f"TransportationElectrificationModel initialized.")

    def project_solar_charging_demand(self, region: str, year: int) -> float:
        """Projects the electricity demand from EVs that could be met by solar charging."""
        # Placeholder logic: very simplified
        ev_penetration = self.ev_fleet_data.get(region, {}).get(f'ev_penetration_{year}', 0.1)
        total_vehicles = 1000000 # Assume a fixed number of vehicles for simplicity
        ev_annual_kwh_per_vehicle = 3000 # kWh
        solar_charging_potential_pct = self.charging_infra_data.get('solar_powered_stations_pct_2030_target', 0.4)
        
        projected_demand_gwh = (total_vehicles * ev_penetration * ev_annual_kwh_per_vehicle * solar_charging_potential_pct) / 1_000_000
        print(f"Projected solar EV charging demand in {region} for {year}: {projected_demand_gwh:.2f} GWh")
        return projected_demand_gwh

    def assess_v2g_potential(self, region: str, enabled_evs_count: int, avg_battery_kwh: float = 60) -> float:
        """Assesses the potential Vehicle-to-Grid (V2G) capacity."""
        # Assume only a fraction of battery is available for V2G and for a limited time
        v2g_capacity_per_ev_kw = avg_battery_kwh * 0.1 # 10% of battery capacity as power
        total_v2g_potential_mw = (enabled_evs_count * v2g_capacity_per_ev_kw) / 1000
        print(f"V2G potential in {region} from {enabled_evs_count} EVs: {total_v2g_potential_mw:.2f} MW")
        return total_v2g_potential_mw

if __name__ == '__main__':
    # Example Usage
    ev_data = {'California': {'ev_penetration_2030': 0.5, 'ev_penetration_2035': 0.75}}
    charge_data = {'solar_powered_stations_pct_2030_target': 0.42}
    model = TransportationElectrificationModel(ev_fleet_data=ev_data, charging_infra_data=charge_data)
    
    model.project_solar_charging_demand(region='California', year=2030)
    model.assess_v2g_potential(region='California', enabled_evs_count=500000, avg_battery_kwh=70)
