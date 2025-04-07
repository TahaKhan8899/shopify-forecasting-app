import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import os

from shopify.api import ShopifyAPI, create_api_client

class TestShopifyAPI(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.domain = "test-store.myshopify.com"
        self.api_token = "fake_token"
        self.api = ShopifyAPI(self.domain, self.api_token)
        
        # Sample GraphQL response for orders
        self.mock_orders_response = {
            "data": {
                "orders": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": "cursor123"
                    },
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Order/1",
                                "createdAt": "2024-01-15T12:00:00Z",
                                "totalPriceSet": {"shopMoney": {"amount": "100.00", "currencyCode": "USD"}},
                                "totalRefundedSet": {"shopMoney": {"amount": "0.00", "currencyCode": "USD"}},
                                "customer": {
                                    "id": "gid://shopify/Customer/1",
                                    "email": "customer1@example.com",
                                    "orders": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "id": "gid://shopify/Order/1",
                                                    "createdAt": "2024-01-15T12:00:00Z"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        # Sample GraphQL response for customer first order
        self.mock_customer_response = {
            "data": {
                "customer": {
                    "orders": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/Order/1",
                                    "createdAt": "2024-01-15T12:00:00Z"
                                }
                            }
                        ]
                    }
                }
            }
        }
    
    @patch('requests.post')
    def test_execute_query(self, mock_post):
        """Test the execute_query method handles responses correctly."""
        # Set up mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"test": "value"}}
        mock_post.return_value = mock_response
        
        # Execute the query
        result = self.api.execute_query("test_query", {"var": "value"})
        
        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], f"https://{self.domain}/admin/api/2025-01/graphql.json")
        self.assertEqual(call_args[1]["headers"]["X-Shopify-Access-Token"], self.api_token)
        self.assertEqual(call_args[1]["json"]["query"], "test_query")
        self.assertEqual(call_args[1]["json"]["variables"], {"var": "value"})
        
        # Verify the result is correct
        self.assertEqual(result, {"data": {"test": "value"}})
    
    @patch('requests.post')
    def test_execute_query_http_error(self, mock_post):
        """Test the execute_query method handles HTTP errors correctly."""
        # Set up mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # Verify the exception is raised
        with self.assertRaises(Exception) as context:
            self.api.execute_query("test_query")
        
        self.assertIn("API request failed with status 401", str(context.exception))
    
    @patch('requests.post')
    def test_execute_query_graphql_error(self, mock_post):
        """Test the execute_query method handles GraphQL errors correctly."""
        # Set up mock response with GraphQL error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [
                {"message": "Field does not exist"}
            ]
        }
        mock_post.return_value = mock_response
        
        # Verify the exception is raised
        with self.assertRaises(Exception) as context:
            self.api.execute_query("test_query")
        
        self.assertIn("GraphQL query failed: Field does not exist", str(context.exception))
    
    @patch.object(ShopifyAPI, 'execute_query')
    def test_get_orders(self, mock_execute_query):
        """Test the get_orders method formats the request correctly."""
        # Set up mock response
        mock_execute_query.return_value = self.mock_orders_response
        
        # Define test dates
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Call the method
        result = self.api.get_orders(start_date, end_date, cursor="test_cursor", limit=25)
        
        # Verify execute_query was called with correct parameters
        mock_execute_query.assert_called_once()
        query_args = mock_execute_query.call_args[0][0]
        variables = mock_execute_query.call_args[0][1]
        
        # Check that the query contains expected structure
        self.assertIn("query GetOrders", query_args)
        self.assertIn("orders(first: $numOrders, after: $cursor, query: $query)", query_args)
        
        # Check variables
        self.assertEqual(variables["numOrders"], 25)
        self.assertEqual(variables["cursor"], "test_cursor")
        self.assertEqual(variables["query"], "created_at:>=2024-01-01 AND created_at:<=2024-01-31")
        
        # Verify the result
        self.assertEqual(result, self.mock_orders_response)
    
    @patch.object(ShopifyAPI, 'execute_query')
    def test_get_customer_first_order_date(self, mock_execute_query):
        """Test that customer first order date is extracted correctly."""
        # Set up mock response
        mock_execute_query.return_value = self.mock_customer_response
        
        # Call the method
        result = self.api.get_customer_first_order_date("gid://shopify/Customer/1")
        
        # Verify execute_query was called correctly
        mock_execute_query.assert_called_once()
        
        # Check the result is a datetime object with the correct value
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)
    
    @patch.object(ShopifyAPI, 'execute_query')
    def test_get_customer_first_order_date_no_orders(self, mock_execute_query):
        """Test handling of customers with no orders."""
        # Set up mock response with no orders
        mock_execute_query.return_value = {"data": {"customer": {"orders": {"edges": []}}}}
        
        # Call the method
        result = self.api.get_customer_first_order_date("gid://shopify/Customer/1")
        
        # Verify result is None
        self.assertIsNone(result)
    
    @patch.object(ShopifyAPI, 'get_orders')
    def test_fetch_all_orders_single_page(self, mock_get_orders):
        """Test fetching all orders when there's only one page."""
        # Set up mock response
        mock_get_orders.return_value = self.mock_orders_response
        
        # Define test dates
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Call the method
        result = self.api.fetch_all_orders(start_date, end_date)
        
        # Verify get_orders was called correctly
        mock_get_orders.assert_called_once_with(start_date, end_date, None)
        
        # Check the result contains the expected orders
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "gid://shopify/Order/1")
    
    @patch.object(ShopifyAPI, 'get_orders')
    def test_fetch_all_orders_multiple_pages(self, mock_get_orders):
        """Test fetching all orders with pagination."""
        # Set up mock responses for two pages
        page1_response = {
            "data": {
                "orders": {
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": "cursor123"
                    },
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Order/1",
                                "createdAt": "2024-01-15T12:00:00Z",
                            }
                        }
                    ]
                }
            }
        }
        
        page2_response = {
            "data": {
                "orders": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": "cursor456"
                    },
                    "edges": [
                        {
                            "node": {
                                "id": "gid://shopify/Order/2",
                                "createdAt": "2024-01-20T12:00:00Z",
                            }
                        }
                    ]
                }
            }
        }
        
        mock_get_orders.side_effect = [page1_response, page2_response]
        
        # Define test dates
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Call the method
        result = self.api.fetch_all_orders(start_date, end_date)
        
        # Verify get_orders was called correctly for both pages
        self.assertEqual(mock_get_orders.call_count, 2)
        mock_get_orders.assert_any_call(start_date, end_date, None)
        mock_get_orders.assert_any_call(start_date, end_date, "cursor123")
        
        # Check the result contains the expected orders
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "gid://shopify/Order/1")
        self.assertEqual(result[1]["id"], "gid://shopify/Order/2")
    
    @patch.dict(os.environ, {"SHOPIFY_STORE_DOMAIN": "env-store.myshopify.com", "SHOPIFY_API_TOKEN": "env_token"})
    def test_create_api_client_from_env(self):
        """Test creating an API client from environment variables."""
        client = create_api_client()
        
        # Verify the client is initialized with env values
        self.assertIsInstance(client, ShopifyAPI)
        self.assertEqual(client.domain, "env-store.myshopify.com")
        self.assertEqual(client.api_token, "env_token")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_create_api_client_missing_env(self):
        """Test error handling when environment variables are missing."""
        with self.assertRaises(ValueError) as context:
            create_api_client()
        
        self.assertIn("SHOPIFY_STORE_DOMAIN and SHOPIFY_API_TOKEN must be set", str(context.exception))

if __name__ == '__main__':
    unittest.main() 