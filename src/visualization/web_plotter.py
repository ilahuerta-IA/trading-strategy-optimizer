# src/visualization/web_plotter.py
import webbrowser
from pathlib import Path
import traceback

# Import our safe serializer
from utils.serialization import json_dumps_safe

# Define paths relative to this file
VISUALIZATION_DIR = Path(__file__).resolve().parent
TEMPLATE_FILE = VISUALIZATION_DIR / 'report_template.html'
PROJECT_ROOT = VISUALIZATION_DIR.parent.parent
TEMP_DIR = PROJECT_ROOT / 'temp_reports'

def create_standalone_report(results_data):
    """
    Generates and opens a self-contained HTML file with embedded data and JS
    to show the backtest results.
    """
    print("\n--- Generating Standalone HTML Report ---")

    try:
        # 1. Read the HTML template from disk
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            template_html = f.read()

        # 2. Serialize the full results object into a JSON string
        results_json = json_dumps_safe(results_data.__dict__)

        # 3. Inject the JSON data into the HTML template
        #    Remove the single quotes from around the placeholder
        final_html = template_html.replace("{{RESULTS_JSON}}", results_json)

        # 4. Save the final HTML to a temporary file
        TEMP_DIR.mkdir(exist_ok=True)
        report_path = TEMP_DIR / f"report_{results_data.run_name}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(final_html)
            
        print(f"✅ Report saved to: {report_path}")

        # 5. Open the report in the user's default web browser
        webbrowser.open(f'file://{report_path.resolve()}')
        print("🚀 Opening report in web browser...")

    except Exception as e:
        print(f"❌ Failed to create HTML report: {e}")
        traceback.print_exc()