import os
import argparse
from datetime import datetime, timedelta
import logging
import sys
from typing import Tuple
from dotenv import load_dotenv

from shopify.api import ShopifyAPI
from metrics.aov import AOVCalculator
from outputs.spreadsheet import MetricsExporter
from utils.customer_cache import CustomerCache

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")

def parse_month(month_str: str) -> Tuple[datetime, datetime]:
    """
    Parse a month string (YYYY-MM) and return the start and end dates
    for the last 12 months ending at that month.
    
    Args:
        month_str: Month in format YYYY-MM
        
    Returns:
        Tuple of start_date, end_date for the 12-month period
    """
    try:
        # Parse the end month
        year, month = map(int, month_str.split('-'))
        
        # Last day of the specified month
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1
            
        end_date = datetime(next_month_year, next_month, 1) - timedelta(days=1)
        
        # Calculate start date: 12 months before the start of the specified month
        # (not the end month)
        start_date = datetime(year - 1, month, 1)
        
        return start_date, end_date
    except (ValueError, IndexError) as e:
        logger.error(f"Invalid month format: {month_str}. Use YYYY-MM format. Error: {str(e)}")
        sys.exit(1)

def get_previous_month_dates() -> tuple:
    """
    Get start and end dates for the previous month.
    
    Returns:
        Tuple of (start_date, end_date) for the previous month
    """
    today = datetime.now()
    
    # Get the first day of the current month
    first_day_of_current_month = datetime(today.year, today.month, 1)
    
    # Subtract one day to get the last day of the previous month
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    
    # Get the first day of the previous month
    first_day_of_previous_month = datetime(
        last_day_of_previous_month.year,
        last_day_of_previous_month.month,
        1
    )
    
    return first_day_of_previous_month, last_day_of_previous_month

