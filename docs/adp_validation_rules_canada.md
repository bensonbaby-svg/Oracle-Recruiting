# ADP GlobalView/Celergo (Canada) — Validation Rule Catalog (placeholder)

Implemented in `src/rules.py`. Each rule below is illustrative, built from
generally known Canadian payroll interface requirements — **not** taken from
Fortive's actual ADP interface control document (ICD), which Deloitte/Fortive
must supply before this moves past wireframe stage.

| Rule ID | Field(s) | Severity | Check |
|---------|----------|----------|-------|
| R001 | sin | Critical | SIN must be exactly 9 numeric digits |
| R002 | sin | Critical | SIN must pass the Luhn checksum (standard CRA SIN validation algorithm) |
| R003 | province | Critical | Must be a valid CA province/territory code (ON, QC, BC, AB, MB, SK, NS, NB, NL, PE, YT, NT, NU) |
| R004 | postal_code | Warning | Must match Canadian postal code format `A1A 1A1` |
| R005 | pay_group | Critical | Must be one of Fortive's configured Canada pay groups |
| R006 | pay_frequency | Warning | Must be one of Weekly / Bi-Weekly / Semi-Monthly / Monthly |
| R007 | hire_date, effective_date | Critical | Effective date cannot precede hire date |
| R008 | termination_date, hire_date, employment_status | Critical/Warning | Termination date can't precede hire date; if set, status should be "Terminated" |
| R009 | employment_status, termination_date | Critical | "Active" status cannot coexist with a termination date |
| R010 | bank_institution | Critical | Must be 3 numeric digits |
| R011 | bank_transit | Critical | Must be 5 numeric digits |
| R012 | bank_account | Critical | Must be 5-12 numeric digits |
| R013 | td1_federal_claim_code, td1_provincial_claim_code | Warning | Must be numeric 0-10, or "E" (exempt) |
| R014 | currency | Critical | Must be CAD (Canada-scoped MVP) |
| R015 | language_code | Warning | Must be EN or FR |
| R016 | employee_id, first_name, last_name, sin, province, pay_group, pay_frequency, hire_date, employment_status | Critical | Mandatory fields must not be blank |

## What Fortive/Deloitte needs to supply to replace the placeholders

1. The ADP Celergo Canada interface control document (field list, formats,
   required vs. optional, code value sets) — this directly becomes the
   Agent's Knowledge source and the authoritative rule catalog.
2. Fortive's actual Canada pay group and pay frequency code lists.
3. The HR/data-owner routing table (who gets notified for which
   province/business unit/pay group).
4. Sample (de-identified) Oracle HCM extract output in the real interface
   layout, so field names/types here can be reconciled against production.
5. Confirmation of the extract delivery mechanism (HCM Extract to OIC,
   BI Publisher report, flat file to SFTP, etc.) so the "get_hcm_extract"
   tool is built against the right source.
