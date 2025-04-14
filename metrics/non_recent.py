# metrics/non_recent.py
from datetime import date
from shopify.api import create_api_client
from outputs.spreadsheet import MetricsExporter

def generate_active_non_recent_report(initial_end: date, reorder_start: date, 
                                    reorder_end: date, output_dir: str) -> None:
    """Generate Active Non-Recent Repeat report"""
    api = create_api_client()
    exporter = MetricsExporter(output_dir)
    
    data = api.get_active_non_recent_customers(
        initial_end=initial_end,
        reorder_start=reorder_start,
        reorder_end=reorder_end
    )
    
    report_data = [{
        "Initial Order Prior to...": data['initial_period'],
        "Re-Ordered Between": data['reorder_period'],
        "Active Non-Recent Customers": data['active_non_recent_customers'],
        "Time": data['time_period'],
        "Active Non-Recent Customer Orders (L30)": data['l30_customers'],
        "RR %": f"{data['rr_percent']:.2f}%"
    }]
    
    exporter.export_active_non_recent_report(
        report_data=report_data,
        filename="Assist-Active_Non_Recent_Repeat.csv"
    )