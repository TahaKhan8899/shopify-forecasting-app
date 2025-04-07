# metrics/recent_repeat.py

import os
import calendar
import logging
from datetime import datetime, date
from shopify.api import create_api_client
from outputs.spreadsheet import MetricsExporter
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def add_months(sourcedate: date, months: int) -> date:
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def end_of_month(date_obj: date) -> date:
    last_day = calendar.monthrange(date_obj.year, date_obj.month)[1]
    return date(date_obj.year, date_obj.month, last_day)

def generate_recent_repeat_report(cohort_start: date, cohort_end: date, output_dir: str) -> None:
    """
    Produce a CSV that shows a cohort-based retention matrix:
      - "Cohort Month"
      - "New Customers"
      - "Orders Month0", "RR% Month0", ..., "Orders Month6", "RR% Month6"
      - An aggregated "All cohorts" row.
    """
    logger.info(f"Generating Cohort Analysis from {cohort_start} to {cohort_end}")
    api_client = create_api_client()
    
    # Data structure: For each cohort month, store:
    # { 'cohort_size': int, 'orders': {0: #orders, 1: #orders, ...} }
    cohorts_data = {}
    
    # "All cohorts" aggregator
    all_cohorts_size = 0
    all_cohorts_orders = {offset: 0 for offset in range(7)}
    
    current_cohort = cohort_start
    while current_cohort <= cohort_end:
        month_label = current_cohort.strftime("%B %Y")
        # Calculate start/end of that month
        month_start = date(current_cohort.year, current_cohort.month, 1)
        month_end = end_of_month(month_start)

        # 1. Fetch new customer data
        new_cust_count = api_client.get_new_customers_count(month_start, month_end)
        new_cust_ids = api_client.get_new_customer_ids(month_start, month_end)

        # 2. For offsets 0..6, find how many orders were placed
        offset_orders = {}
        for offset in range(7):
            period_start = add_months(month_start, offset)
            period_end = end_of_month(period_start)
            today = datetime.today().date()
            
            if period_start > today:
                # No data for future months
                offset_orders[offset] = 0
            else:
                num_orders = api_client.get_orders_for_customers(new_cust_ids, period_start, period_end)
                offset_orders[offset] = num_orders
        
        # 3. Store results in cohorts_data
        cohorts_data[month_label] = {
            "cohort_size": new_cust_count,
            "orders": offset_orders
        }
        
        # 4. Update "All cohorts" aggregator
        all_cohorts_size += new_cust_count
        for offset in range(7):
            all_cohorts_orders[offset] += offset_orders[offset]
        
        # Move to next cohort month
        current_cohort = add_months(current_cohort, 1)

    # Build a list of rows for CSV output
    csv_rows = []
    
    # "All cohorts" row
    all_cohorts_row = {
        "Cohort Month": "All cohorts",
        "New Customers": all_cohorts_size
    }
    for offset in range(7):
        all_cohorts_row[f"Orders Month{offset}"] = all_cohorts_orders[offset]
        if all_cohorts_size > 0:
            rr_percent = (all_cohorts_orders[offset] / all_cohorts_size) * 100
            all_cohorts_row[f"RR% Month{offset}"] = f"{rr_percent:.1f}%"
        else:
            all_cohorts_row[f"RR% Month{offset}"] = ""
    csv_rows.append(all_cohorts_row)
    
    # Then each monthly row
    for month_label, data in cohorts_data.items():
        row = {
            "Cohort Month": month_label,
            "New Customers": data["cohort_size"]
        }
        c_size = data["cohort_size"]
        for offset in range(7):
            orders = data["orders"][offset]
            row[f"Orders Month{offset}"] = orders
            if c_size > 0:
                rr_percent = (orders / c_size) * 100
                row[f"RR% Month{offset}"] = f"{rr_percent:.1f}%"
            else:
                row[f"RR% Month{offset}"] = ""
        csv_rows.append(row)
    
    # Export the CSV using your MetricsExporter method
    exporter = MetricsExporter(output_dir=output_dir)
    exporter.export_recent_repeat_report(csv_rows, filename="Customer_Cohort_Analysis.csv")
    logger.info(f"Customer cohort analysis exported to {output_dir}{os.sep}Customer_Cohort_Analysis.csv")
    print(f"Report generated: {output_dir}{os.sep}Customer_Cohort_Analysis.csv")
