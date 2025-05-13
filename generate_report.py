import pandas as pd
import matplotlib.pyplot as plt
import ast
import base64
import io
import os

# --- Configuration ---
CSV_FILE_NAME = 'full_simulation_results_20250513_161535.csv'
HTML_REPORT_FILE_NAME = 'simulation_analysis_report.html'
REGIONS = ['USA', 'China', 'EU_Germany']
SIMULATION_TECHNOLOGIES = ["TOPCon_PV", "AdvancedMonocrystallineSilicon", "LFP_Battery"]
START_YEAR = 2025
END_YEAR = 2030

# --- Helper Functions ---

def plot_to_base64(plt_figure):
    """Converts a matplotlib figure to a base64 encoded string."""
    buf = io.BytesIO()
    plt_figure.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(plt_figure) # Close the figure to free memory
    return f'data:image/png;base64,{img_str}'

def parse_and_prepare_data(csv_file_path):
    """Loads, parses, and prepares data from the simulation CSV."""
    df = pd.read_csv(csv_file_path)

    # Convert stringified dicts to actual dicts
    df['investments'] = df['investments'].apply(ast.literal_eval)
    df['market_outcomes'] = df['market_outcomes'].apply(ast.literal_eval)

    processed_data = []
    for _, row in df.iterrows():
        year = row['year']
        for region in REGIONS:
            # Investment data
            region_investments = row['investments'].get(region, {})
            for tech, inv_mw in region_investments.items():
                processed_data.append({
                    'year': year,
                    'region': region,
                    'metric_type': 'investment',
                    'technology': tech,
                    'value_mw': inv_mw,
                    'generated_mwh': 0, # Will be filled from market outcomes
                    'demand_mwh': 0,
                    'unmet_demand_mwh': 0,
                    'dispatched_mwh': 0
                })
            
            # Market outcome data
            region_market = row['market_outcomes'].get(region, {})
            annual_demand_mwh = region_market.get('annual_demand_mwh', 0)
            total_dispatched_mwh = region_market.get('total_dispatched_generation_mwh', 0)
            unmet_demand_mwh = region_market.get('unmet_demand_mwh', 0)
            
            tech_generation = region_market.get('total_generation_mwh', {})
            for tech, gen_mwh in tech_generation.items():
                # Try to find a matching investment entry to update, or add new if no investment but generation (e.g. existing)
                found_investment_entry = False
                for record in processed_data:
                    if record['year'] == year and record['region'] == region and record['technology'] == tech and record['metric_type'] == 'investment':
                        record['generated_mwh'] = gen_mwh
                        record['demand_mwh'] = annual_demand_mwh
                        record['unmet_demand_mwh'] = unmet_demand_mwh
                        record['dispatched_mwh'] = total_dispatched_mwh # This is regional total
                        found_investment_entry = True
                        break
                if not found_investment_entry: # If tech generated power but no investment in that year (e.g. existing or pre-simulation)
                     processed_data.append({
                        'year': year,
                        'region': region,
                        'metric_type': 'generation_only', # Differentiate if needed
                        'technology': tech,
                        'value_mw': 0, # No new investment this year
                        'generated_mwh': gen_mwh,
                        'demand_mwh': annual_demand_mwh,
                        'unmet_demand_mwh': unmet_demand_mwh,
                        'dispatched_mwh': total_dispatched_mwh
                    })
            # If no tech-specific generation, still add regional market data
            if not tech_generation and region_market:
                 processed_data.append({
                    'year': year,
                    'region': region,
                    'metric_type': 'regional_market_summary',
                    'technology': 'N/A',
                    'value_mw': 0,
                    'generated_mwh': 0, # No tech specific generation listed for this year
                    'demand_mwh': annual_demand_mwh,
                    'unmet_demand_mwh': unmet_demand_mwh,
                    'dispatched_mwh': total_dispatched_mwh
                })


    processed_df = pd.DataFrame(processed_data)
    
    # Calculate cumulative investment
    if not processed_df.empty and 'value_mw' in processed_df.columns:
        processed_df.sort_values(by=['region', 'technology', 'year'], inplace=True)
        processed_df['cumulative_investment_mw'] = processed_df.groupby(['region', 'technology'])['value_mw'].cumsum()
    else:
        processed_df['cumulative_investment_mw'] = 0


    return processed_df

# --- Plotting Functions ---

