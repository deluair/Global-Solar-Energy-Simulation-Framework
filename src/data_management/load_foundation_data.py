import csv
from typing import List, Optional, Dict
from ..modules.foundation_elements.data_models import Country, PVTechnology, StorageTechnology, GridArchitecture, ClimateZone, LandType
import os
from pathlib import Path

def load_countries_data(csv_file_path: str) -> List[Country]:
    """Loads country data from a CSV file and returns a list of Country objects."""
    countries: List[Country] = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '')
                iso_code = row.get('iso_code', '')
                is_key_market_str = row.get('is_key_market', 'FALSE').upper()
                is_key_market = True if is_key_market_str == 'TRUE' else False
                
                sub_national_regions_str = row.get('sub_national_regions')
                sub_national_regions_list: Optional[List[str]] = None
                if sub_national_regions_str and sub_national_regions_str.strip():
                    sub_national_regions_list = [region.strip() for region in sub_national_regions_str.split(';')]
                
                if name and iso_code: # Basic validation
                    countries.append(Country(
                        name=name,
                        iso_code=iso_code,
                        key_market=is_key_market,
                        sub_national_regions=sub_national_regions_list
                    ))
                else:
                    print(f"Skipping row due to missing name or iso_code: {row}")
                    
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return [] # Return empty list or raise error
    except Exception as e:
        print(f"An error occurred while reading {csv_file_path}: {e}")
        return [] # Return empty list or raise error
    
    return countries

def load_pv_technologies_data(csv_file_path: str) -> List[PVTechnology]:
    """Loads PV technology data from a CSV file and returns a list of PVTechnology objects."""
    technologies: List[PVTechnology] = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '')
                technology_type = row.get('technology_type', '')
                form_factor = row.get('form_factor')
                notes = row.get('notes')

                efficiency_projections_str = row.get('efficiency_projections_data', '')
                efficiency_projections_dict: Optional[Dict[int, float]] = {}
                if efficiency_projections_str and efficiency_projections_str.strip():
                    pairs = efficiency_projections_str.split(';')
                    for pair in pairs:
                        if ':' in pair:
                            try:
                                year_str, eff_str = pair.split(':', 1)
                                efficiency_projections_dict[int(year_str.strip())] = float(eff_str.strip())
                            except ValueError as ve:
                                print(f"Skipping malformed efficiency projection pair for '{name}': '{pair}'. Error: {ve}")
                                # Continue to next pair if possible
                
                if name and technology_type: # Basic validation
                    technologies.append(PVTechnology(
                        name=name,
                        technology_type=technology_type,
                        form_factor=form_factor if form_factor and form_factor.strip() else None,
                        efficiency_projections=efficiency_projections_dict,
                        notes=notes if notes and notes.strip() else None
                    ))
                else:
                    print(f"Skipping PV technology row due to missing name or type: {row}")

    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading {csv_file_path}: {e}")
        return []
        
    return technologies

def load_storage_technologies_data(csv_file_path: str) -> List[StorageTechnology]:
    """Loads storage technology data from a CSV file into a list of StorageTechnology objects."""
    technologies: List[StorageTechnology] = []
    print(f"\nAttempting to load storage technologies from: {csv_file_path}")
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Parse cost_per_kwh_projection_usd
                parsed_cost_projections = {}
                if row.get('cost_per_kwh_projection_usd'):
                    try:
                        pairs = row['cost_per_kwh_projection_usd'].split(';')
                        for pair in pairs:
                            if ':' in pair:
                                year, cost = pair.split(':')
                                parsed_cost_projections[int(year.strip())] = float(cost.strip())
                    except ValueError as e:
                        print(f"Warning: Could not parse cost projections for {row.get('name', 'Unknown Storage Tech')}: {row['cost_per_kwh_projection_usd']}. Error: {e}")

                # Parse round_trip_efficiency_projection_percent
                parsed_efficiency_projections = {}
                if row.get('round_trip_efficiency_projection_percent'):
                    try:
                        pairs = row['round_trip_efficiency_projection_percent'].split(';')
                        for pair in pairs:
                            if ':' in pair:
                                year, rte = pair.split(':')
                                parsed_efficiency_projections[int(year.strip())] = float(rte.strip())
                    except ValueError as e:
                        print(f"Warning: Could not parse round trip efficiency for {row.get('name', 'Unknown Storage Tech')}: {row['round_trip_efficiency_projection_percent']}. Error: {e}")
                
                # Get other fields, converting to appropriate types
                commercial_scale_year_str = row.get('commercial_scale_year')
                commercial_scale_year = int(commercial_scale_year_str) if commercial_scale_year_str and commercial_scale_year_str.strip() else None
                
                price_reduction_factor_str = row.get('projected_price_reduction_factor_2035')
                projected_price_reduction_factor_2035 = float(price_reduction_factor_str) if price_reduction_factor_str and price_reduction_factor_str.strip() else None

                tech = StorageTechnology(
                    name=row.get('name', 'Unnamed Storage Technology'),
                    storage_type=row.get('type', 'N/A'),
                    form_factor=row.get('form_factor', 'N/A'),
                    cost_projections=parsed_cost_projections if parsed_cost_projections else None,
                    efficiency_projections=parsed_efficiency_projections if parsed_efficiency_projections else None,
                    commercial_scale_year=commercial_scale_year,
                    projected_price_reduction_factor_2035=projected_price_reduction_factor_2035,
                    notes=row.get('notes', '')
                )
                technologies.append(tech)
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading storage technologies: {e}")
        return []

    print(f"\nSuccessfully loaded {len(technologies)} storage technologies:")
    for tech in technologies:
        print(f"- Name: {tech.name}, Type: {tech.storage_type}, Form Factor: {tech.form_factor}, "
              f"Cost Proj: {tech.cost_projections}, Efficiency Proj: {tech.efficiency_projections}, "
              f"Commercial Year: {tech.commercial_scale_year}, Price Factor 2035: {tech.projected_price_reduction_factor_2035}, "
              f"Notes: {tech.notes}")
    return technologies

