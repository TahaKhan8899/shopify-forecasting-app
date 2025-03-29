from typing import Dict, Optional
from datetime import datetime
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CustomerCache:
    """
    Cache to store customer first order dates to avoid repeated API calls.
    This improves performance when determining if orders are from new or returning customers.
    """
    
    def __init__(self, cache_file: str = "customer_first_orders.json"):
        """
        Initialize the customer cache.
        
        Args:
            cache_file: Path to the JSON file for cache persistence
        """
        self.cache_file = cache_file
        self.first_order_dates: Dict[str, str] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load the cache from the JSON file if it exists."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.first_order_dates = json.load(f)
                logger.info(f"Loaded {len(self.first_order_dates)} customer records from cache")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading cache file: {str(e)}")
                self.first_order_dates = {}
    
    def save_cache(self) -> None:
        """Save the cache to the JSON file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.first_order_dates, f)
            logger.info(f"Saved {len(self.first_order_dates)} customer records to cache")
        except IOError as e:
            logger.error(f"Error saving cache file: {str(e)}")
    
    def get_first_order_date(self, customer_id: str) -> Optional[datetime]:
        """
        Get the first order date for a customer from the cache.
        
        Args:
            customer_id: The Shopify customer ID
            
        Returns:
            datetime object of the first order date if found, None otherwise
        """
        if customer_id in self.first_order_dates:
            date_str = self.first_order_dates[customer_id]
            dt = datetime.fromisoformat(date_str)
            return dt.replace(tzinfo=None)  # Make timezone-naive for consistent comparisons
        return None
    
    def set_first_order_date(self, customer_id: str, date: datetime) -> None:
        """
        Store a customer's first order date in the cache.
        
        Args:
            customer_id: The Shopify customer ID
            date: The datetime of the customer's first order
        """
        self.first_order_dates[customer_id] = date.isoformat()
    
    def is_new_customer(self, customer_id: str, order_date: datetime) -> bool:
        """
        Determine if an order represents a new customer based on cache data.
        
        Args:
            customer_id: The Shopify customer ID
            order_date: The datetime of the order being evaluated
            
        Returns:
            True if this appears to be a new customer, False otherwise
        """
        first_order_date = self.get_first_order_date(customer_id)
        
        # Normalize the order date for comparison
        order_date = self._normalize_datetime(order_date)
        
        # If we don't have a record, we'll assume it's a new customer
        # The calling code should update this if it finds otherwise
        if first_order_date is None:
            return True
        
        # Compare dates (with tolerance for timezone issues)
        # If the order date is within 1 minute of the first order date, consider it the same
        time_diff = abs((order_date - first_order_date).total_seconds())
        if time_diff < 60:  # within 1 minute
            return True
            
        # If this order date is earlier than what we have in cache, update the cache
        if order_date < first_order_date:
            self.set_first_order_date(customer_id, order_date)
            return True
            
        # This is a returning customer
        return False
    
    def update_from_orders(self, orders: list) -> None:
        """
        Update the cache based on a list of orders.
        
        Args:
            orders: List of order dictionaries from Shopify API
        """
        cache_updated = False
        
        for order in orders:
            try:
                # Skip orders without customer info
                if not order.get('customer') or not order['customer'].get('id'):
                    continue
                    
                customer_id = order['customer']['id']
                order_date = datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00'))
                order_date = self._normalize_datetime(order_date)
                
                # Check if this order's customer has embedded first order info
                customer_orders = order.get('customer', {}).get('orders', {}).get('edges', [])
                if customer_orders:
                    first_order_date = datetime.fromisoformat(
                        customer_orders[0]['node']['createdAt'].replace('Z', '+00:00')
                    )
                    first_order_date = self._normalize_datetime(first_order_date)
                    
                    # Use the earliest date between the current order and the first order data
                    if order_date <= first_order_date:
                        earliest_date = order_date
                    else:
                        earliest_date = first_order_date
                else:
                    # If no embedded order info, use this order's date
                    earliest_date = order_date
                
                # If we don't have this customer or this order is earlier than what we have
                existing_date = self.get_first_order_date(customer_id)
                if existing_date is None or earliest_date < existing_date:
                    self.set_first_order_date(customer_id, earliest_date)
                    cache_updated = True
                    
            except (KeyError, ValueError) as e:
                logger.warning(f"Error processing order for cache update: {str(e)}")
        
        # Save if we made changes
        if cache_updated:
            self.save_cache()

    def _normalize_datetime(self, dt: datetime) -> datetime:
        """
        Ensure datetime is timezone-naive for consistent comparisons.
        
        Args:
            dt: The datetime object to normalize
            
        Returns:
            Timezone-naive datetime object
        """
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
