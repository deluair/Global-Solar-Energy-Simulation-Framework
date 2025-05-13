"""
Module for evaluating the economic viability and attractiveness of solar energy projects.

This module will integrate with CostModel, SolarTechModel, and MarketSimulator to make informed
investment decisions based on LCOE, market conditions, policy incentives, and risk factors.
"""

from typing import TYPE_CHECKING, Dict, Any, Optional, List
import logging

if TYPE_CHECKING:
    from src.modules.technological_evolution.solar_tech_model import SolarTechModel
    from src.modules.economic_framework.cost_model import CostModel
    from src.modules.economic_framework.market_model import MarketSimulator
    from src.modules.economic_framework.carbon_pricing_model import CarbonPricingMechanism
    from src.modules.supply_chain_model import SupplyChainModel

logger = logging.getLogger(__name__)

# Placeholder: Tons of CO2 emissions avoided per MWh of solar generation
# This can be made more sophisticated later (e.g., region-specific grid intensity)
TONS_CO2_AVOIDED_PER_MWH = 0.5

class InvestmentDecisionModel:
    """Evaluates the economic attractiveness of solar energy projects.

    This model integrates data from technological, cost, and market models
    to provide a comprehensive financial assessment. It calculates metrics
    such as LCOE, NPV, simple payback period, and an overall attractiveness
    score, considering dynamic market prices and ancillary service revenues.
    """
    def __init__(self, solar_tech_model: 'SolarTechModel', cost_model: 'CostModel', market_simulator: 'MarketSimulator', carbon_pricing_model: 'CarbonPricingMechanism'):
        """Initializes the InvestmentDecisionModel with necessary component models.

        Args:
            solar_tech_model (SolarTechModel): An instance of SolarTechModel, used to
                retrieve technology-specific parameters like efficiency and CAPEX evolution.
            cost_model (CostModel): An instance of CostModel, used for calculating
                the Levelized Cost of Electricity (LCOE).
            market_simulator (MarketSimulator): An instance of MarketSimulator, used to
                fetch regional energy prices (considering time-of-day) and estimate
                potential revenues from ancillary services.
            carbon_pricing_model (CarbonPricingMechanism): An instance for accessing carbon prices.
        """
        self.solar_tech_model = solar_tech_model
        self.cost_model = cost_model
        self.market_simulator = market_simulator
        self.carbon_pricing_model = carbon_pricing_model
        print("InvestmentDecisionModel initialized.")

    def decide_investments(self, 
                             year: int, 
                             regions: List[str], 
                             technologies: List[str],
                             # Type hints for models can be more specific if they are stable
                             cost_model: Any, # CostModel instance
                             market_model: Any, # MarketSimulator instance
                             solar_tech_model: Any, # SolarTechModel instance
                             grid_model: Any, # GridModel instance
                             policy_model: Any, # PolicyModel instance
                             supply_chain_model: Any # SupplyChainModel instance
                            ) -> Dict[str, Dict[str, float]]:
        """Makes investment decisions for the given year, regions, and technologies.

        This method iterates through specified regions and technologies, evaluates
        a standard project for each, and decides on investments based on attractiveness.

        Args:
            year (int): The current simulation year.
            regions (List[str]): A list of regions to consider for investment.
            technologies (List[str]): A list of technologies to consider.
            cost_model: Instance of CostModel.
            market_model: Instance of MarketSimulator.
            solar_tech_model: Instance of SolarTechModel.
            grid_model: Instance of GridModel.
            policy_model: Instance of PolicyModel.
            supply_chain_model: Instance of SupplyChainModel.

        Returns:
            Dict[str, Dict[str, float]]: A dictionary where keys are region names,
                                         and values are dictionaries with technology names
                                         as keys and invested capacity (e.g., MW) as values.
                                         Example: {'USA': {'TOPCon_PV': 100.0, 'LFP_Battery': 50.0}}
        """
        logger.info(f"InvestmentDecisionModel.decide_investments called for year {year}, regions: {regions}, technologies: {technologies}. Evaluating potential investments.")
        
        investments_made: Dict[str, Dict[str, float]] = {}

        # Default parameters for project evaluation - these can be made more dynamic later
        default_project_capacity_mw = 50.0
        default_capacity_factor = 0.20 # General assumption, could be tech/region specific
        default_discount_rate = 0.05
        default_economic_lifetime_years = 25
        default_time_of_day = 'mid_peak' # For revenue calculation
        # Note: ancillary_service_types and region_carbon_scheme_name will use defaults
        # in evaluate_project_attractiveness if not specified, or we can pass None.

        for region_name in regions:
            investments_made[region_name] = {}
            for tech_name in technologies:
                try:
                    logger.debug(f"Evaluating investment in {tech_name} for {region_name} in year {year}.")
                    
                    # Ensure the technology exists in the solar_tech_model for cost/efficiency data
                    tech_details = self.solar_tech_model.get_technology_details(tech_name, year)
                    if 'error' in tech_details:
                        logger.warning(f"Could not retrieve details for technology {tech_name} in SolarTechModel for year {year}: {tech_details['error']}. Skipping evaluation for {region_name}.")
                        continue
                    # Optional: Further check if tech is commercially available for investment decision
                    # if not tech_details.get('is_commercially_available', False):
                    #     logger.info(f"Technology {tech_name} is not commercially available in year {year}. Skipping investment evaluation for {region_name}.")
                    #     continue

                    # The cost_model passed to decide_investments might need to be updated for the specific tech/year
                    # if it's a single instance. evaluate_project_attractiveness uses self.cost_model.
                    # For now, assume self.cost_model is appropriately managed or general enough.
                    # A more robust approach might involve getting tech-specific costs from the 'cost_model' argument.

                    project_metrics = self.evaluate_project_attractiveness(
                        technology_name=tech_name,
                        year=year,
                        project_capacity_mw=default_project_capacity_mw,
                        capacity_factor=default_capacity_factor,
                        discount_rate=default_discount_rate,
                        economic_lifetime_years=default_economic_lifetime_years,
                        region=region_name, # Critical: use the current region from the loop
                        time_of_day=default_time_of_day
                        # ancillary_service_types: Optional[List[str]] = None, (use default)
                        # region_carbon_scheme_name: Optional[str] = None (use default)
                    )

                    if project_metrics.get('error'):
                        logger.error(f"Error evaluating {tech_name} in {region_name}: {project_metrics['error']}")
                        continue

                    # Decision criteria: e.g., positive NPV or attractiveness_score
                    # Using npv_usd as a primary financial metric for investment decision
                    npv = project_metrics.get('npv_usd', 0)
                    attractiveness_score = project_metrics.get('attractiveness_score', 0)

                    # For this example, let's say we invest if NPV is positive.
                    # A more complex model might consider budget constraints, build limits, policy targets, etc.
                    if npv > 0:
                        logger.info(f"INVEST: Attractive project {tech_name} in {region_name} (Year {year}). NPV: {npv:.2f}. Investing {default_project_capacity_mw} MW.")
                        investments_made[region_name][tech_name] = investments_made[region_name].get(tech_name, 0) + default_project_capacity_mw
                    else:
                        logger.info(f"NO INVEST: Project {tech_name} in {region_name} (Year {year}) not attractive. NPV: {npv:.2f}, Score: {attractiveness_score:.2f}.")

                except Exception as e:
                    logger.error(f"Unexpected error during investment evaluation for {tech_name} in {region_name}, year {year}: {e}", exc_info=True)

        return investments_made

    def _calculate_npv(self, initial_investment: float, annual_cash_flows: List[float], discount_rate: float) -> float:
        """Calculates the Net Present Value (NPV) of a series of cash flows.

        Args:
            initial_investment (float): The initial capital expenditure for the project.
            annual_cash_flows (List[float]): A list of net cash flows expected each year
                over the project's economic lifetime.
            discount_rate (float): The annual discount rate used to bring future cash
                flows to their present value (e.g., 0.05 for 5%).

        Returns:
            float: The calculated Net Present Value in USD.
        """
        # NPV = sum(Net Cash Flow_t / (1 + r)^t) - Initial Investment
        # Assuming constant annual_net_cash_flow_usd for simplicity
        current_npv = -initial_investment
        for t in range(1, len(annual_cash_flows) + 1):
            current_npv += annual_cash_flows[t-1] / ((1 + discount_rate) ** t)
        return current_npv

    def evaluate_project_attractiveness(
        self, 
        technology_name: str, 
        year: int, 
        project_capacity_mw: float, 
        capacity_factor: float, 
        discount_rate: float, 
        economic_lifetime_years: int,
        region: str, 
        time_of_day: str = 'mid_peak', 
        ancillary_service_types: Optional[List[str]] = None,
        region_carbon_scheme_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates the financial attractiveness of a solar project.

        This comprehensive evaluation considers technology-specific costs (LCOE),
        market-driven revenues (energy sales and ancillary services), and key
        financial metrics like Net Present Value (NPV) and Simple Payback Period.
        It leverages the `MarketSimulator` to incorporate regional market dynamics.

        Args:
            technology_name (str): The specific solar technology being evaluated (e.g., 'AdvancedSiliconPV').
            year (int): The year for which the evaluation is being performed.
            project_capacity_mw (float): The nominal power capacity of the project in megawatts (MW).
            capacity_factor (float): The actual energy output as a fraction of the nominal capacity
                (e.g., 0.20 for 20%).
            discount_rate (float): The annual rate used for discounting future cash flows in NPV
                calculations (e.g., 0.05 for 5%).
            economic_lifetime_years (int): The operational lifetime of the project in years, over
                which revenues and costs are considered.
            region (str): The geographical or market region where the project is located.
                This determines energy prices and ancillary service opportunities via the MarketSimulator.
            time_of_day (str, optional): Specifies the time period for which the energy price should
                be fetched (e.g., 'off_peak', 'mid_peak', 'on_peak'). Defaults to 'mid_peak'.
                Relevant for markets with time-of-use (TOU) pricing.
            ancillary_service_types (Optional[List[str]], optional): A list of specific ancillary
                services the project might provide (e.g., ['frequency_response', 'voltage_support']).
                Defaults to None, indicating no ancillary service revenues are considered.
            region_carbon_scheme_name (Optional[str], optional): The name of the carbon pricing
                scheme applicable in the project's region. Defaults to None (no carbon price impact).

        Returns:
            Dict[str, Any]: A dictionary containing a detailed breakdown of the evaluation results,
                including:
                - 'technology_name': The evaluated technology.
                - 'year': The evaluation year.
                - 'project_capacity_mw': The project's capacity.
                - 'region_evaluated': The specific region used for market data.
                - 'time_of_day_evaluated': The time of day used for energy pricing.
                - 'ancillary_service_types_evaluated': List of ancillary services considered.
                - 'region_carbon_scheme_name_used': Carbon pricing scheme name used.
                - 'lcoe_data' (dict): Detailed LCOE calculation results from CostModel.
                - 'market_price_from_simulator_usd_per_mwh': Energy price from MarketSimulator.
                - 'profit_margin_usd_per_mwh': Profit margin from energy sales.
                - 'projected_annual_profit_usd': Total annual profit from energy sales.
                - 'total_ancillary_revenue_usd_per_year': Total annual revenue from ancillary services.
                - 'carbon_credit_revenue_usd_per_year' (float): Revenue from carbon credits due to avoided emissions.
                - 'initial_investment_usd': Calculated initial investment.
                - 'annual_net_cash_flow_usd': Net annual cash flow (energy profit + ancillary revenue + carbon credit revenue).
                - 'simple_payback_period_years': Payback period in years, or 'N/A' if not applicable.
                - 'npv_usd': Net Present Value of the project.
                - 'attractiveness_score': A score based on the profit margin per MWh.
                - 'error' (str, optional): Description of any error encountered during evaluation.
        """
        print(f"\nEvaluating project: {technology_name} for year {year} in {region} ({project_capacity_mw:.1f} MW capacity, {time_of_day} price)")
        results = {
            'technology_name': technology_name,
            'year': year,
            'project_capacity_mw': project_capacity_mw,
            'region_evaluated': region,
            'time_of_day_evaluated': time_of_day,
            'ancillary_service_types_evaluated': ancillary_service_types if ancillary_service_types else [],
            'region_carbon_scheme_name_used': region_carbon_scheme_name
        }

        try:
            lcoe_data = self.cost_model.calculate_lcoe_for_evolving_solar_tech(
                solar_tech_model=self.solar_tech_model, 
                technology_name=technology_name, 
                year=year, 
                capacity_factor=capacity_factor, 
                discount_rate=discount_rate, 
                economic_lifetime_years=economic_lifetime_years
            )
            results['lcoe_data'] = lcoe_data
            if lcoe_data.get('error'):
                results['error'] = lcoe_data['error']
                print(f"  Error in LCOE calculation: {lcoe_data['error']}")
                return results
            
            effective_lcoe_usd_per_mwh = lcoe_data['lcoe_usd_per_mwh']
            print(f"  LCOE (effective): ${effective_lcoe_usd_per_mwh:.2f}/MWh")

            # Get market price from MarketSimulator
            market_price_from_simulator_usd_per_mwh = self.market_simulator.get_energy_price(
                region=region, 
                time_of_day=time_of_day,
                default_base_price=50 
            )
            results['market_price_from_simulator_usd_per_mwh'] = market_price_from_simulator_usd_per_mwh
            print(f"  Market Price ({time_of_day} in {region}): ${market_price_from_simulator_usd_per_mwh:.2f}/MWh")

            # Calculate profit margin (no direct policy incentives here anymore)
            profit_margin_usd_per_mwh = market_price_from_simulator_usd_per_mwh - effective_lcoe_usd_per_mwh
            results['profit_margin_usd_per_mwh'] = profit_margin_usd_per_mwh
            print(f"  Profit Margin: ${profit_margin_usd_per_mwh:.2f}/MWh")

            # Calculate annual generation and profit
            annual_generation_mwh = project_capacity_mw * capacity_factor * 8760 
            projected_annual_profit_usd = profit_margin_usd_per_mwh * annual_generation_mwh
            results['projected_annual_profit_usd'] = projected_annual_profit_usd

            # Estimate ancillary service revenue
            total_ancillary_revenue_usd_per_year = 0.0
            if ancillary_service_types and project_capacity_mw > 0:
                for service_type in ancillary_service_types:
                    revenue = self.market_simulator.estimate_ancillary_revenue(
                        capacity_mw=project_capacity_mw,
                        service_type=service_type,
                        region=region
                    )
                    total_ancillary_revenue_usd_per_year += revenue
            results['total_ancillary_revenue_usd_per_year'] = total_ancillary_revenue_usd_per_year
            if total_ancillary_revenue_usd_per_year > 0:
                print(f"  Total Ancillary Revenue: ${total_ancillary_revenue_usd_per_year:.2f}/year")

            # Calculate Carbon Credit Revenue
            carbon_credit_revenue_usd_per_year = 0.0
            if region_carbon_scheme_name and project_capacity_mw > 0 and capacity_factor > 0:
                annual_co2_emissions_avoided_tons = annual_generation_mwh * TONS_CO2_AVOIDED_PER_MWH # Use module-level constant
                # Pass negative emissions to get_carbon_cost to signify avoided emissions, then negate result for revenue
                value_of_avoided_emissions = self.carbon_pricing_model.get_carbon_cost(
                    emissions_tons_co2=annual_co2_emissions_avoided_tons, # Positive value for avoided tons
                    region_scheme_name=region_carbon_scheme_name
                )
                # If carbon price implies cost for emissions, avoided emissions are a benefit
                carbon_credit_revenue_usd_per_year = value_of_avoided_emissions 
                print(f"  Carbon Credit Revenue ({region_carbon_scheme_name}): ${carbon_credit_revenue_usd_per_year:.2f}/year for {annual_co2_emissions_avoided_tons:.2f} tons CO2 avoided")
            results['carbon_credit_revenue_usd_per_year'] = carbon_credit_revenue_usd_per_year

            # Financial Metrics Calculation
            initial_investment_usd = lcoe_data['capex_usd_per_kw'] * project_capacity_mw * 1000 
            results['initial_investment_usd'] = initial_investment_usd
            print(f"  Initial Investment: ${initial_investment_usd:,.1f}")

            # Annual Net Cash Flow = Annual Profit from Energy Sales + Ancillary Revenue + Carbon Credit Revenue
            annual_net_cash_flow_usd = projected_annual_profit_usd + total_ancillary_revenue_usd_per_year + carbon_credit_revenue_usd_per_year
            results['annual_net_cash_flow_usd'] = annual_net_cash_flow_usd
            print(f"  Annual Net Cash Flow: ${annual_net_cash_flow_usd:,.1f}")

            # Simple Payback Period
            if project_capacity_mw == 0 and initial_investment_usd == 0:
                simple_payback_period_years = 0.0 
            elif initial_investment_usd == 0:
                simple_payback_period_years = 'N/A (initial investment is zero)'
            elif annual_net_cash_flow_usd <= 0:
                simple_payback_period_years = 'N/A (negative or zero cash flow)'
            else:
                simple_payback_period_years = initial_investment_usd / annual_net_cash_flow_usd
            results['simple_payback_period_years'] = simple_payback_period_years
            if isinstance(simple_payback_period_years, float):
                print(f"  Simple Payback Period: {simple_payback_period_years:.2f} years")
            else:
                print(f"  Simple Payback Period: {simple_payback_period_years}")

            # Net Present Value (NPV)
            if economic_lifetime_years > 0:
                cash_flows_for_npv = [annual_net_cash_flow_usd] * economic_lifetime_years
                npv_usd = self._calculate_npv(initial_investment_usd, cash_flows_for_npv, discount_rate)
            elif initial_investment_usd == 0 and annual_net_cash_flow_usd == 0 : 
                npv_usd = 0.0
            else: 
                npv_usd = -initial_investment_usd
            results['npv_usd'] = npv_usd
            print(f"  NPV @ {discount_rate*100:.1f}%: ${npv_usd:,.2f}")

            # Attractiveness Score (can be based on profit margin, NPV, or a composite score)
            attractiveness_score = profit_margin_usd_per_mwh 
            results['attractiveness_score'] = attractiveness_score
            print(f"  Attractiveness Score: {attractiveness_score:.2f}")

        except Exception as e:
            logger.error(f"Error evaluating project {technology_name} in {year}: {e}", exc_info=True)
            results['error'] = str(e)
            print(f"  Unexpected error during evaluation: {e}")
        
        return results

if __name__ == '__main__':
    import sys
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if project_root_dir not in sys.path:
        sys.path.insert(0, project_root_dir)

    from src.modules.technological_evolution.solar_tech_model import SolarTechModel, SolarTechnology
    from src.modules.economic_framework.cost_model import CostModel
    from src.modules.economic_framework.market_model import MarketSimulator
    from src.modules.economic_framework.carbon_pricing_model import CarbonPricingMechanism

    print("--- InvestmentDecisionModel Example --- ")
    stm = SolarTechModel()
    tech1 = SolarTechnology(
        name='AdvancedSiliconPV',
        base_efficiency=0.22, projected_efficiency_2035=0.26, start_year=2023,
        commercial_scale_year=2020, base_capex_usd_per_kw=900, annual_capex_reduction_rate=0.03
    )
    tech2 = SolarTechnology(
        name='EmergingPerovskite',
        base_efficiency=0.25, projected_efficiency_2035=0.32, start_year=2025,
        commercial_scale_year=2027, base_capex_usd_per_kw=750, annual_capex_reduction_rate=0.05
    )
    stm.add_technology(tech1)
    stm.add_technology(tech2)

    cost_settings_tech1 = {'opex_per_kw_year': 18, 'module_usd_per_kw':0, 'bos_usd_per_kw':0, 'inverter_usd_per_kw':0, 'installation_usd_per_kw':0}
    cost_model_tech1 = CostModel(technology_name='AdvancedSiliconPV', initial_costs=cost_settings_tech1, learning_rate=0)
    
    cost_settings_tech2 = {'opex_per_kw_year': 22, 'module_usd_per_kw':0, 'bos_usd_per_kw':0, 'inverter_usd_per_kw':0, 'installation_usd_per_kw':0}
    cost_model_tech2 = CostModel(technology_name='EmergingPerovskite', initial_costs=cost_settings_tech2, learning_rate=0)

    market_simulator = MarketSimulator()

    carbon_pricing_mechanism = CarbonPricingMechanism(schemes={
        'EU_ETS_High': {'type': 'cap_and_trade', 'price_per_ton_co2': 100},
        'NoCarbonPrice': {'type': 'none', 'price_per_ton_co2': 0}
    })

    investment_model_tech1 = InvestmentDecisionModel(solar_tech_model=stm, cost_model=cost_model_tech1, market_simulator=market_simulator, carbon_pricing_model=carbon_pricing_mechanism)
    project1_results = investment_model_tech1.evaluate_project_attractiveness(
        technology_name='AdvancedSiliconPV',
        year=2025,
        project_capacity_mw=50.0,
        capacity_factor=0.20,
        discount_rate=0.06,
        economic_lifetime_years=25,
        region='California',
        time_of_day='peak',
        ancillary_service_types=['frequency_response'],
        region_carbon_scheme_name='EU_ETS_High'
    )

    investment_model_tech2 = InvestmentDecisionModel(solar_tech_model=stm, cost_model=cost_model_tech2, market_simulator=market_simulator, carbon_pricing_model=carbon_pricing_mechanism)
    project2_results = investment_model_tech2.evaluate_project_attractiveness(
        technology_name='EmergingPerovskite',
        year=2028,
        project_capacity_mw=50.0,
        capacity_factor=0.22,
        discount_rate=0.07,
        economic_lifetime_years=20,
        region='Texas',
        time_of_day='off_peak',
        ancillary_service_types=['voltage_support'],
        region_carbon_scheme_name='NoCarbonPrice'
    )

    def print_results(results):
        print("Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")

    print_results(project1_results)
    print_results(project2_results)
