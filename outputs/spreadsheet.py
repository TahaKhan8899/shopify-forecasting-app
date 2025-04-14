import os
import csv
from typing import Dict, List, Any
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetricsExporter:
    """
    Exports calculated metrics to CSV or other formats.
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize the metrics exporter.
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
    
    def format_filename(self, prefix: str, start_date: datetime, end_date: datetime) -> str:
        """
        Generate a filename for the output file.
        
        Args:
            prefix: String prefix for the filename
            start_date: Start date of the reporting period
            end_date: End date of the reporting period
        
        Returns:
            Formatted filename string
        """
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        return f"{prefix}_{start_str}_to_{end_str}.csv"
    
    def export_aov_to_csv(self, aov_metrics: Dict[str, Any], 
                          start_date: datetime, end_date: datetime,
                          filename: str = None) -> str:
        """
        Export AOV metrics to a CSV file in the requested format.
        
        Args:
            aov_metrics: Dictionary with AOV metrics
            start_date: Start date of the reporting period
            end_date: End date of the reporting period
            filename: Optional custom filename
            
        Returns:
            Path to the output file
        """
        # Generate filename if not provided
        if filename is None:
            filename = self.format_filename("aov_metrics", start_date, end_date)
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write period info
                writer.writerow([f'Last 12 Months: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'])
                writer.writerow([])  # Empty row for spacing
                
                # Write the metrics in the requested format (as a data table)
                # Write headers
                writer.writerow(['Metrics', 'Value'])
                
                # New Customer metrics
                writer.writerow(['New Customer "Total Sales"', f"${aov_metrics['new_customers']['total_sales']:.2f}"])
                writer.writerow(['New Customer "Returns"', f"${aov_metrics['new_customers']['total_refunds']:.2f}"])
                writer.writerow(['Total New Customer Revenue', f"${aov_metrics['new_customers']['total_revenue']:.2f}"])
                writer.writerow(['New Customer Orders', aov_metrics['new_customers']['order_count']])
                writer.writerow(['New Customer AOV', f"${aov_metrics['new_customers']['aov']:.2f}"])
                
                # Returning Customer metrics
                writer.writerow(['Returning Customer "Total Sales"', f"${aov_metrics['returning_customers']['total_sales']:.2f}"])
                writer.writerow(['Returning Customer "Returns"', f"${aov_metrics['returning_customers']['total_refunds']:.2f}"])
                writer.writerow(['Total Returning Customer Revenue', f"${aov_metrics['returning_customers']['total_revenue']:.2f}"])
                writer.writerow(['Returning Customer Orders', aov_metrics['returning_customers']['order_count']])
                writer.writerow(['Returning Customer AOV', f"${aov_metrics['returning_customers']['aov']:.2f}"])
                
                # Add totals as a summary
                writer.writerow([])  # Empty row for spacing
                writer.writerow(['Total Orders', aov_metrics['all_customers']['order_count']])
                writer.writerow(['Total Revenue', f"${aov_metrics['all_customers']['total_revenue']:.2f}"])
                writer.writerow(['Overall AOV', f"${aov_metrics['all_customers']['aov']:.2f}"])
                
                logger.info(f"AOV metrics exported to {filepath}")
                return filepath
                
        except IOError as e:
            logger.error(f"Error exporting AOV metrics to CSV: {str(e)}")
            raise
    
    def export_aov_to_horizontal_csv(self, aov_metrics: Dict[str, Any], 
                                    start_date: datetime, end_date: datetime,
                                    filename: str = None) -> str:
        """
        Export AOV metrics to a CSV file in a horizontal layout.
        
        Args:
            aov_metrics: Dictionary with AOV metrics
            start_date: Start date of the reporting period
            end_date: End date of the reporting period
            filename: Optional custom filename
            
        Returns:
            Path to the output file
        """
        if filename is None:
            filename = self.format_filename("aov_metrics_horizontal", start_date, end_date)
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([f'Last 12 Months: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'])
                writer.writerow([])  # Spacing
                
                headers = [
                    'Last 12 Months',
                    'New Customer "Total Sales"',
                    'New Customer "Returns"',
                    'Total New Customer Revenue',
                    'New Customer Orders',
                    'New Customer AOV',
                    'Returning Customer "Total Sales"',
                    'Returning Customer "Returns"',
                    'Total Returning Customer Revenue',
                    'Returning Customer Orders',
                    'Returning Customer AOV'
                ]
                writer.writerow(headers)
                
                values = [
                    f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    f"${aov_metrics['new_customers']['total_sales']:.2f}",
                    f"${aov_metrics['new_customers']['total_refunds']:.2f}",
                    f"${aov_metrics['new_customers']['total_revenue']:.2f}",
                    aov_metrics['new_customers']['order_count'],
                    f"${aov_metrics['new_customers']['aov']:.2f}",
                    f"${aov_metrics['returning_customers']['total_sales']:.2f}",
                    f"${aov_metrics['returning_customers']['total_refunds']:.2f}",
                    f"${aov_metrics['returning_customers']['total_revenue']:.2f}",
                    aov_metrics['returning_customers']['order_count'],
                    f"${aov_metrics['returning_customers']['aov']:.2f}"
                ]
                writer.writerow(values)
                
                logger.info(f"Horizontal AOV metrics exported to {filepath}")
                return filepath
                
        except IOError as e:
            logger.error(f"Error exporting horizontal AOV metrics to CSV: {str(e)}")
            raise
            
    def export_monthly_metrics_to_csv(self, monthly_metrics: Dict[str, Any], 
                                      start_date: datetime, end_date: datetime,
                                      filename: str = None) -> str:
        """
        Export monthly metrics to a CSV file in the specified format.
        
        Args:
            monthly_metrics: Dictionary with monthly metrics data
            start_date: Start date of the period
            end_date: End date of the period
            filename: Optional custom filename
            
        Returns:
            Path to the output file
        """
        if filename is None:
            filename = self.format_filename("monthly_metrics", start_date, end_date)
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                headers = [
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
                writer.writerow(headers)
                
                sorted_months = sorted(monthly_metrics['months'].items(), 
                                       key=lambda x: (x[1]['info']['year'], x[1]['info']['month']))
                
                for month_key, month_data in sorted_months:
                    month_info = month_data['info']
                    month_metrics = month_data['metrics']
                    new_customer_percent = month_metrics['new_customers'].get('percent_change')
                    returning_customer_percent = month_metrics['returning_customers'].get('percent_change')
                    
                    new_customer_percent_str = f"{new_customer_percent * 100:.2f}%" if new_customer_percent is not None else ""
                    returning_customer_percent_str = f"{returning_customer_percent * 100:.2f}%" if returning_customer_percent is not None else ""
                    
                    row = [
                        month_info['display'],
                        f"${month_metrics['new_customers']['total_sales']:.2f}",
                        f"${month_metrics['new_customers']['total_refunds']:.2f}",
                        f"${month_metrics['new_customers']['total_revenue']:.2f}",
                        month_metrics['new_customers']['order_count'],
                        f"${month_metrics['new_customers']['aov']:.2f}",
                        new_customer_percent_str,
                        f"${month_metrics['returning_customers']['total_sales']:.2f}",
                        f"${month_metrics['returning_customers']['total_refunds']:.2f}",
                        f"${month_metrics['returning_customers']['total_revenue']:.2f}",
                        month_metrics['returning_customers']['order_count'],
                        f"${month_metrics['returning_customers']['aov']:.2f}",
                        returning_customer_percent_str
                    ]
                    writer.writerow(row)
                
                totals_row = [
                    "Total",
                    f"${monthly_metrics['totals']['new_customers']['total_sales']:.2f}",
                    f"${monthly_metrics['totals']['new_customers']['total_refunds']:.2f}",
                    f"${monthly_metrics['totals']['new_customers']['total_revenue']:.2f}",
                    monthly_metrics['totals']['new_customers']['order_count'],
                    f"${monthly_metrics['totals']['new_customers']['aov']:.2f}",
                    "",
                    f"${monthly_metrics['totals']['returning_customers']['total_sales']:.2f}",
                    f"${monthly_metrics['totals']['returning_customers']['total_refunds']:.2f}",
                    f"${monthly_metrics['totals']['returning_customers']['total_revenue']:.2f}",
                    monthly_metrics['totals']['returning_customers']['order_count'],
                    f"${monthly_metrics['totals']['returning_customers']['aov']:.2f}",
                    ""
                ]
                writer.writerow(totals_row)
                
                logger.info(f"Monthly metrics exported to {filepath}")
                return filepath
                
        except IOError as e:
            logger.error(f"Error exporting monthly metrics to CSV: {str(e)}")
            raise
    
    def export_detailed_orders_to_csv(self, orders: List[Dict], 
                                      start_date: datetime, end_date: datetime,
                                      customer_types: Dict[str, bool] = None) -> str:
        """
        Export detailed order data to a CSV file.
        
        Args:
            orders: List of order dictionaries from Shopify API
            start_date: Start date of the reporting period
            end_date: End date of the reporting period
            customer_types: Mapping of customer IDs to True (New) or False (Returning)
            
        Returns:
            Path to the output file
        """
        filename = self.format_filename("detailed_orders", start_date, end_date)
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'Order ID', 'Date', 'Customer ID', 'Customer Type',
                    'Sales Value', 'Refunded Amount', 'Total Revenue', 'Notes'
                ])
                
                for order in orders:
                    try:
                        order_id = order.get('id', 'Unknown')
                        order_date = order.get('createdAt', 'Unknown')
                        customer_id = 'None'
                        customer_type = 'Unknown'
                        if order.get('customer') and order['customer'].get('id'):
                            customer_id = order['customer']['id']
                            if customer_types and customer_id in customer_types:
                                customer_type = 'New' if customer_types[customer_id] else 'Returning'
                        
                        sales_value = float(order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0.0))
                        refunded = float(order.get('totalRefundedSet', {}).get('shopMoney', {}).get('amount', 0.0))
                        total_revenue = sales_value + refunded
                        notes = "Includes refunded amount" if refunded > 0 else ""
                        
                        writer.writerow([
                            order_id,
                            order_date,
                            customer_id,
                            customer_type,
                            f"${sales_value:.2f}",
                            f"${refunded:.2f}",
                            f"${total_revenue:.2f}",
                            notes
                        ])
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Error processing order for detailed export: {str(e)}")
                
                logger.info(f"Detailed order data exported to {filepath}")
                return filepath
                
        except IOError as e:
            logger.error(f"Error exporting detailed order data to CSV: {str(e)}")
            raise

    def export_recent_repeat_report(self, report_rows: List[Dict[str, Any]], filename: str = None) -> str:
        """
        Export the "Assist- Recent Customer Repeat" report to a CSV file.
        Each row in report_rows should be a dictionary with keys:
          - "Cohort Month" (e.g. "January 2025")
          - "New Customers"
          - "Orders Month0", "RR% Month0", ..., "Orders Month6", "RR% Month6"
        
        Args:
            report_rows: List of dictionaries with the repeat report data.
            filename: Optional custom filename; defaults to "Assist- Recent Customer Repeat.csv"
            
        Returns:
            Path to the output file.
        """
        if filename is None:
            filename = "Assist- Recent Customer Repeat.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        if not report_rows:
            logger.info("No data provided for the Recent Customer Repeat report.")
            return filepath
        
        # Determine header order from the keys of the first row.
        fieldnames = list(report_rows[0].keys())
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in report_rows:
                    writer.writerow(row)
            logger.info(f"Recent Customer Repeat report exported to {filepath}")
            return filepath
        except IOError as e:
            logger.error(f"Error exporting Recent Customer Repeat report to CSV: {str(e)}")
            raise
    def export_active_non_recent_report(self, report_data: List[Dict], filename: str) -> str:
        """Export Active Non-Recent Repeat report"""
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'Initial Order Prior to...',
                'Re-Ordered Between',
                'Active Non-Recent Customers',
                'Time',
                'Active Non-Recent Customer Orders (L30)',
                'RR %'
            ])
            writer.writeheader()
            writer.writerows(report_data)
        
        return filepath
            
            