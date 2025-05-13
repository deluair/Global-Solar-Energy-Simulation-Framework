import unittest
import os
import csv
import sys
from typing import List, Dict, Any

# Add project root to sys.path to allow direct import of src modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.modules.foundation_elements.data_models import StorageTechnology, PVTechnology, Country, GridArchitecture, ClimateZone
from src.data_management.load_foundation_data import (
    load_storage_technologies_data, load_pv_technologies_data, 
    load_countries_data, load_grid_architectures_data, load_climate_zones_data
)

class TestLoadStorageTechnologiesData(unittest.TestCase):

    def setUp(self):
        """Set up for test methods. This method is called before each test method."""
        # Define a directory for test-specific data files
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)
        
        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_storage_techs.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_storage_techs.csv')
        self.malformed_csv_path = os.path.join(self.test_data_fdn_dir, 'malformed_storage_techs.csv')
        self.missing_optional_csv_path = os.path.join(self.test_data_fdn_dir, 'missing_optional_storage_techs.csv')

        # Sample data for CSV files
        self.csv_header = ['name', 'type', 'form_factor', 'cost_per_kwh_projection_usd', 'round_trip_efficiency_projection_percent', 'commercial_scale_year', 'projected_price_reduction_factor_2035', 'notes']
        
        self.sample_valid_rows = [
            self.csv_header,
            ['TestLFP', 'Electrochemical', 'Pack', '2025:100;2030:70', '2025:90;2030:92', '2022', '0.15', 'Test LFP notes'],
            ['TestSodium', 'Electrochemical', 'Cell', '2026:90;2032:60', '2026:88;2032:90', '2026', '0.2', 'Test Sodium notes']
        ]
        self._create_csv_file(self.valid_csv_path, self.sample_valid_rows)

        self._create_csv_file(self.empty_csv_path, [self.csv_header]) # Header only

        malformed_rows = [
            self.csv_header,
            ['TestMalformed', 'TestType', 'TestForm', '2025:bad;2030:70', '2025:90;2030:good', '2023', '0.1', 'Malformed data test']
        ]
        self._create_csv_file(self.malformed_csv_path, malformed_rows)

        missing_optional_rows = [
            self.csv_header,
            ['TestMissing', 'OptionalType', 'OptionalForm', '', '', '', '', 'Missing optional data test']
        ]
        self._create_csv_file(self.missing_optional_csv_path, missing_optional_rows)

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        """Helper method to create a CSV file with given data."""
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def tearDown(self):
        """Clean up after test methods. This method is called after each test method."""
        files_to_remove = [self.valid_csv_path, self.empty_csv_path, self.malformed_csv_path, self.missing_optional_csv_path]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        
        # Attempt to remove the test_data directories if they are empty
        if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
            os.rmdir(self.test_data_fdn_dir)
        if os.path.exists(self.test_data_root_dir) and not os.listdir(self.test_data_root_dir):
            os.rmdir(self.test_data_root_dir)

    def test_load_valid_data(self):
        """Test loading data from a correctly formatted CSV file."""
        technologies = load_storage_technologies_data(self.valid_csv_path)
        self.assertEqual(len(technologies), 2)
        
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestLFP')
        self.assertEqual(tech1.storage_type, 'Electrochemical')
        self.assertEqual(tech1.form_factor, 'Pack')
        self.assertEqual(tech1.cost_projections, {2025: 100.0, 2030: 70.0})
        self.assertEqual(tech1.efficiency_projections, {2025: 90.0, 2030: 92.0})
        self.assertEqual(tech1.commercial_scale_year, 2022)
        self.assertEqual(tech1.projected_price_reduction_factor_2035, 0.15)
        self.assertEqual(tech1.notes, 'Test LFP notes')

        tech2 = technologies[1]
        self.assertEqual(tech2.name, 'TestSodium')
        self.assertEqual(tech2.cost_projections, {2026: 90.0, 2032: 60.0})
        self.assertEqual(tech2.efficiency_projections, {2026: 88.0, 2032: 90.0})
        self.assertEqual(tech2.commercial_scale_year, 2026)
        self.assertEqual(tech2.projected_price_reduction_factor_2035, 0.2)

    def test_load_non_existent_file(self):
        """Test loading data from a non-existent CSV file."""
        technologies = load_storage_technologies_data('non_existent_file.csv')
        self.assertEqual(len(technologies), 0)

    def test_load_empty_csv(self):
        """Test loading data from an empty CSV file (header only)."""
        technologies = load_storage_technologies_data(self.empty_csv_path)
        self.assertEqual(len(technologies), 0)

    def test_load_malformed_projection_data(self):
        """Test loading data with malformed projection strings."""
        technologies = load_storage_technologies_data(self.malformed_csv_path)
        self.assertEqual(len(technologies), 1)
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestMalformed')
        self.assertEqual(tech1.cost_projections, {})
        self.assertEqual(tech1.efficiency_projections, {2025: 90.0})
        self.assertEqual(tech1.commercial_scale_year, 2023)
        self.assertEqual(tech1.projected_price_reduction_factor_2035, 0.1)

    def test_load_missing_optional_data(self):
        """Test loading data where optional fields are missing."""
        technologies = load_storage_technologies_data(self.missing_optional_csv_path)
        self.assertEqual(len(technologies), 1)
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestMissing')
        self.assertEqual(tech1.storage_type, 'OptionalType')
        self.assertEqual(tech1.form_factor, 'OptionalForm')
        self.assertEqual(tech1.cost_projections, {})
        self.assertEqual(tech1.efficiency_projections, {})
        self.assertIsNone(tech1.commercial_scale_year)
        self.assertIsNone(tech1.projected_price_reduction_factor_2035)
        self.assertEqual(tech1.notes, 'Missing optional data test')

