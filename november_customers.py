#!/usr/bin/env python
import os
import logging
import calendar
from datetime import datetime, timezone
from dotenv import load_dotenv
from shopify.api import create_api_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Define November 2024 timeframe (make timezone-aware)
    TARGET_YEAR = 2025
    TARGET_MONTH = 3
    
    # Create API client
    client = create_api_client()
    
    # Get precise date range for November 2024 (UTC timezone)
    nov_start = datetime(TARGET_YEAR, TARGET_MONTH, 1, 0, 0, 0, tzinfo=timezone.utc)
    nov_end = datetime(TARGET_YEAR, TARGET_MONTH, 
                      calendar.monthrange(TARGET_YEAR, TARGET_MONTH)[1],
                      23, 59, 59, tzinfo=timezone.utc)
    
    logger.info(f"Analyzing March {TARGET_YEAR} cohort ({nov_start} to {nov_end})")
    
    # Get true new customers (first orders in November)
    try:
        cohort = client.get_customers_first_order_between(nov_start, nov_end)
        logger.info(f"Found {len(cohort)} first-time customers in March")
        
        # Display results
        print("\n=== MArch 2025 First-Time Customers ===")
        print(f"Total: {len(cohort)}")
        
        # Optional: Print first 10 as examples
        print("\nSample customers (first 50):")
        for i, customer_id in enumerate(cohort[:50], 1):
            print(f"{i}. {customer_id}")
            
    except Exception as e:
        logger.error(f"Failed to analyze cohort: {str(e)}")
        raise

if __name__ == "__main__":
    main()

import os
import requests
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime,timezone, timedelta
import calendar
import json
from typing import Set
from warnings import warn

# Configure logger
logger = logging.getLogger(__name__)

def get_month_date_range(year: int, month: int) -> tuple[datetime, datetime]:
    """
    Get precise datetime range for a calendar month.
    Returns tuple of (first_moment_of_month, last_moment_of_month)
    """
    first_day = datetime(year, month, 1, 0, 0, 0)
    last_day = datetime(
        year, month,
        calendar.monthrange(year, month)[1],  # Get last day of month
        23, 59, 59  # Set to last moment of the day
    )
    return (first_day, last_day)

def format_date_filter(start_date: datetime, end_date: datetime, field: str = "createdAt", full_day: bool = True) -> str:
    # Use the exact datetime values (in UTC) for filtering.
    # If you still want to ignore the provided time, you could set full_day=True and then force T00:00:00Z and T23:59:59Z.
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f'{field}:>="{start_str}" AND {field}:<="{end_str}"'




