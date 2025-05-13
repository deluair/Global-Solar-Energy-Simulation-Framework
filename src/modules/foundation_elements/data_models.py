from typing import List, Dict, Optional

class Country:
    """Represents a country-level model with sub-national resolution for key markets."""
    def __init__(self, 
                 name: str, 
                 iso_code: str, 
                 key_market: bool = False, 
                 sub_national_regions: Optional[List[str]] = None):
        self.name = name
        self.iso_code = iso_code
        self.key_market = key_market
        self.sub_national_regions = sub_national_regions if sub_national_regions else []

    def __repr__(self):
        return f"Country(name='{self.name}', iso_code='{self.iso_code}', key_market={self.key_market})"

class GridArchitecture:
    """Represents a region-specific grid architecture."""
    def __init__(self, 
                 region_name: str, 
                 transmission_constraints: str, 
                 stability_requirements: str, 
                 interconnection_patterns: str):
        self.region_name = region_name
        self.transmission_constraints = transmission_constraints
        self.stability_requirements = stability_requirements
        self.interconnection_patterns = interconnection_patterns

    def __repr__(self):
        return f"GridArchitecture(region_name='{self.region_name}')"

class ClimateZone:
    """Represents a climate zone with specific temporal resolution."""
    def __init__(self, 
                 name: str, 
                 resolution_minutes: int, # e.g., 60 for hourly, 5 for critical markets
                 data_source_path: Optional[str] = None):
        self.name = name
        self.resolution_minutes = resolution_minutes
        self.data_source_path = data_source_path

    def __repr__(self):
        return f"ClimateZone(name='{self.name}', resolution_minutes={self.resolution_minutes})"

class LandType:
    """Represents a granular land type classification."""
    def __init__(self, category_id: str, name: str, description: Optional[str] = None):
        self.category_id = category_id
        self.name = name
        self.description = description

    def __repr__(self):
        return f"LandType(category_id='{self.category_id}', name='{self.name}')"

class PVTechnology:
    """Represents a solar photovoltaic technology with its evolution."""
    def __init__(self, 
                 name: str, 
                 technology_type: str, # e.g., 'Silicon', 'Tandem', 'Emerging'
                 form_factor: Optional[str] = None, # e.g., 'Single-axis tracking', 'BIPV'
                 efficiency_projections: Optional[Dict[int, float]] = None, # {year: efficiency}
                 notes: Optional[str] = None):
        self.name = name
        self.technology_type = technology_type
        self.form_factor = form_factor
        self.efficiency_projections = efficiency_projections if efficiency_projections else {}
        self.notes = notes

    def __repr__(self):
        return f"PVTechnology(name='{self.name}', type='{self.technology_type}')"

class StorageTechnology:
    """Represents an energy storage technology and its characteristics."""
    def __init__(self, 
                 name: str, 
                 storage_type: str, # e.g., 'Electrochemical', 'Long-Duration Storage'
                 form_factor: Optional[str] = None, 
                 cost_projections: Optional[Dict[int, float]] = None, 
                 efficiency_projections: Optional[Dict[int, float]] = None, 
                 commercial_scale_year: Optional[int] = None,
                 projected_price_reduction_factor_2035: Optional[float] = None, # e.g., 0.1 for 90% reduction
                 notes: Optional[str] = None):
        self.name = name
        self.storage_type = storage_type
        self.form_factor = form_factor 
        self.cost_projections = cost_projections if cost_projections else {} 
        self.efficiency_projections = efficiency_projections if efficiency_projections else {} 
        self.commercial_scale_year = commercial_scale_year
        self.projected_price_reduction_factor_2035 = projected_price_reduction_factor_2035
        self.notes = notes

    def __repr__(self):
        return f"StorageTechnology(name='{self.name}', type='{self.storage_type}', form_factor='{self.form_factor}')"
