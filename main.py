import os
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

    # 1. Load & clean the dataset
    df = load_data(csv_path)

    # 2. Run the full analysis (console output + executive summary + HTML report)
    terminal_buffer = StringIO()
    with redirect_stdout(terminal_buffer):
        run_analysis(df)
    terminal_output = terminal_buffer.getvalue()
    print(terminal_output, end='')

    # 3. Export findings to Excel (9 tabs)
    export_to_excel(df, xlsx_path)
    append_terminal_details(xlsx_path, html_path, terminal_output)

if __name__ == "__main__":
    main()
