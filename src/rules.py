"""
ADP GlobalView/Celergo (Canada) validation rule catalog.

These rules are ILLUSTRATIVE placeholders for the wireframe/POC. Before a real
build, replace REQUIRED_FIELDS / VALID_* lookups and thresholds below with the
actual field-level specification from Fortive's ADP Celergo interface control
document (ICD) and Fortive's own pay group / earnings-code configuration.
"""
from dataclasses import dataclass
from datetime import date

CRITICAL = "Critical"
WARNING = "Warning"

VALID_PROVINCES = {"ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "NL", "PE", "YT", "NT", "NU"}
VALID_PAY_FREQUENCIES = {"Weekly", "Bi-Weekly", "Semi-Monthly", "Monthly"}
VALID_LANGUAGE_CODES = {"EN", "FR"}
VALID_EMPLOYMENT_STATUS = {"Active", "Terminated", "Leave"}

# Placeholder: Fortive Canada pay groups (to be replaced with client-confirmed list)
VALID_PAY_GROUPS = {"CA-ON-BIWK", "CA-QC-BIWK", "CA-BC-BIWK", "CA-AB-MTHLY"}

REQUIRED_FIELDS = [
    "employee_id", "first_name", "last_name", "sin", "province",
    "pay_group", "pay_frequency", "hire_date", "employment_status",
]


@dataclass
class ValidationException:
    employee_id: str
    rule_id: str
    severity: str
    field: str
    message: str


def _parse_date(value):
    if not value:
        return None
    return date.fromisoformat(value)


def _sin_luhn_valid(sin: str) -> bool:
    digits = [int(c) for c in sin]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_record(record: dict) -> list[ValidationException]:
    """Apply the full ADP Canada rule catalog to a single Oracle HCM extract row."""
    exceptions: list[ValidationException] = []
    emp_id = record.get("employee_id", "UNKNOWN")

    def flag(rule_id, severity, field, message):
        exceptions.append(ValidationException(emp_id, rule_id, severity, field, message))

    # R016 - mandatory fields present
    for field in REQUIRED_FIELDS:
        if not record.get(field):
            flag("R016", CRITICAL, field, f"Required field '{field}' is missing.")

    sin = record.get("sin", "")
    if sin:
        if not (sin.isdigit() and len(sin) == 9):
            flag("R001", CRITICAL, "sin", f"SIN '{sin}' must be exactly 9 digits.")
        elif not _sin_luhn_valid(sin):
            flag("R002", CRITICAL, "sin", f"SIN '{sin}' fails Luhn checksum validation.")

    province = record.get("province", "")
    if province and province not in VALID_PROVINCES:
        flag("R003", CRITICAL, "province", f"Province code '{province}' is not a recognized CA province/territory.")

    postal_code = record.get("postal_code", "")
    if postal_code:
        import re
        if not re.match(r"^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$", postal_code):
            flag("R004", WARNING, "postal_code", f"Postal code '{postal_code}' does not match Canadian format A1A 1A1.")

    pay_group = record.get("pay_group", "")
    if pay_group and pay_group not in VALID_PAY_GROUPS:
        flag("R005", CRITICAL, "pay_group", f"Pay group '{pay_group}' is not a recognized Fortive Canada pay group.")

    pay_frequency = record.get("pay_frequency", "")
    if pay_frequency and pay_frequency not in VALID_PAY_FREQUENCIES:
        flag("R006", WARNING, "pay_frequency", f"Pay frequency '{pay_frequency}' is not a recognized value.")

    hire_date = _parse_date(record.get("hire_date"))
    effective_date = _parse_date(record.get("effective_date"))
    termination_date = _parse_date(record.get("termination_date"))
    employment_status = record.get("employment_status", "")

    if hire_date and effective_date and hire_date > effective_date:
        flag("R007", CRITICAL, "effective_date", "Effective date is earlier than hire date.")

    if termination_date:
        if hire_date and termination_date < hire_date:
            flag("R008", CRITICAL, "termination_date", "Termination date is earlier than hire date.")
        if employment_status != "Terminated":
            flag("R008", WARNING, "employment_status", "Termination date is set but employment status is not 'Terminated'.")

    if employment_status == "Active" and termination_date:
        flag("R009", CRITICAL, "termination_date", "Employment status is 'Active' but a termination date is present.")

    bank_institution = record.get("bank_institution", "")
    if bank_institution and not (bank_institution.isdigit() and len(bank_institution) == 3):
        flag("R010", CRITICAL, "bank_institution", f"Bank institution number '{bank_institution}' must be 3 digits.")

    bank_transit = record.get("bank_transit", "")
    if bank_transit and not (bank_transit.isdigit() and len(bank_transit) == 5):
        flag("R011", CRITICAL, "bank_transit", f"Bank transit number '{bank_transit}' must be 5 digits.")

    bank_account = record.get("bank_account", "")
    if bank_account and not (bank_account.isdigit() and 5 <= len(bank_account) <= 12):
        flag("R012", CRITICAL, "bank_account", f"Bank account number '{bank_account}' must be 5-12 digits.")

    for field in ("td1_federal_claim_code", "td1_provincial_claim_code"):
        value = record.get(field, "")
        if value and value != "E":
            try:
                code = int(value)
                if not (0 <= code <= 10):
                    flag("R013", WARNING, field, f"TD1 claim code '{value}' is outside expected range 0-10.")
            except ValueError:
                flag("R013", WARNING, field, f"TD1 claim code '{value}' is not numeric or 'E' (exempt).")

    currency = record.get("currency", "")
    if currency and currency != "CAD":
        flag("R014", CRITICAL, "currency", f"Currency '{currency}' is invalid for Canada-scoped MVP; expected CAD.")

    language_code = record.get("language_code", "")
    if language_code and language_code not in VALID_LANGUAGE_CODES:
        flag("R015", WARNING, "language_code", f"Language code '{language_code}' is not one of {sorted(VALID_LANGUAGE_CODES)}.")

    return exceptions
