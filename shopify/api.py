import os
import requests
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

# Configure logger
logger = logging.getLogger(__name__)

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

    def get_orders_for_customers(self, customer_ids: List[str], start_date: datetime, end_date: datetime) -> int:
        """
        Fetch orders within the date range and count only those orders placed by customers in customer_ids.
        
        Args:
            customer_ids: List of customer IDs to filter orders.
            start_date: Start date for order filtering.
            end_date: End date for order filtering.
        
        Returns:
            Count of orders placed by the given customers.
        """
        orders = self.fetch_all_orders(start_date, end_date)
        count = 0
        for order in orders:
            customer = order.get('customer')
            if customer and customer.get('id') in customer_ids:
                count += 1
        return count

    def get_new_customers(self, start_date: datetime, end_date: datetime, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch all customers created between start_date and end_date using Shopify's GraphQL API.
        
        Args:
            start_date: The start datetime for filtering customer creation.
            end_date: The end datetime for filtering customer creation.
            limit: Number of customers to fetch per page.
        
        Returns:
            List of customer objects containing 'id' and 'createdAt'.
        """
        all_customers = []
        cursor = None
        has_next_page = True

        # Use full ISO8601 timestamps for filtering
        start_str = start_date.strftime("%Y-%m-%dT00:00:00")
        end_str = end_date.strftime("%Y-%m-%dT23:59:59")
        query_filter = f"created_at:>={start_str} AND created_at:<={end_str}"
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
            result = self.execute_query(query, variables)
            customers_data = result["data"]["customers"]
            edges = customers_data["edges"]
            all_customers.extend([edge["node"] for edge in edges])
            page_info = customers_data["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            cursor = page_info["endCursor"] if has_next_page else None
            
        return all_customers

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