def run_aov_report(month: str = None, year: int = None, month_num: int = None, is_twelve_month: bool = False, start_date_str: str = None, end_date_str: str = None):
    """
    Run an AOV report for a specific month or year
    
    Args:
        month: Month in format YYYY-MM (e.g., 2023-01 for January 2023)
        year: Year for the report
        month_num: Month number (1-12) for the report
        is_twelve_month: Whether this is a 12-month report
        start_date_str: Custom start date in YYYY-MM-DD format
        end_date_str: Custom end date in YYYY-MM-DD format
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize Shopify API with environment variables
    domain = os.getenv('SHOPIFY_STORE_DOMAIN')
    api_token = os.getenv('SHOPIFY_API_TOKEN')
    
    if not domain or not api_token:
        logger.error("Missing required environment variables: SHOPIFY_STORE_DOMAIN or SHOPIFY_API_TOKEN")
        print("Error: Missing Shopify API credentials. Please check your .env file.")
        sys.exit(1)
    
    # Initialize Shopify API
    shopify_api = ShopifyAPI(domain, api_token)
    
    # Determine date range based on input parameters
    if start_date_str and end_date_str:
        # Custom date range
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            
            if end_date < start_date:
                logger.error(f"End date {end_date_str} is before start date {start_date_str}")
                print(f"Error: End date {end_date_str} is before start date {start_date_str}")
                sys.exit(1)
        except ValueError as e:
            logger.error(f"Invalid date format: {str(e)}")
            print(f"Error: {str(e)}")
            sys.exit(1)
    elif month:
        # For a specific month with YYYY-MM format
        try:
            if is_twelve_month:
                # Calculate 12-month period ending with the specified month
                start_date, end_date = parse_month(month)
            else:
                # Just for the single month specified
                year, month_num = map(int, month.split('-'))
                start_date = datetime(year, month_num, 1)
                
                # Calculate the last day of the month
                if month_num == 12:
                    next_month_year = year + 1
                    next_month = 1
                else:
                    next_month_year = year
                    next_month = month_num + 1
                    
                end_date = datetime(next_month_year, next_month, 1) - timedelta(days=1)
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid month format: {month}. Use YYYY-MM format. Error: {str(e)}")
            return
    elif year and month_num:
        # For a specific month in a given year
        start_date = datetime(year, month_num, 1)
        
        # Calculate the last day of the month
        if month_num == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month_num + 1
            
        end_date = datetime(next_month_year, next_month, 1) - timedelta(days=1)
    elif year:
        # For an entire year
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
    else:
        # Default to current month
        today = datetime.today()
        start_date = datetime(today.year, today.month, 1)
        
        # Calculate the last day of the current month
        if today.month == 12:
            next_month_year = today.year + 1
            next_month = 1
        else:
            next_month_year = today.year
            next_month = today.month + 1
        
        end_date = datetime(next_month_year, next_month, 1) - timedelta(days=1)
    
    # Log the date range
    logger.info(f"Running report for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Fetch orders for the period
    orders = shopify_api.fetch_all_orders(start_date, end_date)
    logger.info(f"Retrieved {len(orders)} orders for the period")
    
    if not orders:
        logger.warning("No orders found for the specified period")
        print(f"No orders found for period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        return
    
    # Initialize customer cache
    customer_cache = CustomerCache()
    
    # Initialize AOV calculator
    aov_calculator = AOVCalculator(customer_cache)
    
    # Update customer cache with new orders
    customer_cache.update_from_orders(orders)
    
    # Determine customer status for each order
    for order in orders:
        if order.get('customer') and order['customer'].get('id'):
            customer_id = order['customer']['id']
            order_date = datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00'))
            # Make timezone-naive for consistent comparisons
            order_date = order_date.replace(tzinfo=None)
            is_first_order = customer_cache.is_new_customer(customer_id, order_date)
            order['is_new_customer'] = is_first_order
    
    # Initialize metrics exporter
    exporter = MetricsExporter()
    
    # Process orders and calculate metrics
    if is_twelve_month:
        # Calculate monthly metrics for 12-month period
        monthly_metrics = aov_calculator.calculate_monthly_metrics(orders, start_date, end_date)
        
        # Export monthly metrics to CSV
        csv_path = exporter.export_monthly_metrics_to_csv(monthly_metrics, start_date, end_date)
        
        # Export detailed order data for reference
        detailed_csv = exporter.export_detailed_orders_to_csv(
            orders, start_date, end_date, 
            {order.get('customer', {}).get('id'): order.get('is_new_customer', False) 
             for order in orders if order.get('customer')}
        )
        
        # Display summary
        print(f"\n===== Monthly AOV Report ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) =====")
        print(f"Total months: {len(monthly_metrics['months'])}")
        print(f"Total orders processed: {monthly_metrics['totals']['all_customers']['order_count']}")
        print(f"Overall new customer AOV: ${monthly_metrics['totals']['new_customers']['aov']:.2f}")
        print(f"Overall returning customer AOV: ${monthly_metrics['totals']['returning_customers']['aov']:.2f}")
        print(f"Overall AOV: ${monthly_metrics['totals']['all_customers']['aov']:.2f}")
        print(f"Report saved to: {csv_path}")
        print(f"Detailed order data saved to: {detailed_csv}")
        
    else:
        # Calculate aggregate metrics for the period
        aov_metrics = aov_calculator.calculate_monthly_aov(orders, start_date, end_date)
        
        # Export metrics to CSV
        csv_path = exporter.export_aov_to_csv(aov_metrics, start_date, end_date)
        
        # Export detailed order data for reference
        detailed_csv = exporter.export_detailed_orders_to_csv(
            orders, start_date, end_date, 
            {order.get('customer', {}).get('id'): order.get('is_new_customer', False) 
             for order in orders if order.get('customer')}
        )
        
        # Display summary
        print(f"\n===== AOV Report ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}) =====")
        print(f"Total orders processed: {aov_metrics['all_customers']['order_count']}")
        print(f"New customer orders: {aov_metrics['new_customers']['order_count']}")
        print(f"New customer total sales: ${aov_metrics['new_customers']['total_sales']:.2f}")
        print(f"New customer returns: ${aov_metrics['new_customers']['total_refunds']:.2f}")
        print(f"New customer revenue: ${aov_metrics['new_customers']['total_revenue']:.2f}")
        print(f"New customer AOV: ${aov_metrics['new_customers']['aov']:.2f}")
        print(f"Returning customer orders: {aov_metrics['returning_customers']['order_count']}")
        print(f"Returning customer total sales: ${aov_metrics['returning_customers']['total_sales']:.2f}")
        print(f"Returning customer returns: ${aov_metrics['returning_customers']['total_refunds']:.2f}")
        print(f"Returning customer revenue: ${aov_metrics['returning_customers']['total_revenue']:.2f}")
        print(f"Returning customer AOV: ${aov_metrics['returning_customers']['aov']:.2f}")
        print(f"Overall AOV: ${aov_metrics['all_customers']['aov']:.2f}")
        print(f"Report saved to: {csv_path}")
        print(f"Detailed order data saved to: {detailed_csv}")

def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate AOV reports for Shopify store')
    
    # Add arguments
    parser.add_argument('--month', type=str, help='Month in YYYY-MM format (e.g., 2023-01 for January 2023)')
    parser.add_argument('--year', type=int, help='Year for the report')
    parser.add_argument('--month-num', type=int, choices=range(1, 13), help='Month number (1-12) for the report')
    parser.add_argument('--twelve-month', action='store_true', help='Generate a 12-month report ending at the specified month')
    parser.add_argument('--start-date', type=str, help='Custom start date in YYYY-MM-DD format (e.g., 2023-01-01)')
    parser.add_argument('--end-date', type=str, help='Custom end date in YYYY-MM-DD format (e.g., 2023-12-31)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the AOV report
    run_aov_report(args.month, args.year, args.month_num, args.twelve_month, args.start_date, args.end_date)

if __name__ == "__main__":
    main()