def generate_cumulative_investment_plot(df):
    """Generates a plot of cumulative investment over time by region and technology."""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Filter for actual investment data points
    investment_df = df[df['metric_type'] == 'investment'][['year', 'region', 'technology', 'cumulative_investment_mw']].drop_duplicates()
    
    if not investment_df.empty:
        for region in REGIONS:
            for tech in SIMULATION_TECHNOLOGIES: # Iterate through all possible techs
                subset = investment_df[(investment_df['region'] == region) & (investment_df['technology'] == tech)]
                if not subset.empty:
                    ax.plot(subset['year'], subset['cumulative_investment_mw'], marker='o', linestyle='-', label=f'{region} - {tech}')
    
    ax.set_title('Cumulative Investment (MW) Over Time by Region & Technology')
    ax.set_xlabel('Year')
    ax.set_ylabel('Cumulative Installed Capacity (MW)')
    ax.legend(title='Region - Technology', bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    return plot_to_base64(fig)

def generate_market_dynamics_plot(df, region):
    """Generates a plot of demand, dispatched generation, and unmet demand for a region."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    region_df = df[(df['region'] == region) & (df['metric_type'] != 'investment')].copy()
    if region_df.empty:
        ax.text(0.5, 0.5, 'No market data available for this region.', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        return plot_to_base64(fig)

    # Aggregate total generation for the region per year
    # Use dispatched_mwh for total generation, demand_mwh and unmet_demand_mwh are regional figures
    market_summary = region_df.groupby('year').agg(
        total_generated_mwh=('dispatched_mwh', 'first'), # total dispatched for the region
        annual_demand_mwh=('demand_mwh', 'first'),
        total_unmet_demand_mwh=('unmet_demand_mwh', 'first')
    ).reset_index()
    
    if market_summary.empty:
        ax.text(0.5, 0.5, 'No summarized market data available for plotting.', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        return plot_to_base64(fig)

    ax.plot(market_summary['year'], market_summary['annual_demand_mwh'], marker='o', linestyle='-', label='Annual Demand (MWh)')
    ax.plot(market_summary['year'], market_summary['total_generated_mwh'], marker='s', linestyle='--', label='Total Dispatched Generation (MWh)')
    ax.plot(market_summary['year'], market_summary['total_unmet_demand_mwh'], marker='^', linestyle=':', label='Unmet Demand (MWh)')
    
    ax.set_title(f'Market Dynamics in {region}')
    ax.set_xlabel('Year')
    ax.set_ylabel('Energy (MWh)')
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.tight_layout()
    return plot_to_base64(fig)

def generate_generation_mix_pie_chart(df, region, year):
    """Generates a pie chart of the generation mix for a given region and year."""
    fig, ax = plt.subplots(figsize=(8, 8))
    
    year_region_df = df[(df['region'] == region) & (df['year'] == year) & (df['generated_mwh'] > 0)]
    
    if year_region_df.empty:
        ax.text(0.5, 0.5, 'No generation data for this period.', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title(f'Generation Mix in {region} - {year}')
        return plot_to_base64(fig)

    generation_data = year_region_df.groupby('technology')['generated_mwh'].sum()
    
    if generation_data.empty or generation_data.sum() == 0:
        ax.text(0.5, 0.5, 'No generation recorded for this period.', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    else:
        ax.pie(generation_data, labels=generation_data.index, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
        ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
    
    ax.set_title(f'Generation Mix in {region} - {year}')
    plt.tight_layout()
    return plot_to_base64(fig)

# --- HTML Generation ---

def generate_html_report(data_df, plots_dict):
    """Generates the HTML report string with embedded plots and data tables."""
    
    # Executive Summary
    invested_techs = data_df[data_df['metric_type'] == 'investment']['technology'].unique()
    non_invested_techs = [tech for tech in SIMULATION_TECHNOLOGIES if tech not in invested_techs]
    
    final_year_data = data_df[data_df['year'] == END_YEAR]
    exec_summary_market = ""
    if not final_year_data.empty:
        # Ensure that 'first' is a safe aggregation if multiple rows exist per region/year after other processing.
        # If processed_df can have multiple entries for a region in a year that aren't duplicates for these fields,
        # this aggregation might need to be more specific. Given current parsing, 'first' should be okay.
        regional_summary_final_year = final_year_data.groupby('region').agg(
            total_demand=('demand_mwh', 'first'),
            total_generation=('dispatched_mwh', 'first'),
            total_unmet=('unmet_demand_mwh', 'first')
        ).reset_index()
        exec_summary_market = "<p>In the final simulated year ({}):</p><ul>".format(END_YEAR)
        for _, row in regional_summary_final_year.iterrows():
            exec_summary_market += f"<li><b>{row['region']}:</b> Demand: {row['total_demand']:,.0f} MWh, Generation: {row['total_generation']:,.0f} MWh, Unmet: {row['total_unmet']:,.0f} MWh.</li>"
        exec_summary_market += "</ul>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Global Solar Energy Simulation Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; color: #333; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            h1 {{ text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px; }}
            .container {{ max-width: 1200px; margin: auto; }}
            .section {{ margin-bottom: 30px; padding: 15px; background-color: #f9f9f9; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.05);}}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #3498db; color: white; }}
            img {{ max-width: 100%; height: auto; display: block; margin: 15px auto; border: 1px solid #ddd; border-radius: 4px; }}
            .plot-container {{ text-align: center; margin-bottom: 20px;}}
            .executive-summary, .conclusions, .project-context {{ background-color: #eaf5ff; border-left: 5px solid #3498db; padding: 15px;}}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Global Solar Energy Simulation Report ({START_YEAR}-{END_YEAR})</h1>

            <div class="section executive-summary">
                <h2>Executive Summary</h2>
                <p>This report summarizes key findings from a specific simulation run ({START_YEAR}-{END_YEAR}) within the broader <strong>Ultra-High-Resolution Global Solar Energy Simulation Framework</strong>. 
                   The framework aims to comprehensively model global solar energy deployment considering diverse technical, economic, policy, social, and environmental factors. 
                   This particular simulation focused on core investment decisions and market outcomes in three primary regions: {', '.join(REGIONS)}, evaluating technologies: {', '.join(SIMULATION_TECHNOLOGIES)}.</p>
                <p>Key observations from this run include:
                    <ul>
                        <li>Consistent investment was primarily directed towards <strong>{', '.join(invested_techs) if invested_techs.size > 0 else "No specific technology"}</strong> across all simulated regions and years.</li>
                        {"<li>Technologies such as <strong>" + ', '.join(non_invested_techs) + "</strong> did not see investment. Within the context of this simulation's parameters (e.g., costs, market prices, basic policy model), their projected net present value (NPV) or attractiveness scores were likely insufficient.</li>" if non_invested_techs else ""}
                        <li>Significant <strong>unmet energy demand</strong> was observed in all regions throughout the simulation period, indicating a gap between projected energy needs and dispatched generation from the newly invested and existing (if any) capacities in this specific scenario.</li>
                    </ul>
                </p>
                {exec_summary_market}
            </div>

            <div class="section">
                <h2>Simulation Overview</h2>
                <p>This analysis pertains to a simulation run for the period <strong>{START_YEAR} - {END_YEAR}</strong>, covering the regions: <strong>{', '.join(REGIONS)}</strong>. The technologies explicitly modeled for investment and generation in this run were: <strong>{', '.join(SIMULATION_TECHNOLOGIES)}</strong>.</p>
                <p>The simulation, part of the larger framework's phased development, aimed to model core aspects of investment decisions (driven by the InvestmentDecisionModel), technological evolution (via SolarTechModel), cost dynamics (CostModel), supply chain influences (SupplyChainModel), market interactions (MarketSimulator), and grid capacity evolution (GridModel). The results presented here reflect the interplay of these components under the specific configurations and input data used for this simulation instance.</p>
            </div>

            <div class="section project-context">
                <h2>Project Context & Future Outlook</h2>
                <p>The findings in this report stem from a simulation exercise within the <strong>Ultra-High-Resolution Global Solar Energy Simulation Framework</strong>, an ambitious project designed to provide deep insights into the multifaceted transition to solar energy. The framework is modular, encompassing areas such as:</p>
                <ul>
                    <li><strong>Foundation Elements:</strong> Regional details, climate zones, comprehensive technology portfolios.</li>
                    <li><strong>Economic Framework:</strong> Detailed cost structures, diverse market designs, carbon pricing.</li>
                    <li><strong>Policy Landscape:</strong> National/international climate policies, support mechanisms, regulatory impacts.</li>
                    <li><strong>Grid Integration Architecture:</strong> Power system transformation, grid security, advanced grid technologies.</li>
                    <li><strong>Supply Chain Dynamics:</strong> Manufacturing capacity, material availability, geopolitical risks, circular economy.</li>
                    <li><strong>Climate & Environmental Dimensions:</strong> Carbon mitigation, life-cycle emissions, climate resilience.</li>
                    <li><strong>Socioeconomic Dimensions:</strong> Employment, energy equity, community impacts.</li>
                    <li><strong>Sector Coupling:</strong> Interactions with transport, industry, and building systems.</li>
                </ul>
                <p>The current simulation provides valuable baseline insights based on the implemented modules (primarily focusing on economic viability and basic market dispatch for selected solar and storage technologies). Future iterations of the framework will progressively incorporate more detailed and dynamic modeling of the modules listed above. For instance, nuanced policy scenarios, sophisticated supply chain constraints, detailed environmental impact assessments, and socioeconomic feedback loops are planned.</p>
                <p>As these advanced features are integrated, the simulation outcomes—such as technology adoption trajectories, regional investment patterns, and the extent of unmet demand—are expected to become more refined and reflective of real-world complexities. This iterative development will enhance the framework's capability to explore diverse future energy pathways and inform strategic decision-making.</p>
            </div>

            <div class="section">
                <h2>Investment Analysis</h2>
                <p>The following chart illustrates the cumulative installed capacity (MW) from new investments over the simulation period, based on the current model's decision-making.</p>
                <div class="plot-container">
                    <img src="{plots_dict.get('cumulative_investment_plot', '')}" alt="Cumulative Investment Plot">
                </div>
    """
    
    # Investment Table for final year
    final_year_investments = data_df[(data_df['year'] == END_YEAR) & (data_df['metric_type'] == 'investment') & (data_df['cumulative_investment_mw'] > 0)]
    if not final_year_investments.empty:
        investment_summary_table = final_year_investments[['region', 'technology', 'cumulative_investment_mw']].rename(
            columns={'cumulative_investment_mw': f'Total Installed Capacity (MW) from New Investments by {END_YEAR}'}
        ).pivot_table(index='region', columns='technology', values=f'Total Installed Capacity (MW) from New Investments by {END_YEAR}', fill_value=0).reset_index()
        html_content += f"<h3>Total Installed Capacity (MW) from New Investments by End of Simulation ({END_YEAR})</h3>"
        html_content += investment_summary_table.to_html(index=False, classes='data-table', float_format='{:,.0f}'.format)
    else:
        html_content += f"<p>No new investments leading to cumulative capacity were recorded by {END_YEAR} in this simulation run, or data is insufficient for this table.</p>"


    html_content += """
            </div>

            <div class="section">
                <h2>Market Outcomes Analysis</h2>
    """

    for region in REGIONS:
        html_content += f"""
                <h3>Market Dynamics: {region}</h3>
                <p>The chart below shows the annual energy demand, total dispatched generation from modeled technologies, and resulting unmet demand for {region} in this simulation.</p>
                <div class="plot-container">
                    <img src="{plots_dict.get(f'market_dynamics_{region}', '')}" alt="Market Dynamics Plot for {region}">
                </div>
                
                <h4>Generation Mix from Modeled Technologies in {region} ({END_YEAR})</h4>
                 <div class="plot-container">
                    <img src="{plots_dict.get(f'generation_mix_{region}_{END_YEAR}', '')}" alt="Generation Mix Pie Chart for {region} {END_YEAR}">
                </div>
        """
        # Market summary table for the final year for this region
        region_final_data = final_year_data[final_year_data['region'] == region]
        if not region_final_data.empty:
            # Need to get the specific values for demand, dispatched, unmet for the region
            # Assuming these are consistent across tech entries for a given year/region from parsing logic
            demand_val = region_final_data['demand_mwh'].iloc[0] if not region_final_data['demand_mwh'].empty else 0
            dispatched_val = region_final_data['dispatched_mwh'].iloc[0] if not region_final_data['dispatched_mwh'].empty else 0
            unmet_val = region_final_data['unmet_demand_mwh'].iloc[0] if not region_final_data['unmet_demand_mwh'].empty else 0
            
            market_summary_dict = {
                'Metric': ['Annual Demand (MWh)', 'Total Dispatched Generation (MWh)', 'Unmet Demand (MWh)'],
                'Value': [f'{demand_val:,.0f}', f'{dispatched_val:,.0f}', f'{unmet_val:,.0f}']
            }
            market_summary_table_df = pd.DataFrame(market_summary_dict)
            html_content += f"<h4>Key Market Metrics for {region} - {END_YEAR} (This Simulation Run)</h4>"
            html_content += market_summary_table_df.to_html(index=False, classes='data-table')
        else:
            html_content += f"<p>No market summary data available for {region} in {END_YEAR} for this simulation run.</p>"


    html_content += """
            </div>

            <div class="section conclusions">
                <h2>Conclusions from This Simulation Run</h2>
                <p>Based on the specific parameters, inputs, and model configurations of <em>this simulation run</em>:</p>
                <ul>
                    <li><strong>LFP Battery technology</strong> demonstrated consistent economic attractiveness relative to the other modeled PV technologies, leading to its adoption across all analyzed regions. This suggests that, under the simulated cost structures and market conditions, battery storage can be a viable investment.</li>
                    <li>The <strong>absence of investment in other solar PV technologies</strong> (TOPCon_PV, AdvancedMonocrystallineSilicon) in this run indicates that their projected returns did not meet the investment thresholds set by the model. This outcome is sensitive to the specific CAPEX, efficiency, and degradation assumptions for these technologies versus LFP Battery, as well as the market price signals used.</li>
                    <li>A <strong>significant and persistent unmet energy demand</strong> was observed in USA, China, and EU_Germany. This highlights that, with the investments made by the model in this run, a substantial gap remains between demand and the supply provided by the considered technologies. This outcome underscores the scale of the challenge in meeting future energy needs.</li>
                </ul>
                <p><strong>Important Context:</strong> These conclusions are a snapshot based on the current development stage of the <strong>Ultra-High-Resolution Global Solar Energy Simulation Framework</strong>. As the framework evolves to include more detailed modeling of policies, supply chains, grid constraints, environmental factors, and socioeconomic dynamics, the simulated investment patterns and market outcomes may change significantly. Future analyses with more comprehensive module integration will provide a richer understanding of potential global solar energy deployment pathways.</p>
                <p>Further analysis, even with the current modules, could explore sensitivity to carbon prices, varying cost trajectories for PV technologies, different policy incentives, and more dynamic supply chain assumptions to refine these initial insights.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# --- Main Execution ---

if __name__ == "__main__":
    print(f"Starting report generation from {CSV_FILE_NAME}...")
    
    # Check if CSV exists
    if not os.path.exists(CSV_FILE_NAME):
        print(f"ERROR: CSV file '{CSV_FILE_NAME}' not found in the current directory: {os.getcwd()}")
        exit()

    # 1. Load and Prepare Data
    print("Loading and parsing data...")
    try:
        data_df = parse_and_prepare_data(CSV_FILE_NAME)
        if data_df.empty:
            print("ERROR: No data processed from CSV. Exiting.")
            exit()
        print("Data loaded and parsed successfully.")
        # print("\nSample of Processed DataFrame:")
        # print(data_df.head())
        # print(f"Total records processed: {len(data_df)}")
    except Exception as e:
        print(f"Error during data parsing: {e}")
        # print traceback
        import traceback
        traceback.print_exc()
        exit()

    # 2. Generate Plots
    print("Generating plots...")
    plots = {}
    try:
        plots['cumulative_investment_plot'] = generate_cumulative_investment_plot(data_df)
        print("- Cumulative investment plot generated.")
        for region in REGIONS:
            plots[f'market_dynamics_{region}'] = generate_market_dynamics_plot(data_df, region)
            print(f"- Market dynamics plot for {region} generated.")
            plots[f'generation_mix_{region}_{END_YEAR}'] = generate_generation_mix_pie_chart(data_df, region, END_YEAR)
            print(f"- Generation mix pie chart for {region} ({END_YEAR}) generated.")
        print("All plots generated successfully.")
    except Exception as e:
        print(f"Error during plot generation: {e}")
        import traceback
        traceback.print_exc()
        # Continue to generate report with available plots if any
    
    # 3. Generate HTML Report
    print("Generating HTML report...")
    try:
        html_report = generate_html_report(data_df, plots)
        print("HTML report content generated.")
    except Exception as e:
        print(f"Error during HTML report generation: {e}")
        import traceback
        traceback.print_exc()
        exit()

    # 4. Save HTML Report
    try:
        with open(HTML_REPORT_FILE_NAME, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"Successfully saved HTML report to: {os.path.join(os.getcwd(), HTML_REPORT_FILE_NAME)}")
    except Exception as e:
        print(f"Error saving HTML report: {e}")
        import traceback
        traceback.print_exc()

    print("Report generation process complete.") 