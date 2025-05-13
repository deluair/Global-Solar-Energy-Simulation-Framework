"""
Models supply chain resilience, including concentration risk (HHI), onshoring/friendshoring
trends, end-of-life management (recycling), and ESG compliance.
"""
import math

class SupplyChainResilienceModel:
    """A class to model and assess supply chain resilience factors."""
    def __init__(self, market_share_data: dict, recycling_data: dict):
        """
        Initializes with market share data for HHI calc and recycling capacity info.
        market_share_data: e.g., {'polysilicon_production': {'CompanyA': 0.4, 'CompanyB': 0.3}}
        recycling_data: e.g., {'solar_panel_recycling_capacity_gw_2025': 15}
        """
        self.market_share_data = market_share_data
        self.recycling_data = recycling_data
        print(f"SupplyChainResilienceModel initialized.")

    def calculate_hhi(self, component_key: str) -> float:
        """Calculates the Herfindahl-Hirschman Index (HHI) for a given component/material."""
        shares = self.market_share_data.get(component_key, {})
        if not shares:
            print(f"Warning: Market share data not found for '{component_key}'. Returning HHI of -1.")
            return -1.0
        
        hhi = sum([(share * 100) ** 2 for share in shares.values()])
        concentration = "Low"
        if hhi > 1500:
            concentration = "Moderate"
        if hhi > 2500:
            concentration = "High"
        
        print(f"HHI for {component_key}: {hhi:.0f} (Concentration: {concentration})")
        return hhi

    def project_recycling_capacity(self, year: int, annual_growth_rate: float = 0.20) -> float:
        """Projects end-of-life solar panel recycling capacity."""
        base_capacity = self.recycling_data.get('solar_panel_recycling_capacity_gw_2025', 0)
        # Simple exponential growth projection
        projected_capacity_gw = base_capacity * (1 + annual_growth_rate) ** (year - 2025)
        print(f"Projected solar panel recycling capacity for {year}: {projected_capacity_gw:.1f} GW/year")
        return projected_capacity_gw

    def assess_esg_compliance_risk(self, supplier_profile: dict) -> str:
        """
        Assesses ESG compliance risk based on supplier profile (simplified).
        supplier_profile: e.g., {'traceability_score': 0.8, 'labor_standards_audit': 'pass'}
        """
        # Placeholder logic
        risk_level = "Low"
        if supplier_profile.get('traceability_score', 0) < 0.7:
            risk_level = "Medium"
        if supplier_profile.get('labor_standards_audit') == 'fail':
            risk_level = "High"
        
        print(f"ESG Compliance Risk Assessment: {risk_level}")
        return risk_level

if __name__ == '__main__':
    # Example Usage
    market_shares = {
        'polysilicon_production': {'CompanyA': 0.35, 'CompanyB': 0.25, 'CompanyC': 0.15, 'CompanyD': 0.10, 'Others': 0.15},
        'lithium_refining': {'RefinerX': 0.5, 'RefinerY': 0.3, 'RefinerZ': 0.2}
    }
    recycling_info = {'solar_panel_recycling_capacity_gw_2025': 20}
    model = SupplyChainResilienceModel(market_share_data=market_shares, recycling_data=recycling_info)
    
    model.calculate_hhi(component_key='polysilicon_production')
    model.calculate_hhi(component_key='lithium_refining')
    
    model.project_recycling_capacity(year=2030, annual_growth_rate=0.25)
    model.project_recycling_capacity(year=2035, annual_growth_rate=0.22) # growth may slow over time

    supplier_A_profile = {'traceability_score': 0.9, 'labor_standards_audit': 'pass', 'carbon_footprint_kgCO2eq_per_unit': 5}
    model.assess_esg_compliance_risk(supplier_profile=supplier_A_profile)
    
    supplier_B_profile = {'traceability_score': 0.6, 'labor_standards_audit': 'pending', 'carbon_footprint_kgCO2eq_per_unit': 8}
    model.assess_esg_compliance_risk(supplier_profile=supplier_B_profile)
