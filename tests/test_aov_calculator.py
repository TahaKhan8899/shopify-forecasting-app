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
        """Test that customers are correctly classified as new or returning based on the new rules."""
        # New definition:
        # - New customers: acquired in the current month
        # - Returning customers:
        #   - Recently acquired (acquired within the last 6 months)
        #   - Active non-recent (acquired more than 6 months ago and reordered within the last 6 months)
        
        result = self.aov_calculator.calculate_monthly_metrics(
            self.mock_orders, self.start_date, self.end_date
        )
        
        # Verify January has a new customer (first order from customer1 in January)
        jan_key = next((k for k in result['months'].keys() if '2024-01' in k), None)
        self.assertEqual(result['months'][jan_key]['metrics']['new_customers']['order_count'], 1)
        self.assertEqual(result['months'][jan_key]['metrics']['returning_customers']['order_count'], 0)
        
        # Verify February has a returning customer (second order from customer1, who was acquired within 6 months)
        feb_key = next((k for k in result['months'].keys() if '2024-02' in k), None)
        self.assertEqual(result['months'][feb_key]['metrics']['new_customers']['order_count'], 0)
        self.assertEqual(result['months'][feb_key]['metrics']['returning_customers']['order_count'], 1)
        
        # Verify March has a new customer (first order from customer2 in March)
        mar_key = next((k for k in result['months'].keys() if '2024-03' in k), None)
        self.assertEqual(result['months'][mar_key]['metrics']['new_customers']['order_count'], 1)
        self.assertEqual(result['months'][mar_key]['metrics']['returning_customers']['order_count'], 0)
        
        # Verify April has a returning customer (second order from customer2, who was acquired within 6 months)
        apr_key = next((k for k in result['months'].keys() if '2024-04' in k), None)
        self.assertEqual(result['months'][apr_key]['metrics']['new_customers']['order_count'], 0)
        self.assertEqual(result['months'][apr_key]['metrics']['returning_customers']['order_count'], 1)
        
        # Verify June has a new customer (first order from customer3 in June)
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

    def test_customer_type_determination(self):
        """Test the customer type determination logic with individual orders."""
        expected_classifications = {
            "1": "new_customers",     # Customer 1's first order in January
            "2": "returning_customers", # Customer 1's second order in February
            "3": "new_customers",     # Customer 2's first order in March
            "4": "returning_customers", # Customer 2's second order in April
            "5": "new_customers"      # Customer 3's first order in June
        }
        
        for order in self.mock_orders:
            order_id = order['id'].split('/')[-1]
            order_date = datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00'))
            month_start = datetime(order_date.year, order_date.month, 1)
            
            # Test the _determine_customer_type method directly
            actual_classification = self.aov_calculator._determine_customer_type(order, month_start)
            
            # Assert that the classification matches expectations
            self.assertEqual(
                actual_classification, 
                expected_classifications[order_id],
                f"Order {order_id} on {order_date.strftime('%Y-%m-%d')} was incorrectly classified as {actual_classification}"
            )
    
    def test_six_month_classification_logic(self):
        """Test the six-month window rules for customer classification."""
        # Create a mock order that's a first-time order more than 6 months ago
        old_first_order = {
            "id": "gid://shopify/Order/101",
            "createdAt": "2023-06-15T12:00:00Z",  # 9 months before test period
            "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
            "totalRefundedSet": {"shopMoney": {"amount": "0.00", "currencyCode": "USD"}},
            "customer": {
                "id": "gid://shopify/Customer/101",
                "email": "old.customer@example.com",
                "orders": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Order/101",
                                "createdAt": "2023-06-15T12:00:00Z"
                            }
                        }
                    ]
                }
            }
        }
        
        # Recent order from the same customer (active non-recent customer)
        recent_order_from_old_customer = {
            "id": "gid://shopify/Order/102",
            "createdAt": "2024-03-15T12:00:00Z",  # Within the 6-month active window
            "totalPriceSet": {"shopMoney": {"amount": "150.00", "currencyCode": "USD"}},
            "totalRefundedSet": {"shopMoney": {"amount": "0.00", "currencyCode": "USD"}},
            "customer": {
                "id": "gid://shopify/Customer/101",
                "email": "old.customer@example.com",
                "orders": {
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Order/101",
                                "createdAt": "2023-06-15T12:00:00Z"
                            }
                        }
                    ]
                }
            }
        }
        
        # Add old order to cache first
        self.customer_cache.update_from_orders([old_first_order])
        
        # Test classification of the recent order
        march_start = datetime(2024, 3, 1)
        classification = self.aov_calculator._determine_customer_type(
            recent_order_from_old_customer, march_start
        )
        
        # Should be classified as "returning_customers" (active non-recent)
        self.assertEqual(classification, "returning_customers")
        
        # Make sure the old order itself would be classified as "new" in its own month
        june_start = datetime(2023, 6, 1)
        old_order_classification = self.aov_calculator._determine_customer_type(
            old_first_order, june_start
        )
        self.assertEqual(old_order_classification, "new_customers")
        
        # But it would be classified as "returning" if analyzed in a different month
        july_start = datetime(2023, 7, 1)
        old_order_diff_month = self.aov_calculator._determine_customer_type(
            old_first_order, july_start
        )
        self.assertEqual(old_order_diff_month, "returning_customers")

if __name__ == '__main__':
    unittest.main() 