import os
import sys
from contextlib import redirect_stdout
from io import StringIO

from loader import load_data
from analyzer import run_analysis
from exporter import export_to_excel, append_terminal_details

def main():
    # Resolve paths relative to this file so the script works from any cwd
    project_root = os.path.abspath(os.path.dirname(__file__))
    csv_path     = os.path.join(project_root, "data", "interactions.csv")
    xlsx_path    = os.path.join(project_root, "reports", "june_2026_genesys_report.xlsx")
    html_path    = os.path.join(project_root, "reports", "executive_report_june2026.html")

    # 1. Load & clean the dataset (with a safety check)
    if not os.path.exists(csv_path):
        print(f"❌ Error: Cannot find the dataset at {csv_path}")
        print("Please ensure your Genesys export is named 'interactions.csv' and placed in the 'data' folder.")
        sys.exit(1)
        
    df = load_data(csv_path)

    if df is None or df.empty:
        print("❌ Error: Dataset is empty or failed to load.")
        sys.exit(1)

    # 2. Run the full analysis (console output + executive summary + HTML report)
    terminal_buffer = StringIO()
    with redirect_stdout(terminal_buffer):
        run_analysis(df)
        
    terminal_output = terminal_buffer.getvalue()
    print(terminal_output, end='')

    # 3. Export findings to Excel (9 tabs)
    export_to_excel(df, xlsx_path)
    
    # 4. Append exact runtime terminal output to the logs
    append_terminal_details(xlsx_path, html_path, terminal_output)

if __name__ == "__main__":
    main()