import os
from loader import load_data
from analyzer import run_analysis
from exporter import export_to_excel

def main():
    # Resolve paths relative to this file so the script works from any cwd
    project_root = os.path.abspath(os.path.dirname(__file__))
    csv_path     = os.path.join(project_root, "data", "interactions.csv")
    xlsx_path    = os.path.join(project_root, "reports", "june_2026_genesys_report.xlsx")

    # 1. Load & clean the dataset
    df = load_data(csv_path)

    # 2. Run the full analysis (console output + executive summary + HTML report)
    run_analysis(df)

    # 3. Export findings to Excel (9 tabs)
    export_to_excel(df, xlsx_path)

if __name__ == "__main__":
    main()