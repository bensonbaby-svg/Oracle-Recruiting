"""
Detect-and-flag validation engine.

Reads an Oracle HCM data extract (the wireframe stand-in for the real HCM ->
ADP Celergo interface extract), runs the ADP Canada rule catalog against every
record, and returns a structured exception report. This module is the piece
that, in the real build, becomes the Oracle AI Agent Studio "tool" the agent
calls after retrieving the extract (see docs/oracle_agent_studio_setup.md).
"""
import csv
from dataclasses import dataclass, field

from .rules import ValidationException, validate_record


@dataclass
class ValidationReport:
    total_records: int
    exceptions: list[ValidationException] = field(default_factory=list)

    @property
    def flagged_employee_ids(self) -> list[str]:
        seen = []
        for exc in self.exceptions:
            if exc.employee_id not in seen:
                seen.append(exc.employee_id)
        return seen

    @property
    def critical_count(self) -> int:
        return sum(1 for e in self.exceptions if e.severity == "Critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.exceptions if e.severity == "Warning")


def load_extract(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_extract(records: list[dict]) -> ValidationReport:
    report = ValidationReport(total_records=len(records))
    for record in records:
        report.exceptions.extend(validate_record(record))
    return report


def run_validation(csv_path: str) -> ValidationReport:
    records = load_extract(csv_path)
    return validate_extract(records)
