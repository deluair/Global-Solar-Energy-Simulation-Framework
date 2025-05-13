"""
Models the use of solar energy for industrial decarbonization, including green hydrogen production,
industrial heat applications, and pathways for emission-intensive industries.
"""

import math
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology 
    from ..economic_framework.cost_model import CostModel

class IndustrialDecarbonizationModel:
    """A class to model solar energy's role in industrial decarbonization."""
    def __init__(self, industry_data: Dict[str, Any]):
        """
        Initializes with data on industrial energy demand and processes.
        industry_data: e.g., {'Steel_EU': {'current_emissions_mtco2': 150, 'hydrogen_demand_potential_mt': 5}}
        """
        self.industry_data = industry_data
        print(f"IndustrialDecarbonizationModel initialized for {len(self.industry_data)} industrial sectors/regions.")

    def estimate_green_hydrogen_production_cost(self, 
                                                solar_tech_model: 'SolarTechModel',
                                                solar_cost_model: 'CostModel',
                                                solar_tech_name: str,
                                                solar_project_year: int,
                                                solar_project_capacity_factor: float,
                                                solar_project_discount_rate: float,
                                                solar_project_lifetime_years: int,
                                                electrolyzer_capex_usd_per_kw: int, 
                                                electrolyzer_efficiency_kwh_per_kg_h2: float = 50.0, 
                                                electrolyzer_capacity_factor: float = 0.60, 
                                                electrolyzer_discount_rate: float = 0.08, 
                                                electrolyzer_lifetime_years: int = 20,
                                                stack_lifetime_hours: int = 80000,
                                                stack_replacement_cost_pct_capex: float = 0.40, 
                                                fixed_om_cost_pct_capex: float = 0.02, 
                                                variable_om_cost_usd_per_mwh: float = 1.0 
                                                ) -> float:
        """Estimates the Levelized Cost of Hydrogen (LCOH) in $/kg.
        
        Args:
            solar_tech_model: Instance of SolarTechModel.
            solar_cost_model: Instance of CostModel, configured for the solar technology.
            solar_tech_name: Name of the solar technology to use for LCOE calculation.
            solar_project_year: Year for solar project evaluation.
            solar_project_capacity_factor: Capacity factor for the solar project.
            solar_project_discount_rate: Discount rate for the solar project LCOE calculation.
            solar_project_lifetime_years: Economic lifetime for the solar project.
            electrolyzer_capex_usd_per_kw: Capital expenditure for electrolyzer ($/kW of input electricity capacity).
            electrolyzer_efficiency_kwh_per_kg_h2: Specific energy consumption (kWh_DC/kg_H2).
            electrolyzer_capacity_factor: Annual average utilization of the electrolyzer.
            electrolyzer_discount_rate: Discount rate for electrolyzer capital recovery factor.
            electrolyzer_lifetime_years: Economic lifetime of the electrolyzer system.
            stack_lifetime_hours: Operational lifetime of the electrolyzer stack before replacement.
            stack_replacement_cost_pct_capex: Cost of stack replacement as a percentage of initial CAPEX.
            fixed_om_cost_pct_capex: Fixed annual O&M costs as a percentage of initial CAPEX.
            variable_om_cost_usd_per_mwh: Variable O&M costs per MWh of electricity consumed by electrolyzer.
        """

        # 0. Calculate Solar LCOE for electricity input
        solar_lcoe_results = solar_cost_model.calculate_lcoe_for_evolving_solar_tech(
            solar_tech_model=solar_tech_model,
            technology_name=solar_tech_name,
            year=solar_project_year,
            capacity_factor=solar_project_capacity_factor,
            discount_rate=solar_project_discount_rate,
            economic_lifetime_years=solar_project_lifetime_years
        )

        if solar_lcoe_results.get('error') or solar_lcoe_results['lcoe_usd_per_mwh'] == float('inf'):
            error_msg = solar_lcoe_results.get('error', 'Solar LCOE is infinite.')
            print(f"Error in LCOH calculation: Could not determine valid Solar LCOE. Reason: {error_msg}")
            return float('inf')
        
        solar_lcoe_usd_per_mwh = solar_lcoe_results['lcoe_usd_per_mwh']
        print(f"  Internal Solar LCOE calculated: ${solar_lcoe_usd_per_mwh:.2f}/MWh for {solar_tech_name} in {solar_project_year}")

        # 1. Calculate Capital Recovery Factor (CRF) for Electrolyzer
        if electrolyzer_discount_rate > 0:
            crf = (electrolyzer_discount_rate * (1 + electrolyzer_discount_rate) ** electrolyzer_lifetime_years) / \
                  ((1 + electrolyzer_discount_rate) ** electrolyzer_lifetime_years - 1)
        elif electrolyzer_lifetime_years > 0:
            crf = 1 / electrolyzer_lifetime_years
        else:
            print("Warning: Electrolyzer lifetime is zero and discount rate is zero. Cannot calculate CRF.")
            return float('inf')

        # 2. Annualized CAPEX for Electrolyzer
        annualized_capex_usd_per_kw_year = electrolyzer_capex_usd_per_kw * crf

        # 3. Annual Hydrogen Production per kW of electrolyzer capacity
        annual_operating_hours = 8760 * electrolyzer_capacity_factor
        annual_electricity_consumed_kwh_per_kw_year = 1 * annual_operating_hours # 1 kW capacity * hours
        annual_h2_production_kg_per_kw_year = annual_electricity_consumed_kwh_per_kw_year / electrolyzer_efficiency_kwh_per_kg_h2

        if annual_h2_production_kg_per_kw_year == 0:
            print("Warning: Annual H2 production is zero. Check capacity factor or efficiency.")
            return float('inf')

        # 4. Stack Replacement Costs
        # Number of stack replacements over the electrolyzer lifetime
        num_stack_replacements = math.floor((annual_operating_hours * electrolyzer_lifetime_years) / stack_lifetime_hours) 
        if (annual_operating_hours * electrolyzer_lifetime_years) % stack_lifetime_hours == 0 and num_stack_replacements > 0:
             num_stack_replacements -=1 # If it aligns perfectly with EOL, no final replacement needed for *this* LCOH period

        total_stack_replacement_cost_present_value = 0
        if num_stack_replacements > 0:
            cost_per_replacement = electrolyzer_capex_usd_per_kw * stack_replacement_cost_pct_capex
            for i in range(1, int(num_stack_replacements) + 1):
                replacement_year = (i * stack_lifetime_hours) / annual_operating_hours
                if replacement_year < electrolyzer_lifetime_years: # only consider if within project lifetime
                    total_stack_replacement_cost_present_value += cost_per_replacement / ((1 + electrolyzer_discount_rate) ** replacement_year)
        
        annualized_stack_replacement_cost_usd_per_kw_year = total_stack_replacement_cost_present_value * crf 
        # This is an approximation; ideally, each replacement NPV is annualized over remaining life or specific period.
        # Simpler: average it over the project lifetime (less accurate if replacements are not uniform)
        # annualized_stack_replacement_cost_usd_per_kw_year = (num_stack_replacements * cost_per_replacement_not_npv) / electrolyzer_lifetime_years
        # For now, using the CRF applied to NPV sum as a proxy

        # 5. Fixed O&M Costs
        fixed_om_usd_per_kw_year = electrolyzer_capex_usd_per_kw * fixed_om_cost_pct_capex

        # 6. Variable O&M Costs
        # VOM per MWh, electricity cost is separate
        variable_om_usd_per_kw_year = (annual_electricity_consumed_kwh_per_kw_year / 1000) * variable_om_cost_usd_per_mwh

        # 7. Electricity Costs
        electricity_cost_usd_per_kw_year = (annual_electricity_consumed_kwh_per_kw_year / 1000) * solar_lcoe_usd_per_mwh

        # 8. Total Annualized Costs per kW
        total_annual_cost_usd_per_kw_year = (
            annualized_capex_usd_per_kw_year +
            annualized_stack_replacement_cost_usd_per_kw_year +
            fixed_om_usd_per_kw_year +
            variable_om_usd_per_kw_year +
            electricity_cost_usd_per_kw_year
        )

        # 9. Levelized Cost of Hydrogen ($/kg)
        lcoh_usd_per_kg = total_annual_cost_usd_per_kw_year / annual_h2_production_kg_per_kw_year
        
        print(f"Detailed LCOH Calculation Inputs:")
        print(f"  Solar LCOE (used): ${solar_lcoe_usd_per_mwh:.2f}/MWh, Electrolyzer CAPEX: ${electrolyzer_capex_usd_per_kw}/kW")
        print(f"  Electrolyzer Efficiency: {electrolyzer_efficiency_kwh_per_kg_h2} kWh/kg, Electrolyzer CF: {electrolyzer_capacity_factor*100:.0f}% H2")
        print(f"  Electrolyzer Discount Rate: {electrolyzer_discount_rate*100:.0f}%, Electrolyzer Lifetime: {electrolyzer_lifetime_years} years")
        print(f"Calculated LCOH: ${lcoh_usd_per_kg:.2f}/kg H2")
        return lcoh_usd_per_kg

    def assess_solar_for_industrial_heat(self, industry_type: str, temperature_requirement_c: int) -> str:
        """Assesses suitability of solar thermal for industrial heat applications."""
        suitability = "Low"
        if temperature_requirement_c < 150:
            suitability = "High (e.g., using flat plate collectors, evacuated tubes)"
        elif temperature_requirement_c < 400:
            suitability = "Medium (e.g., using concentrating solar power - parabolic troughs)"
        else:
            suitability = "Challenging (may require advanced CSP or hybridization)"
        
        print(f"Suitability of solar for {industry_type} (Temp: {temperature_requirement_c}°C): {suitability}")
        return suitability