class TestLoadPVTechnologiesData(unittest.TestCase):

    def setUp(self):
        """Set up for test methods. This method is called before each test method."""
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)
        
        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_pv_techs.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_pv_techs.csv')
        self.malformed_csv_path = os.path.join(self.test_data_fdn_dir, 'malformed_pv_techs.csv')
        self.missing_optional_csv_path = os.path.join(self.test_data_fdn_dir, 'missing_optional_pv_techs.csv')

        self.csv_header = ['name', 'technology_type', 'form_factor', 'efficiency_projections_data', 'notes']
        
        sample_valid_rows = [
            self.csv_header,
            ['TestTOPCon', 'Silicon', 'Utility-Scale', '2025:0.24;2030:0.25', 'Test TOPCon notes'],
            ['TestHJT', 'Silicon', 'Rooftop', '2025:0.25;2030:0.26', 'Test HJT notes']
        ]
        self._create_csv_file(self.valid_csv_path, sample_valid_rows)

        self._create_csv_file(self.empty_csv_path, [self.csv_header]) # Header only

        malformed_rows = [
            self.csv_header,
            ['TestMalformedPV', 'Silicon', 'Utility', '2025:bad;2030:0.25', 'Malformed PV data test']
        ]
        self._create_csv_file(self.malformed_csv_path, malformed_rows)

        missing_optional_rows = [
            self.csv_header,
            ['TestMissingPV', 'Emerging', '', '', 'Missing optional PV notes'] # form_factor and efficiency_projections empty
        ]
        self._create_csv_file(self.missing_optional_csv_path, missing_optional_rows)

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        """Helper method to create a CSV file with given data."""
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def tearDown(self):
        """Clean up after test methods. This method is called after each test method."""
        files_to_remove = [
            self.valid_csv_path, 
            self.empty_csv_path, 
            self.malformed_csv_path, 
            self.missing_optional_csv_path
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        
        # Attempt to remove the test_data directories if they are empty
        # This check is basic; assumes only this test class uses these specific files in this dir.
        # More robust cleanup might be needed if multiple test classes share dirs and file naming patterns.
        if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
            try:
                os.rmdir(self.test_data_fdn_dir)
            except OSError: # Directory might not be empty due to other tests
                pass 
        if os.path.exists(self.test_data_root_dir) and not os.listdir(self.test_data_root_dir):
            try:
                os.rmdir(self.test_data_root_dir)
            except OSError:
                pass

    def test_load_valid_pv_data(self):
        """Test loading PV data from a correctly formatted CSV file."""
        technologies = load_pv_technologies_data(self.valid_csv_path)
        self.assertEqual(len(technologies), 2)
        
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestTOPCon')
        self.assertEqual(tech1.technology_type, 'Silicon')
        self.assertEqual(tech1.form_factor, 'Utility-Scale')
        self.assertEqual(tech1.efficiency_projections, {2025: 0.24, 2030: 0.25})
        self.assertEqual(tech1.notes, 'Test TOPCon notes')

        tech2 = technologies[1]
        self.assertEqual(tech2.name, 'TestHJT')
        self.assertEqual(tech2.efficiency_projections, {2025: 0.25, 2030: 0.26})

    def test_load_pv_non_existent_file(self):
        """Test loading PV data from a non-existent CSV file."""
        technologies = load_pv_technologies_data('non_existent_pv_file.csv')
        self.assertEqual(len(technologies), 0)

    def test_load_pv_empty_csv(self):
        """Test loading PV data from an empty CSV file (header only)."""
        technologies = load_pv_technologies_data(self.empty_csv_path)
        self.assertEqual(len(technologies), 0)

    def test_load_pv_malformed_projection_data(self):
        """Test loading PV data with malformed efficiency_projections_data."""
        technologies = load_pv_technologies_data(self.malformed_csv_path)
        self.assertEqual(len(technologies), 1)
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestMalformedPV')
        # Best-effort parsing: valid parts should be kept
        self.assertEqual(tech1.efficiency_projections, {2030: 0.25}) 
        self.assertEqual(tech1.notes, 'Malformed PV data test')

    def test_load_pv_missing_optional_data(self):
        """Test loading PV data where optional fields are missing."""
        technologies = load_pv_technologies_data(self.missing_optional_csv_path)
        self.assertEqual(len(technologies), 1)
        tech1 = technologies[0]
        self.assertEqual(tech1.name, 'TestMissingPV')
        self.assertEqual(tech1.technology_type, 'Emerging')
        self.assertIsNone(tech1.form_factor) # Empty string in CSV becomes None
        self.assertEqual(tech1.efficiency_projections, {}) # Empty string becomes empty dict
        self.assertEqual(tech1.notes, 'Missing optional PV notes')

class TestLoadCountriesData(unittest.TestCase):
    def setUp(self):
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)

        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_countries.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_countries.csv')
        self.missing_fields_csv_path = os.path.join(self.test_data_fdn_dir, 'missing_fields_countries.csv')
        self.varied_data_csv_path = os.path.join(self.test_data_fdn_dir, 'varied_data_countries.csv')

        self.csv_header = ['name', 'iso_code', 'is_key_market', 'sub_national_regions']

        sample_valid_rows = [
            self.csv_header,
            ['CountryA', 'AAA', 'TRUE', 'RegionA1;RegionA2'],
            ['CountryB', 'BBB', 'FALSE', ''],
            ['CountryC', 'CCC', 'true', 'RegionC1'],
            ['CountryD', 'DDD', '', 'RegionD1;RegionD2;RegionD3'] # Missing is_key_market
        ]
        self._create_csv_file(self.valid_csv_path, sample_valid_rows)
        self._create_csv_file(self.empty_csv_path, [self.csv_header])

        missing_fields_rows = [
            self.csv_header,
            ['', 'EEE', 'TRUE', 'RegionE1'], # Missing name
            ['CountryF', '', 'FALSE', 'RegionF1']  # Missing iso_code
        ]
        self._create_csv_file(self.missing_fields_csv_path, missing_fields_rows)
        
        varied_data_rows = [
            self.csv_header,
            ['CountryG', 'GGG', 'FalSe', 'RegionG1'], # Varied case for is_key_market
            ['CountryH', 'HHH', 'Yes', 'RegionH1'],    # Invalid value for is_key_market
            ['CountryI', 'III', 'TRUE', '  RegionI1  ;  RegionI2  '] # Regions with extra spaces
        ]
        self._create_csv_file(self.varied_data_csv_path, varied_data_rows)

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def tearDown(self):
        files_to_remove = [
            self.valid_csv_path, self.empty_csv_path, 
            self.missing_fields_csv_path, self.varied_data_csv_path
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        
        # Attempt to remove the test_data directories if they are empty
        if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
            try: os.rmdir(self.test_data_fdn_dir)
            except OSError: pass
        if os.path.exists(self.test_data_root_dir) and not os.listdir(self.test_data_root_dir):
            try: os.rmdir(self.test_data_root_dir)
            except OSError: pass

    def test_load_valid_countries_data(self):
        countries = load_countries_data(self.valid_csv_path)
        self.assertEqual(len(countries), 4)
        self.assertEqual(countries[0].name, 'CountryA')
        self.assertTrue(countries[0].key_market)
        self.assertEqual(countries[0].sub_national_regions, ['RegionA1', 'RegionA2'])
        
        self.assertEqual(countries[1].name, 'CountryB')
        self.assertFalse(countries[1].key_market)
        self.assertEqual(countries[1].sub_national_regions, []) # Empty string results in empty list

        self.assertEqual(countries[2].name, 'CountryC')
        self.assertTrue(countries[2].key_market) # 'true' casing
        self.assertEqual(countries[2].sub_national_regions, ['RegionC1'])

        self.assertEqual(countries[3].name, 'CountryD')
        self.assertFalse(countries[3].key_market) # Missing is_key_market defaults to False
        self.assertEqual(countries[3].sub_national_regions, ['RegionD1', 'RegionD2', 'RegionD3'])

    def test_load_countries_non_existent_file(self):
        countries = load_countries_data('non_existent_countries.csv')
        self.assertEqual(len(countries), 0)

    def test_load_countries_empty_csv(self):
        countries = load_countries_data(self.empty_csv_path)
        self.assertEqual(len(countries), 0)

    def test_load_countries_missing_mandatory_fields(self):
        # The loading function skips rows with missing name or iso_code and prints a message.
        # We expect 0 countries to be loaded from this file.
        countries = load_countries_data(self.missing_fields_csv_path)
        self.assertEqual(len(countries), 0) 

    def test_load_countries_varied_data_handling(self):
        countries = load_countries_data(self.varied_data_csv_path)
        self.assertEqual(len(countries), 3)
        
        # CountryG: 'FalSe' for key_market
        self.assertEqual(countries[0].name, 'CountryG')
        self.assertFalse(countries[0].key_market)
        self.assertEqual(countries[0].sub_national_regions, ['RegionG1'])

        # CountryH: 'Yes' for key_market (invalid, should default to False)
        self.assertEqual(countries[1].name, 'CountryH')
        self.assertFalse(countries[1].key_market)
        self.assertEqual(countries[1].sub_national_regions, ['RegionH1'])

        # CountryI: Regions with extra spaces
        self.assertEqual(countries[2].name, 'CountryI')
        self.assertTrue(countries[2].key_market)
        self.assertEqual(countries[2].sub_national_regions, ['RegionI1', 'RegionI2'])

class TestLoadGridArchitecturesData(unittest.TestCase):
    def setUp(self):
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)

        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_grid_architectures.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_grid_architectures.csv')
        self.missing_fields_csv_path = os.path.join(self.test_data_fdn_dir, 'missing_fields_grid_architectures.csv')

        self.csv_header = ['region_name', 'transmission_constraints', 'stability_requirements', 'interconnection_patterns']

        sample_valid_rows = [
            self.csv_header,
            ['RegionAlpha', 'ConstraintAlpha', 'RequirementAlpha', 'PatternAlpha'],
            ['RegionBeta', 'ConstraintBeta', 'RequirementBeta', 'PatternBeta']
        ]
        self._create_csv_file(self.valid_csv_path, sample_valid_rows)
        self._create_csv_file(self.empty_csv_path, [self.csv_header])

        missing_fields_rows = [
            self.csv_header,
            ['', 'ConstraintGamma', 'RequirementGamma', 'PatternGamma'], # Missing region_name
            ['RegionDelta', '', 'RequirementDelta', 'PatternDelta'],    # Missing transmission_constraints
            ['RegionEpsilon', 'ConstraintEpsilon', '', 'PatternEpsilon'],# Missing stability_requirements
            ['RegionZeta', 'ConstraintZeta', 'RequirementZeta', '']      # Missing interconnection_patterns
        ]
        self._create_csv_file(self.missing_fields_csv_path, missing_fields_rows)

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def tearDown(self):
        files_to_remove = [
            self.valid_csv_path, self.empty_csv_path, self.missing_fields_csv_path
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        # Basic cleanup for potentially created directories
        if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
            try: os.rmdir(self.test_data_fdn_dir)
            except OSError: pass # Might fail if other test classes created files
        if os.path.exists(self.test_data_root_dir) and not os.listdir(self.test_data_root_dir):
            try: os.rmdir(self.test_data_root_dir)
            except OSError: pass # Might fail if other test classes created files

    def test_load_valid_grid_architectures_data(self):
        architectures = load_grid_architectures_data(self.valid_csv_path)
        self.assertEqual(len(architectures), 2)
        self.assertEqual(architectures[0].region_name, 'RegionAlpha')
        self.assertEqual(architectures[0].transmission_constraints, 'ConstraintAlpha')
        self.assertEqual(architectures[0].stability_requirements, 'RequirementAlpha')
        self.assertEqual(architectures[0].interconnection_patterns, 'PatternAlpha')
        self.assertEqual(architectures[1].region_name, 'RegionBeta')

    def test_load_grid_architectures_non_existent_file(self):
        architectures = load_grid_architectures_data('non_existent_grid_architectures.csv')
        self.assertEqual(len(architectures), 0)

    def test_load_grid_architectures_empty_csv(self):
        architectures = load_grid_architectures_data(self.empty_csv_path)
        self.assertEqual(len(architectures), 0)

    def test_load_grid_architectures_missing_mandatory_fields(self):
        # The loading function skips rows with any missing mandatory field and prints a message.
        # Expect 0 architectures to be loaded from this file.
        architectures = load_grid_architectures_data(self.missing_fields_csv_path)
        self.assertEqual(len(architectures), 0)


class TestLoadClimateZonesData(unittest.TestCase):
    def setUp(self):
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)

        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_climate_zones.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_climate_zones.csv')
        self.invalid_data_csv_path = os.path.join(self.test_data_fdn_dir, 'invalid_climate_zones.csv')

        self.csv_header = ['name', 'resolution_minutes', 'data_source_path']

        sample_valid_rows = [
            self.csv_header,
            ['ZoneAlpha', '60', 'path/to/alpha.csv'],
            ['ZoneBeta', '5', ''], # Empty data_source_path
            ['ZoneGamma', '30', None]  # Missing data_source_path value in CSV row writing
        ]
        # For None in CSV, we write an empty string if csv.writer is used directly with list of lists.
        # DictWriter would handle a missing key as None if the key wasn't in a particular dict row.
        # Here, we'll simulate it as an empty string for data_source_path if source row had None for it.
        self._create_csv_file(self.valid_csv_path, [
            self.csv_header,
            ['ZoneAlpha', '60', 'path/to/alpha.csv'],
            ['ZoneBeta', '5', ''],
            ['ZoneGamma', '30', ''] # Simulating None or empty for optional field
        ])
        self._create_csv_file(self.empty_csv_path, [self.csv_header])

        invalid_data_rows = [
            self.csv_header,
            ['', '60', 'path/to/delta.csv'],    # Missing name
            ['ZoneEpsilon', 'bad_int', 'path/to/epsilon.csv'], # Invalid resolution_minutes
            ['ZoneOmega', '15'] # Missing data_source_path column entirely in some CSV writing tools (though DictReader handles)
                               # Here, ensure the column exists but is empty for a test if needed, or test with fewer columns.
                               # For this test, assuming header implies column exists for DictReader.
        ]
        self._create_csv_file(self.invalid_data_csv_path, invalid_data_rows)

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def tearDown(self):
        files_to_remove = [
            self.valid_csv_path, self.empty_csv_path, self.invalid_data_csv_path
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        # Basic cleanup, trying to remove test_data_fdn_dir if it's empty
        # This might fail if other test classes have not cleaned up their files yet, which is fine.
        try:
            if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
                os.rmdir(self.test_data_fdn_dir)
            # Similarly for test_data_root_dir, though less likely to be empty if other test modules exist
            if os.path.exists(self.test_data_root_dir) and not os.listdir(self.test_data_root_dir):
                 os.rmdir(self.test_data_root_dir)
        except OSError: # Silently pass if directory removal fails (e.g., not empty)
            pass 

    def test_load_valid_climate_zones_data(self):
        zones = load_climate_zones_data(self.valid_csv_path)
        self.assertEqual(len(zones), 3)
        self.assertEqual(zones[0].name, 'ZoneAlpha')
        self.assertEqual(zones[0].resolution_minutes, 60)
        self.assertEqual(zones[0].data_source_path, 'path/to/alpha.csv')
        
        self.assertEqual(zones[1].name, 'ZoneBeta')
        self.assertEqual(zones[1].resolution_minutes, 5)
        self.assertIsNone(zones[1].data_source_path) # Empty string becomes None

        self.assertEqual(zones[2].name, 'ZoneGamma')
        self.assertEqual(zones[2].resolution_minutes, 30)
        self.assertIsNone(zones[2].data_source_path) # Empty string becomes None

    def test_load_climate_zones_non_existent_file(self):
        zones = load_climate_zones_data('non_existent_climate_zones.csv')
        self.assertEqual(len(zones), 0)

    def test_load_climate_zones_empty_csv(self):
        zones = load_climate_zones_data(self.empty_csv_path)
        self.assertEqual(len(zones), 0)

    def test_load_climate_zones_invalid_data(self):
        # Covers missing name and invalid resolution_minutes.
        # The loading function skips these rows and prints messages.
        zones = load_climate_zones_data(self.invalid_data_csv_path)
        # The row with missing 'data_source_path' column will load if name and resolution are valid.
        # DictReader will return None for a field not in a row if fieldnames are provided to constructor, or if it's just not in the row.
        # If 'data_source_path' is in fieldnames (from header) but not in a row, row.get('data_source_path') is None.
        # Here, the third row in invalid_data_rows has 'ZoneOmega', '15' - data_source_path will be None.
        self.assertEqual(len(zones), 1) 
        self.assertEqual(zones[0].name, 'ZoneOmega')
        self.assertEqual(zones[0].resolution_minutes, 15)
        self.assertIsNone(zones[0].data_source_path)

if __name__ == '__main__':
    # This allows running the tests directly from this file
    unittest.main()
