import unittest
from src.modules.economic_framework.market_model import MarketSimulator

class TestMarketSimulator(unittest.TestCase):
    def setUp(self):
        self.market_designs = {
            'TestRegionA': {
                'type': 'energy_only',
                'base_energy_price_usd_per_mwh': 50,
                'tou_factors': {'off_peak': 0.8, 'mid_peak': 1.0, 'on_peak': 1.5},
                'ancillary_services': {
                    'freq_control': {'price_usd_per_mw_year': 4000},
                    'voltage_support': {'price_usd_per_mw_year': 1500}
                }
            },
            'TestRegionB': {
                'type': 'capacity_market',
                'base_energy_price_usd_per_mwh': 60,
                # No TOU factors specified, should use default multiplier of 1
                'ancillary_services': {
                    'freq_control': {'price_usd_per_mw_year': 5500}
                }
            },
            'TestRegionC': {
                'type': 'energy_only',
                'base_energy_price_usd_per_mwh': 40,
                'tou_factors': {'peak': 2.0, 'off_peak_winter': 0.7}
                # No ancillary services specified
            }
        }
        self.simulator = MarketSimulator(market_designs=self.market_designs)

    def test_get_energy_price_with_tou(self):
        # TestRegionA: base 50, on_peak x1.5 -> 75
        price = self.simulator.get_energy_price(region='TestRegionA', time_of_day='on_peak')
        self.assertAlmostEqual(price, 75.0)

        # TestRegionA: base 50, mid_peak x1.0 -> 50
        price = self.simulator.get_energy_price(region='TestRegionA', time_of_day='mid_peak')
        self.assertAlmostEqual(price, 50.0)

        # TestRegionA: base 50, off_peak x0.8 -> 40
        price = self.simulator.get_energy_price(region='TestRegionA', time_of_day='off_peak')
        self.assertAlmostEqual(price, 40.0)

    def test_get_energy_price_no_tou_factors_defined(self):
        # TestRegionB: base 60, no TOU defined for 'on_peak', should use multiplier 1 -> 60
        price = self.simulator.get_energy_price(region='TestRegionB', time_of_day='on_peak')
        self.assertAlmostEqual(price, 60.0)

    def test_get_energy_price_specific_tou_factor_missing(self):
        # TestRegionC: base 40, 'super_peak' not in tou_factors, should use multiplier 1 -> 40
        price = self.simulator.get_energy_price(region='TestRegionC', time_of_day='super_peak')
        self.assertAlmostEqual(price, 40.0)

    def test_get_energy_price_unknown_region_with_default_base(self):
        # Unknown region, should use default_base_price (e.g., 30) and multiplier 1 -> 30
        price = self.simulator.get_energy_price(region='UnknownRegion', time_of_day='on_peak', default_base_price=30)
        self.assertAlmostEqual(price, 30.0)

    def test_get_energy_price_unknown_region_fallback_default_base(self):
        # Unknown region, should use built-in default_base_price (50 in method signature) and multiplier 1 -> 50
        price = self.simulator.get_energy_price(region='UnknownRegion', time_of_day='on_peak')
        self.assertAlmostEqual(price, 50.0)        

    def test_estimate_ancillary_revenue_service_exists(self):
        # TestRegionA, freq_control: 10 MW * $4000/MW/year = $40000
        revenue = self.simulator.estimate_ancillary_revenue(capacity_mw=10, service_type='freq_control', region='TestRegionA')
        self.assertAlmostEqual(revenue, 40000.0)

    def test_estimate_ancillary_revenue_service_not_in_region_config(self):
        # TestRegionC has no ancillary services defined, so revenue for 'freq_control' should be 0
        revenue = self.simulator.estimate_ancillary_revenue(capacity_mw=10, service_type='freq_control', region='TestRegionC')
        self.assertAlmostEqual(revenue, 0.0)

    def test_estimate_ancillary_revenue_specific_service_not_defined(self):
        # TestRegionA has 'freq_control' but not 'black_start', revenue should be 0
        revenue = self.simulator.estimate_ancillary_revenue(capacity_mw=10, service_type='black_start', region='TestRegionA')
        self.assertAlmostEqual(revenue, 0.0)

    def test_estimate_ancillary_revenue_unknown_region(self):
        # Unknown region, no ancillary services defined, revenue should be 0
        revenue = self.simulator.estimate_ancillary_revenue(capacity_mw=10, service_type='freq_control', region='UnknownRegion')
        self.assertAlmostEqual(revenue, 0.0)

if __name__ == '__main__':
    unittest.main()