class ShopifyAPI:
    """
    Client for interacting with the Shopify Admin GraphQL API.
    Handles authentication, request formatting, and error handling.
    """
    
    def __init__(self, domain: str, api_token: str):
        """
        Initialize the Shopify API client.
        
        Args:
            domain: The Shopify store domain (e.g., 'my-store.myshopify.com')
            api_token: The Shopify Admin API access token
        """
        self.domain = domain
        self.api_token = api_token
        # Use the latest API version
        self.base_url = f"https://{domain}/admin/api/2025-01/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": api_token
        }
    
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        Execute a GraphQL query against the Shopify Admin API.
        
        Args:
            query: The GraphQL query string
            variables: Optional variables for the GraphQL query
            
        Returns:
            Dict containing the response data
            
        Raises:
            Exception: If the API request fails
        """
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        result = response.json()
        
        if "errors" in result:
            errors = result["errors"]
            error_message = "; ".join([error.get("message", "Unknown error") for error in errors])
            raise Exception(f"GraphQL query failed: {error_message}")
        
        return result
    
    def get_orders(self, start_date: datetime, end_date: Optional[datetime] = None, 
                   cursor: Optional[str] = None, limit: int = 50) -> Dict:
        """
        Fetch orders from the Shopify store within a date range.
        
        Args:
            start_date: The start date for order filtering
            end_date: Optional end date for order filtering, defaults to current date
            cursor: Optional cursor for pagination
            limit: Number of orders to fetch per request (max 250)
            
        Returns:
            Dict containing order data and pagination info
        """
        if end_date is None:
            end_date = datetime.now()
            
        # Format dates for Shopify query
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Build date query filter
        date_query = f"created_at:>={start_str} AND created_at:<={end_str}"
        
        # GraphQL query for orders with essential fields
        # Updated to use valid fields according to the schema
        query = """
        query GetOrders($query: String, $numOrders: Int!, $cursor: String) {
          orders(first: $numOrders, after: $cursor, query: $query) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                createdAt
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                totalRefundedSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                customer {
                  id
                  email
                  # Getting first order to determine if new/returning
                  orders(first: 1, sortKey: CREATED_AT, reverse: false) {
                    edges {
                      node {
                        id
                        createdAt
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "query": date_query,
            "numOrders": limit,
            "cursor": cursor
        }
        
        return self.execute_query(query, variables)
    
    def get_customer_first_order_date(self, customer_id: str) -> Optional[datetime]:
        """
        Get the date of a customer's first order.
        
        Args:
            customer_id: The Shopify customer ID
            
        Returns:
            datetime of the customer's first order or None if no orders
        """
        query = """
        query GetCustomerFirstOrder($id: ID!) {
          customer(id: $id) {
            orders(first: 1, sortKey: CREATED_AT, reverse: false) {
              edges {
                node {
                  id
                  createdAt
                }
              }
            }
          }
        }
        """
        
        variables = {
            "id": customer_id
        }
        
        result = self.execute_query(query, variables)
        
        try:
            edges = result["data"]["customer"]["orders"]["edges"]
            if edges:
                created_at = edges[0]["node"]["createdAt"]
                return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return None
        except (KeyError, IndexError):
            return None
    
    def fetch_all_orders(self, start_date: datetime, end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Fetch all orders in a date range, handling pagination automatically.
        
        Args:
            start_date: The start date for order filtering
            end_date: Optional end date for order filtering
            
        Returns:
            List of all order objects
        """
        all_orders = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            response = self.get_orders(start_date, end_date, cursor)
            
            try:
                orders_data = response["data"]["orders"]
                page_info = orders_data["pageInfo"]
                
                # Add orders from this page
                edges = orders_data["edges"]
                all_orders.extend([edge["node"] for edge in edges])
                
                # Update pagination variables
                has_next_page = page_info["hasNextPage"]
                cursor = page_info["endCursor"] if has_next_page else None
                
            except (KeyError, TypeError) as e:
                raise Exception(f"Failed to process orders response: {str(e)}")
        
        return all_orders
      

      
    def get_orders_for_customers(self, customer_ids: List[str], start_date: datetime, end_date: datetime, exclude_first_order: bool = False) -> int:
        """Fetch orders within the date range and count only those orders placed by customers in customer_ids.
        Optionally exclude each customer's first order in the period.
        
        Args:
            customer_ids: List of customer IDs to filter orders.
            start_date: Start date for order filtering.
            end_date: End date for order filtering.
            exclude_first_order: If True, excludes each customer's first order in the period.
            
        Returns:
            Count of orders placed by the given customers.
        """
        orders = self.fetch_all_orders(start_date, end_date)
        count = 0
        
        if not exclude_first_order:
            # Original behavior - count all orders
            for order in orders:
                customer = order.get('customer')
                if customer and customer.get('id') in customer_ids:
                    count += 1
        else:
            # New behavior - track first order dates and exclude them
            first_order_dates = {}
            
            # First pass: collect first order dates for each customer
            for order in orders:
                customer = order.get('customer')
                if customer and customer.get('id') in customer_ids:
                    customer_id = customer['id']
                    order_date = datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00'))
                    
                    if customer_id not in first_order_dates or order_date < first_order_dates[customer_id]:
                        first_order_dates[customer_id] = order_date
            
            # Second pass: count orders that aren't the first order
            for order in orders:
                customer = order.get('customer')
                if customer and customer.get('id') in customer_ids:
                    customer_id = customer['id']
                    order_date = datetime.fromisoformat(order['createdAt'].replace('Z', '+00:00'))
                    
                    if order_date > first_order_dates.get(customer_id, order_date + timedelta(days=1)):
                        count += 1
        
        return count    

    
    
    def  get_customers_created_between(self, start_date: datetime, end_date: datetime, limit: int = 50) -> List[Dict[str, Any]]:
        """
        [Legacy] Get customers who CREATED ACCOUNTS between dates.
        Use get_customers_first_order_between() for first purchase cohorts.
        """
        warn("get_customers_created_between() uses account creation dates. Use get_customers_first_order_between() for first-order cohorts.", DeprecationWarning)
        all_customers = []
        cursor = None
        has_next_page = True
        
 
        query_filter = format_date_filter(start_date, end_date, field="created_at")
        # Log the filter for debugging
        logger.info(f"Customer query filter: {query_filter}")

        query = """
        query GetCustomers($first: Int!, $query: String, $cursor: String) {
          customers(first: $first, query: $query, after: $cursor) {
            edges {
              node {
                id
                createdAt
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        while has_next_page:
            variables = {
                "first": limit,
                "query": query_filter,
                "cursor": cursor
            }
            logger.info(f"[get_new_customers] Executing query with variables: {variables}")
            result = self.execute_query(query, variables)
            customers_data = result["data"]["customers"]
            edges = customers_data["edges"]
            for edge in edges:
                customer = edge["node"]
                logger.info(f"[get_new_customers] Customer {customer['id']} created at {customer['createdAt']}")
            all_customers.extend([edge["node"] for edge in edges])
            page_info = customers_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"] if has_next_page else None
        logger.info(f"[get_new_customers] Total customers fetched: {len(all_customers)}")    
        return all_customers
    # New cohort analysis method
    
    
    
    def get_customers_first_order_between(self, start_date: datetime, end_date: datetime) -> List[str]:
        """
        Identify customers whose FIRST ORDER occurred between dates.
        Returns list of customer IDs.
        """
        logger.info(f"Building first-order cohort for {start_date} to {end_date}")
        # Ensure dates are timezone-aware (convert if necessary)
        if start_date.tzinfo is None:
          start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
          end_date = end_date.replace(tzinfo=timezone.utc)
        # Get all orders in date range with customer first order data
        orders = self.fetch_all_orders(start_date, end_date)
        cohort: Set[str] = set()

        for order in orders:
            customer = order.get('customer')
            if not customer:
                continue

            try:
                # Get first order data from embedded customer info
                first_order = customer['orders']['edges'][0]['node']
                first_order_date = datetime.fromisoformat(
                    first_order['createdAt'].replace('Z', '+00:00')
                )
            except (KeyError, IndexError, TypeError):
                continue

            customer_id = customer['id']
            
            # Check if first order falls in target window
            if start_date <= first_order_date <= end_date:
                cohort.add(customer_id)

        logger.info(f"Found {len(cohort)} customers in cohort")
        return list(cohort)
    # Optimized version of fetch_all_orders
    def fetch_cohort_orders(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Enhanced order fetcher with first-order date pre-fetching
        """
        query = """
        query GetOrders($query: String, $numOrders: Int!, $cursor: String) {
          orders(first: $numOrders, after: $cursor, query: $query) {
            edges {
              node {
                id
                createdAt
                customer {
                  id
                  orders(first: 1, sortKey: CREATED_AT, reverse: false) {
                    edges {
                      node {
                        createdAt
                      }
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        all_orders = []
        cursor = None
        has_next_page = True
        date_filter = format_date_filter(start_date, end_date, field="created_at")
        
        while has_next_page:
            variables = {
                "query": date_filter,
                "numOrders": 100,  # Optimal batch size
                "cursor": cursor
            }
            result = self.execute_query(query, variables)
            orders_data = result["data"]["orders"]
            all_orders.extend([edge["node"] for edge in orders_data["edges"]])
            page_info = orders_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"] or None

        return all_orders    

    def get_new_customers_count(self, start_date: datetime, end_date: datetime, limit: int = 50) -> int:
        """
        Return the count of customers created between start_date and end_date.
        """
        customers = self.get_new_customers(start_date, end_date, limit)
        return len(customers)

    def get_new_customer_ids(self, start_date: datetime, end_date: datetime, limit: int = 50) -> List[str]:
        """
        Return a list of customer IDs for customers created between start_date and end_date.
        """
        customers = self.get_new_customers(start_date, end_date, limit)
        return [customer["id"] for customer in customers]

def create_api_client() -> ShopifyAPI:
    """
    Create a Shopify API client from environment variables.
    
    Returns:
        ShopifyAPI instance
    
    Raises:
        ValueError: If required environment variables are missing
    """
    domain = os.getenv("SHOPIFY_STORE_DOMAIN")
    api_token = os.getenv("SHOPIFY_API_TOKEN")
    
    if not domain or not api_token:
        raise ValueError("SHOPIFY_STORE_DOMAIN and SHOPIFY_API_TOKEN must be set in .env file")
    
    return ShopifyAPI(domain, api_token)
