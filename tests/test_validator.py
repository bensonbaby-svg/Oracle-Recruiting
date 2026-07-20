"""Stdlib-only test suite (no pytest dependency) for the validation engine."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rules import validate_record
from src.validator import load_extract, validate_extract

SAMPLE_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "sample_hcm_extract_canada.csv")


class TestRules(unittest.TestCase):
    def base_record(self, **overrides):
        record = {
            "employee_id": "E9999",
            "first_name": "Test",
            "last_name": "Employee",
            "sin": "100000009",
            "province": "ON",
            "postal_code": "M5V 2T6",
            "pay_group": "CA-ON-BIWK",
            "pay_frequency": "Bi-Weekly",
            "hire_date": "2022-01-01",
            "termination_date": "",
            "effective_date": "2022-01-01",
            "bank_institution": "003",
            "bank_transit": "12345",
            "bank_account": "123456789",
            "td1_federal_claim_code": "1",
            "td1_provincial_claim_code": "1",
            "currency": "CAD",
            "language_code": "EN",
            "employment_status": "Active",
        }
        record.update(overrides)
        return record

    def test_clean_record_has_no_exceptions(self):
        self.assertEqual(validate_record(self.base_record()), [])

    def test_bad_sin_format_flagged(self):
        exceptions = validate_record(self.base_record(sin="12345"))
        self.assertTrue(any(e.rule_id == "R001" for e in exceptions))

    def test_bad_sin_checksum_flagged(self):
        exceptions = validate_record(self.base_record(sin="123456789"))
        self.assertTrue(any(e.rule_id == "R002" for e in exceptions))

    def test_invalid_province_flagged(self):
        exceptions = validate_record(self.base_record(province="XX"))
        self.assertTrue(any(e.rule_id == "R003" for e in exceptions))

    def test_hire_after_effective_flagged(self):
        exceptions = validate_record(self.base_record(hire_date="2023-01-01", effective_date="2022-01-01"))
        self.assertTrue(any(e.rule_id == "R007" for e in exceptions))

    def test_active_with_termination_date_flagged(self):
        exceptions = validate_record(self.base_record(termination_date="2024-01-01", employment_status="Active"))
        self.assertTrue(any(e.rule_id == "R009" for e in exceptions))

    def test_missing_required_field_flagged(self):
        exceptions = validate_record(self.base_record(first_name=""))
        self.assertTrue(any(e.rule_id == "R016" for e in exceptions))


class TestSampleExtract(unittest.TestCase):
    def test_sample_extract_produces_expected_exception_volume(self):
        records = load_extract(SAMPLE_CSV)
        report = validate_extract(records)
        # 2 clean records (E1001, E1002) out of 17; the rest each carry >=1 flag.
        self.assertEqual(report.total_records, 17)
        self.assertGreaterEqual(len(report.flagged_employee_ids), 14)
        self.assertNotIn("E1001", report.flagged_employee_ids)
        self.assertNotIn("E1002", report.flagged_employee_ids)


if __name__ == "__main__":
    unittest.main()
