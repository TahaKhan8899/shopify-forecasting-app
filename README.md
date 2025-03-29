# Shopify AOV Forecasting Tool

A data automation backend for a marketing agency that connects to Shopify, fetches order data, and calculates AOV (Average Order Value) metrics segmented by new vs. returning customers.

## Overview

This tool automates the process of gathering metrics from Shopify stores by:

1. Connecting to the Shopify Admin GraphQL API
2. Fetching orders for a specified time period
3. Determining whether each order is from a new or returning customer
4. Calculating AOV metrics for each customer segment
5. Exporting the results as CSV files

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd forecasting-app
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your Shopify API credentials:
   ```
   SHOPIFY_API_TOKEN=shpat_your_api_token_here
   SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
   ```

## Getting Shopify API Access

To use this tool, you need to create a custom app in your Shopify admin:

1. Go to your Shopify admin panel
2. Navigate to Apps > App and sales channel settings
3. Click "Develop apps" at the bottom
4. Create a new app
5. Set up the app with Admin API access
6. Request the necessary scopes (read_orders, read_customers)
7. Generate an Admin API access token
8. Add the token to your `.env` file

## Usage

Run the tool to generate AOV reports:

```
python main.py
```

By default, this will generate a report for the previous month and save it to the `reports/` directory.

### Command-line Options

You can customize the date range and output directory:

```
python main.py --start-date 2023-01-01 --end-date 2023-01-31 --output-dir custom_reports
```

## Output

The tool generates two CSV files:

1. **AOV Metrics Report** - Contains aggregated metrics including:
   - Order counts for new and returning customers
   - Total sales values
   - Average Order Value for each segment
   - Percentage breakdown of orders

2. **Detailed Orders Report** - Contains line-by-line order data with customer type labeling

## Project Structure

```
forecasting-app/
├── .env                      # Environment variables
├── main.py                   # Entry point
├── requirements.txt          # Python dependencies
├── shopify/
│   └── api.py                # Shopify API client
├── metrics/
│   └── aov.py                # AOV calculation logic
├── outputs/
│   └── spreadsheet.py        # CSV export functionality
├── utils/
│   └── customer_cache.py     # Customer data caching
└── reports/                  # Output directory
```

## Deployment

For automated reporting, you can deploy this tool on a server with a cron job:

1. Set up a cron job to run weekly or monthly
2. Example cron configuration (runs on the 1st of each month at 2 AM):
   ```
   0 2 1 * * cd /path/to/forecasting-app && python main.py
   ```

## Future Enhancements

- Google Sheets integration
- Multi-store support
- Web dashboard
- Additional metrics (LTV, retention rates, etc.)

## Troubleshooting

- If you encounter permission errors with the Shopify API, verify your token has the correct scopes
- For large stores, the initial run may take longer as it builds the customer cache
- Check the `forecasting.log` file for detailed error information 