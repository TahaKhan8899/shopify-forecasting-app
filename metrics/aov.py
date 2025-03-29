from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import logging
from utils.customer_cache import CustomerCache
import calendar

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AOVCalculator:
    """
    Calculator for Average Order Value (AOV) metrics,
    segmented by new vs. returning customers.
    """
    
    def __init__(self, customer_cache: CustomerCache):
        """
        Initialize the AOV calculator.
        
        Args:
            customer_cache: CustomerCache instance for determining customer type
        """
        self.customer_cache = customer_cache
        
    def _extract_money_amount(self, money_obj: Dict) -> float:
        """
        Extract the amount from a Shopify money object.
        
        Args:
            money_obj: Dictionary containing shopMoney with amount
            
        Returns:
            Float amount or 0.0 if not found
        """
        try:
            return float(money_obj.get('shopMoney', {}).get('amount', 0.0))
        except (ValueError, TypeError, AttributeError):
            logger.warning(f"Error extracting money amount from {money_obj}")
            return 0.0
    
    def _parse_order_date(self, created_at: str) -> datetime:
        """
        Parse the order creation date from ISO format.
        
        Args:
            created_at: ISO format date string from Shopify
            
        Returns:
            datetime object
        
        Raises:
            ValueError: If the date cannot be parsed
        """
        # Return timezone-naive datetime for consistent comparisons
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        return dt.replace(tzinfo=None)  # Strip timezone info
    
    def _get_order_value(self, order: Dict) -> Tuple[float, float, float]:
        """
        Calculate the value components of an order.
        
        Args:
            order: Order dictionary from Shopify API
            
        Returns:
            Tuple of (total_price, refunded_amount, total_revenue)
            where total_revenue = total_price + refunded_amount
        """
        # Extract total price
        total_price = self._extract_money_amount(order.get('totalPriceSet', {}))
        
        # Extract refunds
        refunded_amount = self._extract_money_amount(order.get('totalRefundedSet', {}))
        
        # Total revenue includes both the remaining value and refunds
        # This accounts for the original order value as requested
        total_revenue = total_price + refunded_amount
        
        return total_price, refunded_amount, total_revenue
    
    def _is_first_order(self, order: Dict) -> bool:
        """
        Determine if an order is the customer's first order based on the order data.
        
        Args:
            order: Order dictionary from Shopify API
            
        Returns:
            True if this appears to be the customer's first order, False otherwise
        """
        try:
            # Get the current order date
            current_order_date = self._parse_order_date(order['createdAt'])
            
            # Extract customer's first order date from embedded orders data
            customer = order.get('customer', {})
            if not customer:
                return True  # If no customer data, treat as new customer
                
            customer_orders = customer.get('orders', {}).get('edges', [])
            
            # If no previous orders, it's a first order
            if not customer_orders:
                return True
                
            first_order_date = self._parse_order_date(customer_orders[0]['node']['createdAt'])
            
            # If current order date is within 1 minute of first order date, consider it the same order
            time_diff = abs((current_order_date - first_order_date).total_seconds())
            if time_diff < 60:
                return True
                
            # If current order date is earlier or the same as first order date, it's a first order
            return current_order_date <= first_order_date
            
        except (KeyError, IndexError, ValueError) as e:
            logger.warning(f"Error determining if order is first: {str(e)}")
            return True  # Default to treating as a new customer if we can't determine
    
    def _get_empty_metrics_template(self) -> Dict:
        """
        Get an empty metrics template with the structure for customer segments.
        
        Returns:
            Dictionary with empty metrics structure
        """
        return {
            'new_customers': {
                'order_count': 0,
                'total_sales': 0.0,
                'total_refunds': 0.0,
                'total_revenue': 0.0,
                'aov': 0.0
            },
            'returning_customers': {
                'order_count': 0,
                'total_sales': 0.0,
                'total_refunds': 0.0,
                'total_revenue': 0.0,
                'aov': 0.0
            },
            'all_customers': {
                'order_count': 0,
                'total_sales': 0.0,
                'total_refunds': 0.0,
                'total_revenue': 0.0,
                'aov': 0.0
            }
        }
        
    def _calculate_aov(self, metrics: Dict) -> None:
        """
        Calculate AOV for each segment in the metrics dictionary.
        
        Args:
            metrics: Dictionary containing metrics data
        """
        for segment in ['new_customers', 'returning_customers', 'all_customers']:
            if metrics[segment]['order_count'] > 0:
                metrics[segment]['aov'] = round(
                    metrics[segment]['total_revenue'] / metrics[segment]['order_count'], 2
                )
            else:
                metrics[segment]['aov'] = 0.0
    
    def calculate_monthly_aov(self, orders: List[Dict],
                               start_date: datetime, end_date: datetime,
                               update_cache: bool = True) -> Dict:
        """
        Calculate monthly AOV metrics split by new vs. returning customers.
        
        Args:
            orders: List of order dictionaries from Shopify API
            start_date: Start date of the period
            end_date: End date of the period
            update_cache: Whether to update the customer cache
            
        Returns:
            Dictionary with AOV metrics
        """
        # Initialize metrics
        metrics = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
        # Add the metrics template
        metrics.update(self._get_empty_metrics_template())
        
        # Update cache with all orders if requested
        if update_cache:
            self.customer_cache.update_from_orders(orders)
        
        # Process each order
        for order in orders:
            try:
                # Skip orders without customer info
                if not order.get('customer') or not order['customer'].get('id'):
                    logger.warning(f"Skipping order without customer info: {order.get('id', 'unknown')}")
                    continue
                    
                # Get customer ID and order date
                customer_id = order['customer']['id']
                order_date = self._parse_order_date(order['createdAt'])
                total_sales, total_refunds, total_revenue = self._get_order_value(order)
                
                # Check if this is a new or returning customer
                # First try to use the cache
                is_new = self.customer_cache.is_new_customer(customer_id, order_date)
                
                # If cache indicates it's not a new customer, verify with order data
                if not is_new:
                    is_new = self._is_first_order(order)
                
                # Update metrics
                if is_new:
                    customer_type = 'new_customers'
                else:
                    customer_type = 'returning_customers'
                
                metrics[customer_type]['order_count'] += 1
                metrics[customer_type]['total_sales'] += total_sales
                metrics[customer_type]['total_refunds'] += total_refunds
                metrics[customer_type]['total_revenue'] += total_revenue
                
                metrics['all_customers']['order_count'] += 1
                metrics['all_customers']['total_sales'] += total_sales
                metrics['all_customers']['total_refunds'] += total_refunds
                metrics['all_customers']['total_revenue'] += total_revenue
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Error processing order for AOV: {str(e)}")
        
        # Calculate AOV for each segment using the total revenue (sales + refunds)
        self._calculate_aov(metrics)
        
        return metrics
    
    def _get_month_name(self, month_num: int) -> str:
        """
        Get the month name from the month number.
        
        Args:
            month_num: Month number (1-12)
            
        Returns:
            Month name
        """
        return calendar.month_name[month_num]
    
    def _get_month_key(self, year: int, month: int) -> str:
        """
        Generate a key for the monthly data dictionary.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            String key in format "YYYY-MM"
        """
        return f"{year}-{month:02d}"
    
    def _get_month_range(self, date_obj: datetime) -> Tuple[datetime, datetime]:
        """
        Get the start and end dates for a given month.
        
        Args:
            date_obj: Datetime object
            
        Returns:
            Tuple of (start_date, end_date) for the month
        """
        year = date_obj.year
        month = date_obj.month
        
        # Calculate first day of month
        first_day = datetime(year, month, 1)
        
        # Calculate last day of month
        if month == 12:
            last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Set the time to end of day for last_day
        last_day = datetime.combine(last_day.date(), datetime.max.time())
        
        return first_day, last_day
    
    def calculate_monthly_metrics(self, orders: List[Dict],
                                 start_date: datetime, end_date: datetime,
                                 update_cache: bool = True) -> Dict:
        """
        Calculate metrics for each month in the specified date range.
        
        Args:
            orders: List of order dictionaries from Shopify API
            start_date: Start date of the overall period
            end_date: End date of the overall period
            update_cache: Whether to update the customer cache
            
        Returns:
            Dictionary with monthly metrics and totals
        """
        # Initialize the result dictionary
        result = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'months': {},
            'totals': self._get_empty_metrics_template()
        }
        
        # Update cache with all orders if requested
        if update_cache:
            self.customer_cache.update_from_orders(orders)
        
        # Generate list of months in the date range
        current_date = datetime(start_date.year, start_date.month, 1)
        end_month_date = datetime(end_date.year, end_date.month, 1)
        
        months = []
        while current_date <= end_month_date:
            month_start, month_end = self._get_month_range(current_date)
            month_key = self._get_month_key(current_date.year, current_date.month)
            month_name = self._get_month_name(current_date.month)
            
            months.append({
                'key': month_key,
                'name': month_name,
                'year': current_date.year,
                'month': current_date.month,
                'start_date': month_start,
                'end_date': month_end,
                'display': f"{month_name} {current_date.year}"
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1)
        
        # Initialize metrics for each month
        for month_info in months:
            month_key = month_info['key']
            result['months'][month_key] = {
                'info': month_info,
                'metrics': self._get_empty_metrics_template()
            }
        
        # Process each order and assign to the correct month
        for order in orders:
            try:
                # Skip orders without customer info
                if not order.get('customer') or not order['customer'].get('id'):
                    logger.warning(f"Skipping order without customer info: {order.get('id', 'unknown')}")
                    continue
                
                # Get customer ID and order date
                customer_id = order['customer']['id']
                order_date = self._parse_order_date(order['createdAt'])
                
                # Check if the order falls within our date range
                if order_date < start_date or order_date > end_date:
                    continue
                
                # Determine which month this order belongs to
                order_month_key = self._get_month_key(order_date.year, order_date.month)
                
                # Skip if we don't have this month in our range
                if order_month_key not in result['months']:
                    continue
                
                # Get values from the order
                total_sales, total_refunds, total_revenue = self._get_order_value(order)
                
                # Check if this is a new or returning customer
                # First try to use the cache
                is_new = self.customer_cache.is_new_customer(customer_id, order_date)
                
                # If cache indicates it's not a new customer, verify with order data
                if not is_new:
                    is_new = self._is_first_order(order)
                
                # Update metrics for the month
                customer_type = 'new_customers' if is_new else 'returning_customers'
                
                month_metrics = result['months'][order_month_key]['metrics']
                
                # Update monthly metrics
                month_metrics[customer_type]['order_count'] += 1
                month_metrics[customer_type]['total_sales'] += total_sales
                month_metrics[customer_type]['total_refunds'] += total_refunds
                month_metrics[customer_type]['total_revenue'] += total_revenue
                
                month_metrics['all_customers']['order_count'] += 1
                month_metrics['all_customers']['total_sales'] += total_sales
                month_metrics['all_customers']['total_refunds'] += total_refunds
                month_metrics['all_customers']['total_revenue'] += total_revenue
                
                # Update totals
                result['totals'][customer_type]['order_count'] += 1
                result['totals'][customer_type]['total_sales'] += total_sales
                result['totals'][customer_type]['total_refunds'] += total_refunds
                result['totals'][customer_type]['total_revenue'] += total_revenue
                
                result['totals']['all_customers']['order_count'] += 1
                result['totals']['all_customers']['total_sales'] += total_sales
                result['totals']['all_customers']['total_refunds'] += total_refunds
                result['totals']['all_customers']['total_revenue'] += total_revenue
                
            except (KeyError, ValueError) as e:
                logger.warning(f"Error processing order for monthly metrics: {str(e)}")
        
        # Calculate AOV for each month and for totals
        for month_key, month_data in result['months'].items():
            self._calculate_aov(month_data['metrics'])
            
        self._calculate_aov(result['totals'])
        
        # Calculate percentage change for each month's AOV compared to the 12-month average
        # First, get the overall average AOVs
        avg_new_customer_aov = result['totals']['new_customers']['aov']
        avg_returning_customer_aov = result['totals']['returning_customers']['aov']
        
        # Then calculate the percentage change for each month
        for month_key, month_data in result['months'].items():
            month_metrics = month_data['metrics']
            
            # Calculate percentage change for new customers
            if month_metrics['new_customers']['order_count'] == 0:
                # No orders in this month, so don't calculate a percentage change
                new_customer_percent_change = None
            elif avg_new_customer_aov > 0:
                new_customer_percent_change = (month_metrics['new_customers']['aov'] - avg_new_customer_aov) / avg_new_customer_aov
            else:
                new_customer_percent_change = 0.0
                
            # Calculate percentage change for returning customers
            if month_metrics['returning_customers']['order_count'] == 0:
                # No orders in this month, so don't calculate a percentage change
                returning_customer_percent_change = None
            elif avg_returning_customer_aov > 0:
                returning_customer_percent_change = (month_metrics['returning_customers']['aov'] - avg_returning_customer_aov) / avg_returning_customer_aov
            else:
                returning_customer_percent_change = 0.0
                
            # Add these values to the month's metrics
            month_metrics['new_customers']['percent_change'] = new_customer_percent_change
            month_metrics['returning_customers']['percent_change'] = returning_customer_percent_change
            
        # Add zero percent change to the totals entry (since it's the baseline)
        result['totals']['new_customers']['percent_change'] = 0.0
        result['totals']['returning_customers']['percent_change'] = 0.0
        
        return result
