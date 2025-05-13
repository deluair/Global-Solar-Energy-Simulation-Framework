# This file makes 'data_management' a Python package
from .load_foundation_data import load_countries_data, load_pv_technologies_data, load_storage_technologies_data

__all__ = [
    'load_countries_data',
    'load_pv_technologies_data',
    'load_storage_technologies_data'
]