if __name__ == '__main__':
    # Runtime imports for example usage
    from ..technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology
    from ..economic_framework.cost_model import CostModel

    # Example Usage
    industry_data_example = {'Cement_Global': {'decarbonization_pathway': 'CCS, H2-firing, alternative binders'}}
    model = IndustrialDecarbonizationModel(industry_data=industry_data_example)

    # Setup for SolarTechModel and CostModel
    stm = SolarTechModel()
    example_solar_tech = SolarTechnology(
        name='UtilityPV_AdvancedSi',
        base_efficiency=0.22,
        projected_efficiency_2035=0.28,
        start_year=2020,
        commercial_scale_year=2018,
        base_capex_usd_per_kw=900,
        annual_capex_reduction_rate=0.025
    )
    stm.add_technology(example_solar_tech)

    cost_settings_solar = {
        'module_usd_per_kw': 500, # Example breakdown
        'bos_usd_per_kw': 250,
        'inverter_usd_per_kw': 100,
        'installation_usd_per_kw': 50,
        'opex_per_kw_year': 15 # Annual OPEX for solar farm
    }
    solar_cm = CostModel(
        technology_name='UtilityPV_AdvancedSi',
        initial_costs=cost_settings_solar,
        learning_rate=0.0 # Assuming CAPEX evolution handled by SolarTechModel's annual_capex_reduction_rate
    )
    
    print("\n--- LCOH Calculation Example 1 ---")
    model.estimate_green_hydrogen_production_cost(
        solar_tech_model=stm,
        solar_cost_model=solar_cm,
        solar_tech_name='UtilityPV_AdvancedSi',
        solar_project_year=2025,
        solar_project_capacity_factor=0.25, # E.g. for a good solar location
        solar_project_discount_rate=0.05,
        solar_project_lifetime_years=25,
        electrolyzer_capex_usd_per_kw=600,  
        electrolyzer_efficiency_kwh_per_kg_h2=50.0, 
        electrolyzer_capacity_factor=0.70,               
        electrolyzer_discount_rate=0.07,                 
        electrolyzer_lifetime_years=20,    
        stack_lifetime_hours=80000,         
        stack_replacement_cost_pct_capex=0.35, 
        fixed_om_cost_pct_capex=0.015,      
        variable_om_cost_usd_per_mwh=0.5    
    )

    print("\n--- LCOH Calculation Example 2 (Improved conditions) ---")
    model.estimate_green_hydrogen_production_cost(
        solar_tech_model=stm,
        solar_cost_model=solar_cm,
        solar_tech_name='UtilityPV_AdvancedSi',
        solar_project_year=2030, # Later year, better solar tech
        solar_project_capacity_factor=0.28, 
        solar_project_discount_rate=0.045,
        solar_project_lifetime_years=30,
        electrolyzer_capex_usd_per_kw=450,  
        electrolyzer_efficiency_kwh_per_kg_h2=48.0, 
        electrolyzer_capacity_factor=0.80,               
        electrolyzer_discount_rate=0.06,
        electrolyzer_lifetime_years=25,
        stack_lifetime_hours=90000,
        stack_replacement_cost_pct_capex=0.30,
        fixed_om_cost_pct_capex=0.01,
        variable_om_cost_usd_per_mwh=0.3
    )

    model.assess_solar_for_industrial_heat(industry_type="FoodProcessing", temperature_requirement_c=120)
    model.assess_solar_for_industrial_heat(industry_type="Chemicals", temperature_requirement_c=350)
