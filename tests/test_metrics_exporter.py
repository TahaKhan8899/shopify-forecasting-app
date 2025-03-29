import unittest
import os
import csv
from datetime import datetime
from pathlib import Path
import shutil

from outputs.spreadsheet import MetricsExporter

class TestMetricsExporter(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_output_dir = "test_reports"
        if not os.path.exists(self.test_output_dir):
            os.makedirs(self.test_output_dir)
            
        self.exporter = MetricsExporter(self.test_output_dir)
        
        # Sample metrics data
        self.sample_monthly_metrics = {
            'period': {
                'start': '2024-01-01T00:00:00',
                'end': '2024-12-31T00:00:00'
            },
            'months': {
                '2024-01': {
                    'info': {
                        'key': '2024-01',
                        'name': 'January',
                        'year': 2024,
                        'month': 1,
                        'start_date': datetime(2024, 1, 1),
                        'end_date': datetime(2024, 1, 31),
                        'display': 'January 2024'
                    },
                    'metrics': {
                        'new_customers': {
                            'order_count': 1,
                            'total_sales': 100.0,
                            'total_refunds': 0.0,
                            'total_revenue': 100.0,
                            'aov': 100.0,
                            'percent_change': 0.25
                        },
                        'returning_customers': {
                            'order_count': 0,
                            'total_sales': 0.0,
                            'total_refunds': 0.0,
                            'total_revenue': 0.0,
                            'aov': 0.0,
                            'percent_change': None
                        },
                        'all_customers': {
                            'order_count': 1,
                            'total_sales': 100.0,
                            'total_refunds': 0.0,
                            'total_revenue': 100.0,
                            'aov': 100.0,
                        }
                    }
                },
                '2024-02': {
                    'info': {
                        'key': '2024-02',
                        'name': 'February',
                        'year': 2024,
                        'month': 2,
                        'start_date': datetime(2024, 2, 1),
                        'end_date': datetime(2024, 2, 29),
                        'display': 'February 2024'
                    },
                    'metrics': {
                        'new_customers': {
                            'order_count': 0,
                            'total_sales': 0.0,
                            'total_refunds': 0.0,
                            'total_revenue': 0.0,
                            'aov': 0.0,
                            'percent_change': None
                        },
                        'returning_customers': {
                            'order_count': 1,
                            'total_sales': 150.0,
                            'total_refunds': 20.0,
                            'total_revenue': 170.0,
                            'aov': 170.0,
                            'percent_change': 0.7
                        },
                        'all_customers': {
                            'order_count': 1,
                            'total_sales': 150.0,
                            'total_refunds': 20.0,
                            'total_revenue': 170.0,
                            'aov': 170.0,
                        }
                    }
                }
            },
            'totals': {
                'new_customers': {
                    'order_count': 1,
                    'total_sales': 100.0,
                    'total_refunds': 0.0,
                    'total_revenue': 100.0,
                    'aov': 100.0,
                    'percent_change': 0.0
                },
                'returning_customers': {
                    'order_count': 1,
                    'total_sales': 150.0,
                    'total_refunds': 20.0,
                    'total_revenue': 170.0,
                    'aov': 170.0,
                    'percent_change': 0.0
                },
                'all_customers': {
                    'order_count': 2,
                    'total_sales': 250.0,
                    'total_refunds': 20.0,
                    'total_revenue': 270.0,
                    'aov': 135.0
                }
            }
        }
        
        # Set date range for testing
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 12, 31)
    
    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
    
    def test_export_monthly_metrics_to_csv(self):
        """Test that monthly metrics CSV export works correctly."""
        # Export the metrics to CSV
        csv_path = self.exporter.export_monthly_metrics_to_csv(
            self.sample_monthly_metrics, 
            self.start_date, 
            self.end_date
        )
        
        # Verify file exists
        self.assertTrue(os.path.exists(csv_path))
        
        # Read the CSV and check content
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Check header row
            self.assertEqual(len(rows[0]), 13)  # 11 regular columns + 2 new % columns
            
            # Verify % columns are in the right position
            self.assertEqual(rows[0][6], '%')  # After new customer AOV
            self.assertEqual(rows[0][12], '%')  # After returning customer AOV
            
            # Check data rows
            # In our test data we have 2 months (January and February) plus the totals row
            self.assertGreater(len(rows), 2)  # At least header + 2 data rows
            
            # Check January row
            jan_row = next((row for row in rows if 'January 2024' in row[0]), None)
            self.assertIsNotNone(jan_row, "January row not found in CSV data")
            
            if jan_row:
                # Check January values
                self.assertEqual(jan_row[5], '$100.00')  # New customer AOV
                self.assertEqual(jan_row[6], '25.00%')   # New customer % change
            
            # Check February row - returning customer values
            feb_row = next((row for row in rows if 'February 2024' in row[0]), None)
            self.assertIsNotNone(feb_row, "February row not found in CSV data")
            
            if feb_row:
                self.assertEqual(feb_row[11], '$170.00')  # Returning customer AOV
                self.assertEqual(feb_row[12], '70.00%')   # Returning customer % change
            
            # Check totals row
            totals_row = next((row for row in rows if row[0] == 'Total'), None)
            self.assertIsNotNone(totals_row, "Totals row not found in CSV data")
    
    def test_handling_zero_orders(self):
        """Test that months with zero orders show empty percent values."""
        csv_path = self.exporter.export_monthly_metrics_to_csv(
            self.sample_monthly_metrics, 
            self.start_date, 
            self.end_date
        )
        
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Check January row - should have empty value for returning customer percent
            jan_row = next((row for row in rows if 'January 2024' in row[0]), None)
            self.assertIsNotNone(jan_row, "January row not found in CSV data")
            
            if jan_row:
                self.assertEqual(jan_row[12], '')  # Empty returning customer percent
            
            # Check February row - should have empty value for new customer percent
            feb_row = next((row for row in rows if 'February 2024' in row[0]), None)
            self.assertIsNotNone(feb_row, "February row not found in CSV data")
            
            if feb_row:
                self.assertEqual(feb_row[6], '')   # Empty new customer percent
    
    def test_csv_format_matches_requirements(self):
        """Test that the CSV format matches the required format shown in the image."""
        csv_path = self.exporter.export_monthly_metrics_to_csv(
            self.sample_monthly_metrics, 
            self.start_date, 
            self.end_date
        )
        
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Check header row columns
            header = rows[0]
            expected_headers = [
                'Last 12 Months',
                'New Customer "Total Sales"',
                'New Customer "Returns"',
                'Total New Customer Revenue',
                'New Customer Orders',
                'New Customer AOV',
                '%',
                'Returning Customer "Total Sales"',
                'Returning Customer "Returns"',
                'Total Returning Customer Revenue',
                'Returning Customer Orders',
                'Returning Customer AOV',
                '%'
            ]
            self.assertEqual(header, expected_headers)
            
            # Check totals row is labeled correctly
            totals_row = next((row for row in rows if row[0] == 'Total'), None)
            self.assertIsNotNone(totals_row, "Totals row not found in CSV data")
            
            # Verify empty percent cells for totals row
            if totals_row:
                self.assertEqual(totals_row[6], '')
                self.assertEqual(totals_row[12], '')
    
    def test_detailed_orders_export(self):
        """Test that detailed orders are exported correctly."""
        # Sample orders
        sample_orders = [
            {
                "id": "gid://shopify/Order/1",
                "createdAt": "2024-01-15T12:00:00Z",
                "totalPriceSet": {
                    "shopMoney": {
                        "amount": "100.00",
                        "currencyCode": "USD"
                    }
                },
                "totalRefundedSet": {
                    "shopMoney": {
                        "amount": "20.00",
                        "currencyCode": "USD"
                    }
                },
                "customer": {
                    "id": "gid://shopify/Customer/1"
                }
            }
        ]
        
        # Customer types dictionary
        customer_types = {
            "gid://shopify/Customer/1": True  # New customer
        }
        
        # Export detailed orders
        csv_path = self.exporter.export_detailed_orders_to_csv(
            sample_orders,
            self.start_date,
            self.end_date,
            customer_types
        )
        
        # Verify file exists
        self.assertTrue(os.path.exists(csv_path))
        
        # Check content
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            
            # Should have header + 1 data row
            self.assertEqual(len(rows), 2)
            
            # Check data row values
            data_row = rows[1]
            self.assertEqual(data_row[0], 'gid://shopify/Order/1')  # Order ID
            self.assertEqual(data_row[3], 'New')                   # Customer type
            self.assertEqual(data_row[4], '$100.00')               # Sales value
            self.assertEqual(data_row[5], '$20.00')                # Refunded amount
            self.assertEqual(data_row[6], '$120.00')               # Total revenue

if __name__ == '__main__':
    unittest.main() 