def load_grid_architectures_data(csv_file_path: str) -> List[GridArchitecture]:
    """Loads grid architecture data from a CSV file and returns a list of GridArchitecture objects."""
    architectures: List[GridArchitecture] = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                region_name = row.get('region_name', '')
                transmission_constraints = row.get('transmission_constraints', '')
                stability_requirements = row.get('stability_requirements', '')
                interconnection_patterns = row.get('interconnection_patterns', '')
                
                # All fields are expected to be present as per the data model, but allow empty strings if that's acceptable.
                # Assuming non-empty strings are required for meaningful data based on the model's design.
                if region_name and transmission_constraints and stability_requirements and interconnection_patterns:
                    architectures.append(GridArchitecture(
                        region_name=region_name,
                        transmission_constraints=transmission_constraints,
                        stability_requirements=stability_requirements,
                        interconnection_patterns=interconnection_patterns
                    ))
                else:
                    print(f"Skipping row due to missing mandatory fields for GridArchitecture: {row}")
                    
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return [] 
    except Exception as e:
        print(f"An error occurred while reading {csv_file_path}: {e}")
        return []
    
    return architectures

def load_climate_zones_data(csv_file_path: str) -> List[ClimateZone]:
    """Loads climate zone data from a CSV file and returns a list of ClimateZone objects."""
    climate_zones: List[ClimateZone] = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                name = row.get('name', '')
                resolution_minutes_str = row.get('resolution_minutes', '')
                data_source_path = row.get('data_source_path') # Can be None if column is missing or empty string

                if not name:
                    print(f"Skipping row due to missing name for ClimateZone: {row}")
                    continue
                
                try:
                    resolution_minutes = int(resolution_minutes_str)
                except ValueError:
                    print(f"Skipping row for ClimateZone '{name}' due to invalid resolution_minutes: '{resolution_minutes_str}'.")
                    continue

                # Handle empty string for optional data_source_path as None
                actual_data_source_path = data_source_path if data_source_path and data_source_path.strip() else None

                climate_zones.append(ClimateZone(
                    name=name,
                    resolution_minutes=resolution_minutes,
                    data_source_path=actual_data_source_path
                ))
                    
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return [] 
    except Exception as e:
        print(f"An error occurred while reading {csv_file_path}: {e}")
        return []
    
    return climate_zones

def load_land_types_data(csv_file_path: str) -> List[LandType]:
    """Loads land type data from a CSV file and returns a list of LandType objects."""
    land_types: List[LandType] = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8', newline='') as file:
            reader = csv.DictReader(file)
            for row in reader:
                category_id = row.get('category_id', '')
                name = row.get('name', '')
                description = row.get('description') # Can be None or empty string

                if not category_id or not name:
                    print(f"Skipping row due to missing category_id or name for LandType: {row}")
                    continue

                # Handle empty string for optional description as None
                actual_description = description if description and description.strip() else None

                land_types.append(LandType(
                    category_id=category_id,
                    name=name,
                    description=actual_description
                ))
                    
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading {csv_file_path}: {e}")
        return []
    
    return land_types

if __name__ == "__main__":
    # Determine the base path of the project
    project_base_path = Path(__file__).resolve().parent.parent.parent 
    # Construct paths to the example CSV files
    countries_csv_path = project_base_path / "examples" / "example_countries.csv"
    pv_tech_csv_path = project_base_path / "examples" / "example_pv_technologies.csv"
    storage_tech_csv_path = project_base_path / "examples" / "example_storage_technologies.csv"
    grid_arch_csv_path = project_base_path / "examples" / "example_grid_architectures.csv"
    climate_zones_csv_path = project_base_path / "examples" / "example_climate_zones.csv"
    land_types_csv_path = project_base_path / "examples" / "example_land_types.csv"

    # Load data
    countries = load_countries_data(str(countries_csv_path))
    pv_technologies = load_pv_technologies_data(str(pv_tech_csv_path))
    storage_technologies = load_storage_technologies_data(str(storage_tech_csv_path))
    grid_architectures = load_grid_architectures_data(str(grid_arch_csv_path))
    climate_zones = load_climate_zones_data(str(climate_zones_csv_path))
    land_types = load_land_types_data(str(land_types_csv_path))

    # Example: Print loaded data to verify (optional)
    # print("\nLoaded Countries:")
    # for country in countries:
    # print(f"  {country.name} (ISO: {country.iso_code}), Key Market: {country.key_market}, Regions: {country.sub_national_regions}")
    
    print("\nLoaded PV Technologies:")
    for pv_tech in pv_technologies:
        print(f"  {pv_tech.name} ({pv_tech.technology_type}), Form Factor: {pv_tech.form_factor}, Efficiencies: {pv_tech.efficiency_projections}, Notes: {pv_tech.notes}")

    print("\nLoaded Grid Architectures:")
    for arch in grid_architectures:
        print(f"  {arch.region_name}, Transmission Constraints: {arch.transmission_constraints}, Stability Requirements: {arch.stability_requirements}, Interconnection Patterns: {arch.interconnection_patterns}")

    print("\nLoaded Climate Zones:")
    for cz in climate_zones:
        print(f"  {cz.name}, Resolution Minutes: {cz.resolution_minutes}, Data Source Path: {cz.data_source_path}")

    print("\nLoaded Land Types:")
    for lt in land_types:
        print(f"  {lt.name}, Category ID: {lt.category_id}, Description: {lt.description}")
