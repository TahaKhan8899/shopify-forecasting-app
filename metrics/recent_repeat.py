# metrics/recent_repeat.py
import os
import calendar
import logging
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from shopify.api import create_api_client
from outputs.spreadsheet import MetricsExporter
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def generate_recent_repeat_report(cohort_start: date, cohort_end: date, output_dir: str) -> None:
    """Generate cohort retention report using first-order dates"""
    logger.info(f"Generating cohort report from {cohort_start} to {cohort_end}")
    
    api = create_api_client()
    exporter = MetricsExporter(output_dir)
    
    # Use naive datetimes
    start_dt = datetime(cohort_start.year, cohort_start.month, 1)
    end_dt = datetime(cohort_end.year, cohort_end.month, 
                     calendar.monthrange(cohort_end.year, cohort_end.month)[1],
                     23, 59, 59)

    months = []
    current = start_dt
    while current <= end_dt:
        months.append(current)
        current += relativedelta(months=1)

    report_rows = []
    for cohort_month in months:
        month_str = cohort_month.strftime("%b %Y")
        logger.info(f"Processing cohort: {month_str}")

        # Get first-order customers for this month
        cohort_end_date = cohort_month + relativedelta(months=1) - timedelta(seconds=1)
        customer_ids = api.get_customers_first_order_between(cohort_month, cohort_end_date)
        cohort_size = len(customer_ids)

        row_data = {
            "Cohort Month": month_str,
            "New Customers": cohort_size
        }
        
        for offset in range(7):
            period_start = cohort_month + relativedelta(months=offset)
            period_end = period_start + relativedelta(months=1) - timedelta(seconds=1)
            
            if datetime.now() < period_start:
                row_data[f"Orders Month{offset}"] = 0
                row_data[f"RR% Month{offset}"] = "0%"
            else:
                if offset == 0:
                    # SPECIAL HANDLING FOR MONTH 0:
                    # Only count orders after their first order in the same month
                    orders = api.get_orders_for_customers(
                        customer_ids,
                        # Start from day after first order (implementation depends on your API)
                        # This requires modifying get_orders_for_customers to accept per-customer start dates
                        period_start.date(),
                        period_end.date(),
                        exclude_first_order=True  # You'll need to add this parameter
                    )
                else:
                    orders = api.get_orders_for_customers(
                        customer_ids, 
                        period_start.date(),
                        period_end.date()
                    )
                
                rr_percent = (orders / cohort_size * 100) if cohort_size > 0 else 0
                row_data[f"Orders Month{offset}"] = orders
                row_data[f"RR% Month{offset}"] = f"{rr_percent:.1f}%"

        report_rows.append(row_data)
        logger.info(f"Processed {month_str}: {cohort_size} new customers")

    exporter.export_recent_repeat_report(
        report_rows=report_rows,
        filename="Assist- Recent Customer Repeat.csv"
    )