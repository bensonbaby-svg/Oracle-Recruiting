"""
Wireframe entry point for the Fortive Oracle HCM -> ADP Celergo (Canada)
data validation agent.

Simulates the end-to-end detect-and-flag flow that the real Oracle AI Agent
Studio agent will perform:
  1. Retrieve the Oracle HCM data extract (data/sample_hcm_extract_canada.csv)
  2. Validate it against the ADP Canada rule catalog (src/rules.py)
  3. Flag exceptions and email a digest to the relevant HR/data owner (dry-run
     by default -> writes HTML files to output/)

Run: python main.py [path-to-csv]
"""
import sys

from src.validator import load_extract, validate_extract
from src.email_notifier import notify

DEFAULT_EXTRACT = "data/sample_hcm_extract_canada.csv"


def main(csv_path: str = DEFAULT_EXTRACT) -> int:
    records = load_extract(csv_path)
    report = validate_extract(records)

    print(f"Validated {report.total_records} Oracle HCM records against the ADP Canada rule catalog.")
    print(f"  Critical exceptions: {report.critical_count}")
    print(f"  Warning exceptions:  {report.warning_count}")
    print(f"  Employees flagged:   {len(report.flagged_employee_ids)}")

    if not report.exceptions:
        print("No exceptions found. Data is clean for ADP transmission.")
        return 0

    print("\nException detail:")
    for exc in report.exceptions:
        print(f"  [{exc.severity:8}] {exc.employee_id} - {exc.rule_id} ({exc.field}): {exc.message}")

    results = notify(report.exceptions, records)
    print("\nNotification results:")
    for r in results:
        print(f"  {r}")

    return 0


if __name__ == "__main__":
    csv_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXTRACT
    sys.exit(main(csv_arg))
