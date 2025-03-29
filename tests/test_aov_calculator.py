import unittest
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from metrics.aov import AOVCalculator
from utils.customer_cache import CustomerCache

class TestAOVCalculator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.customer_cache = CustomerCache("test_customer_cache.json")
        self.aov_calculator = AOVCalculator(self.customer_cache)
        
        # Load mock data
        test_dir = Path(__file__).parent
        with open(test_dir / "mock_data" / "sample_orders.json", "r") as f:
            self.mock_orders = json.load(f)
            
        # Set test date range
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 12, 31)
    
    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists("test_customer_cache.json"):
            os.remove("test_customer_cache.json")
    
    def test_calculate_monthly_metrics_with_empty_data(self):
        """Test calculation with no orders."""
        result = self.aov_calculator.calculate_monthly_metrics([], self.start_date, self.end_date)
        
        # Check that the structure is correct
        self.assertIn('months', result)
        self.assertIn('totals', result)
        
        # Check that we have all 12 months
        self.assertEqual(len(result['months']), 12)
        
        # Verify all metrics are zero
        self.assertEqual(result['totals']['all_customers']['order_count'], 0)
        self.assertEqual(result['totals']['all_customers']['aov'], 0.0)
    
    def test_calculate_monthly_metrics_with_mixed_customers(self):
        """Test calculation with mix of new and returning customers."""
        result = self.aov_calculator.calculate_monthly_metrics(
            self.mock_orders, self.start_date, self.end_date
        )
        
        # Check total order count matches expected
        expected_order_count = len(self.mock_orders)
        self.assertEqual(result['totals']['all_customers']['order_count'], expected_order_count)
        
        # Check January metrics (based on mock data)
        jan_key = next((k for k in result['months'].keys() if '2024-01' in k), None)
        if jan_key:
            jan_metrics = result['months'][jan_key]['metrics']
            self.assertGreater(jan_metrics['new_customers']['order_count'], 0)
            self.assertGreater(jan_metrics['new_customers']['aov'], 0)
            
            # Verify percentage calculation exists
            self.assertIn('percent_change', jan_metrics['new_customers'])
    
    def test_percent_change_calculation(self):
        """Test that percent change calculations are correct."""
        result = self.aov_calculator.calculate_monthly_metrics(
            self.mock_orders, self.start_date, self.end_date
        )
        
        # Get the overall average AOV
        avg_aov = result['totals']['new_customers']['aov']
        
        # Calculate expected percent change for a specific month
        # (Only check months with data)
        for month_key, month_data in result['months'].items():
            metrics = month_data['metrics']
            if metrics['new_customers']['order_count'] > 0:
                month_aov = metrics['new_customers']['aov']
                expected_pct = (month_aov - avg_aov) / avg_aov if avg_aov else 0
                actual_pct = metrics['new_customers']['percent_change']
                
                # Allow for small floating point differences
                self.assertAlmostEqual(actual_pct, expected_pct, places=5)
                break  # Just check one month with data
    
    def test_new_vs_returning_customer_classification(self):
        """Test that customers are correctly classified as new or returning."""
        result = self.aov_calculator.calculate_monthly_metrics(
            self.mock_orders, self.start_date, self.end_date
        )
        
        # Verify January has a new customer (first order from customer1)
        jan_key = next((k for k in result['months'].keys() if '2024-01' in k), None)
        self.assertEqual(result['months'][jan_key]['metrics']['new_customers']['order_count'], 1)
        self.assertEqual(result['months'][jan_key]['metrics']['returning_customers']['order_count'], 0)
        
        # Verify February has a returning customer (second order from customer1)
        feb_key = next((k for k in result['months'].keys() if '2024-02' in k), None)
        self.assertEqual(result['months'][feb_key]['metrics']['new_customers']['order_count'], 0)
        self.assertEqual(result['months'][feb_key]['metrics']['returning_customers']['order_count'], 1)
        
        # Verify March has a new customer (first order from customer2)
        mar_key = next((k for k in result['months'].keys() if '2024-03' in k), None)
        self.assertEqual(result['months'][mar_key]['metrics']['new_customers']['order_count'], 1)
        self.assertEqual(result['months'][mar_key]['metrics']['returning_customers']['order_count'], 0)
        
        # Verify April has a returning customer (second order from customer2)
        apr_key = next((k for k in result['months'].keys() if '2024-04' in k), None)
        self.assertEqual(result['months'][apr_key]['metrics']['new_customers']['order_count'], 0)
        self.assertEqual(result['months'][apr_key]['metrics']['returning_customers']['order_count'], 1)
        
        # Verify June has a new customer (first order from customer3)
        jun_key = next((k for k in result['months'].keys() if '2024-06' in k), None)
        self.assertEqual(result['months'][jun_key]['metrics']['new_customers']['order_count'], 1)
        self.assertEqual(result['months'][jun_key]['metrics']['returning_customers']['order_count'], 0)

    def test_refund_handling(self):
        """Test that refunds are properly included in revenue calculations."""
        result = self.aov_calculator.calculate_monthly_metrics(
            self.mock_orders, self.start_date, self.end_date
        )
        
        # February order has a $20 refund on a $150 order
        feb_key = next((k for k in result['months'].keys() if '2024-02' in k), None)
        feb_metrics = result['months'][feb_key]['metrics']
        
        # Verify total_revenue includes refunds (150 + 20 = 170)
        self.assertEqual(feb_metrics['returning_customers']['total_revenue'], 170.0)
        self.assertEqual(feb_metrics['returning_customers']['total_sales'], 150.0)
        self.assertEqual(feb_metrics['returning_customers']['total_refunds'], 20.0)
        
        # April order has a $50 refund on a $200 order
        apr_key = next((k for k in result['months'].keys() if '2024-04' in k), None)
        apr_metrics = result['months'][apr_key]['metrics']
        
        # Verify total_revenue includes refunds (200 + 50 = 250)
        self.assertEqual(apr_metrics['returning_customers']['total_revenue'], 250.0)
        self.assertEqual(apr_metrics['returning_customers']['total_sales'], 200.0)
        self.assertEqual(apr_metrics['returning_customers']['total_refunds'], 50.0)

if __name__ == '__main__':
    unittest.main() 