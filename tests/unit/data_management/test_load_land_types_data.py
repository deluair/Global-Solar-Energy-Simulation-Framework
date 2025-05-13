import unittest
import os
import csv
import sys
from typing import List, Any

# Add project root to sys.path to allow direct import of src modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

from src.modules.foundation_elements.data_models import LandType
from src.data_management.load_foundation_data import load_land_types_data

class TestLoadLandTypesData(unittest.TestCase):
    def setUp(self):
        self.test_data_root_dir = os.path.join(PROJECT_ROOT, 'tests', 'test_data')
        self.test_data_fdn_dir = os.path.join(self.test_data_root_dir, 'foundation_elements')
        os.makedirs(self.test_data_fdn_dir, exist_ok=True)

        self.valid_csv_path = os.path.join(self.test_data_fdn_dir, 'valid_land_types.csv')
        self.empty_csv_path = os.path.join(self.test_data_fdn_dir, 'empty_land_types.csv')
        self.missing_fields_csv_path = os.path.join(self.test_data_fdn_dir, 'missing_fields_land_types.csv')

        self.csv_header = ['category_id', 'name', 'description']

        self._create_csv_file(self.valid_csv_path, [
            self.csv_header,
            ['URBAN', 'Urban Area', 'Densely populated residential and commercial areas.'],
            ['AGRIC', 'Agricultural Land', ''], 
            ['FOREST', 'Forestry Land', None] 
        ])
        
        self._create_csv_file(self.empty_csv_path, [self.csv_header])

        self._create_csv_file(self.missing_fields_csv_path, [
            self.csv_header,
            ['', 'No Category ID Land', 'Test description'], 
            ['NOCAT', '', 'Another test description'],       
            ['VALID_ID', 'Valid Name In Missing File', 'This one should load']
        ])

    def _create_csv_file(self, file_path: str, data: List[List[Any]]):
        processed_data = []
        for row in data:
            processed_data.append(['' if item is None else item for item in row])
        
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(processed_data)

    def tearDown(self):
        files_to_remove = [
            self.valid_csv_path, self.empty_csv_path, self.missing_fields_csv_path
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                os.remove(f_path)
        try:
            if os.path.exists(self.test_data_fdn_dir) and not os.listdir(self.test_data_fdn_dir):
                os.rmdir(self.test_data_fdn_dir)
        except OSError:
            pass # Directory might not be empty if other tests created files
        # We won't remove test_data_root_dir here as it's shared by other test files

    def test_load_valid_land_types_data(self):
        land_types = load_land_types_data(self.valid_csv_path)
        self.assertEqual(len(land_types), 3)
        self.assertEqual(land_types[0].category_id, 'URBAN')
        self.assertEqual(land_types[0].name, 'Urban Area')
        self.assertEqual(land_types[0].description, 'Densely populated residential and commercial areas.')
        
        self.assertEqual(land_types[1].category_id, 'AGRIC')
        self.assertEqual(land_types[1].name, 'Agricultural Land')
        self.assertIsNone(land_types[1].description)

        self.assertEqual(land_types[2].category_id, 'FOREST')
        self.assertEqual(land_types[2].name, 'Forestry Land')
        self.assertIsNone(land_types[2].description)

    def test_load_land_types_non_existent_file(self):
        land_types = load_land_types_data('non_existent_land_types.csv')
        self.assertEqual(len(land_types), 0)

    def test_load_land_types_empty_csv(self):
        land_types = load_land_types_data(self.empty_csv_path)
        self.assertEqual(len(land_types), 0)

    def test_load_land_types_missing_mandatory_fields(self):
        land_types = load_land_types_data(self.missing_fields_csv_path)
        self.assertEqual(len(land_types), 1) 
        self.assertEqual(land_types[0].category_id, 'VALID_ID')
        self.assertEqual(land_types[0].name, 'Valid Name In Missing File')
        self.assertEqual(land_types[0].description, 'This one should load')

if __name__ == '__main__':
    unittest.main()
