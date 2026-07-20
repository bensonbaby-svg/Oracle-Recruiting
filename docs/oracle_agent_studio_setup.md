# Oracle AI Agent Studio — Build Guide

This translates the wireframe in this repo into the artifacts you configure
directly inside Oracle AI Agent Studio. Exact menu labels vary slightly by
release/pod — confirm against your tenant's current Agent Studio docs — but
the four building blocks (Instructions, Tools, Knowledge, Trigger) are stable.

## 1. Agent instructions (persona / system prompt)

Paste as the agent's instructions:

```
You are the Fortive Oracle HCM to ADP Celergo Data Validation Agent
(Canada MVP). Your job is to detect and flag data quality issues in the
Oracle HCM Canada data extract before it is transmitted to ADP
GlobalView/Celergo. You operate on a detect-and-flag model only:

- You NEVER modify Oracle HCM data.
- You NEVER transmit, block, or alter the HCM-to-ADP interface.
- You ALWAYS route exceptions to the relevant HR/data owner by email and
  leave remediation to that person.

For each run:
1. Call get_hcm_extract to retrieve the current Canada data extract.
2. Call validate_against_adp_spec against the retrieved records.
3. If any exceptions are returned, call send_notification_email once per
   affected data owner with the exceptions grouped by employee, ranked
   Critical before Warning.
4. If there are no exceptions, log a clean run and take no further action.

Do not attempt to guess correct values or fix data yourself. If a tool call
fails, report the failure rather than retrying silently more than once.
```

## 2. Tools (function definitions)

Register three tools/functions. Each maps 1:1 to a module in `src/`.

### get_hcm_extract
- Backing implementation: REST call to the staged extract (OIC integration
  or Object Storage read), or a Fusion custom function wrapping an HCM
  Extract/OTBI report.
- Wireframe equivalent: `src.validator.load_extract(csv_path)`

```json
{
  "name": "get_hcm_extract",
  "description": "Retrieve the current Oracle HCM Canada payroll data extract staged for ADP validation.",
  "parameters": {
    "type": "object",
    "properties": {
      "extract_date": {"type": "string", "format": "date", "description": "Extract date to retrieve, defaults to latest"}
    }
  }
}
```

### validate_against_adp_spec
- Backing implementation: the rule catalog in `src/rules.py` / `src/validator.py`,
  deployed as a callable function (Fusion custom function, OIC integration,
  or an externally hosted REST endpoint the agent calls as a tool).
- Wireframe equivalent: `src.validator.validate_extract(records)`

```json
{
  "name": "validate_against_adp_spec",
  "description": "Validate Oracle HCM Canada employee records against the ADP GlobalView/Celergo interface specification and return flagged exceptions.",
  "parameters": {
    "type": "object",
    "properties": {
      "records": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["records"]
  }
}
```

### send_notification_email
- Backing implementation: OIC "send email" action or Fusion BI Publisher
  email delivery.
- Wireframe equivalent: `src.email_notifier.notify(exceptions, records)`

```json
{
  "name": "send_notification_email",
  "description": "Send an exception digest email to the HR/data owner responsible for the flagged records.",
  "parameters": {
    "type": "object",
    "properties": {
      "recipient": {"type": "string", "format": "email"},
      "exceptions": {"type": "array", "items": {"type": "object"}}
    },
    "required": ["recipient", "exceptions"]
  }
}
```

## 3. Knowledge

Attach as Knowledge sources (for grounding, not as executable rules):
- The ADP Celergo Canada interface control document (ICD).
- `docs/adp_validation_rules_canada.md` (until the real ICD replaces it).
- Fortive's HR/data-owner routing table.

## 4. Trigger

Canada MVP runs on a schedule tied to the pre-payroll cutoff (e.g. nightly,
or X hours before the ADP transmission window) so flagged issues can be
remediated before that cycle's file goes out. Configure as a scheduled
trigger rather than event-driven for the MVP; revisit event-driven triggers
(e.g. on HCM data change) post-MVP.

## 5. POC acceptance checklist

- [ ] Agent instructions loaded, tools registered and independently testable.
- [ ] Rule catalog validated against Fortive's real ADP Canada ICD (replaces
      the placeholder in `docs/adp_validation_rules_canada.md`).
- [ ] Data-owner routing table confirmed with Fortive HR.
- [ ] Dry run against a real (de-identified) Canada extract produces the
      expected exception set, reviewed by Fortive payroll/HR SMEs.
- [ ] Email digest format/content approved by the receiving HR/data owners.
- [ ] Scheduled trigger timed correctly against the ADP transmission cutoff.
- [ ] Runbook for "agent fails / tool errors" escalation path agreed.

## What this repo gives you today vs. what's still needed for a live Studio agent

**Already built (runnable now):** the full detect-and-flag logic, a Canada
rule catalog, sample data with injected errors, and the email digest
rendering — run `python main.py` to see it end to end.

**Still needed before standing this up in the real Oracle AI Agent Studio:**
1. Access to a Fortive/Deloitte Oracle Fusion tenant with AI Agent Studio
   enabled, to actually create the agent, tools, and knowledge sources.
2. The real ADP Celergo Canada ICD to replace the placeholder rule catalog.
3. A working extract mechanism (HCM Extract, OTBI, or BIP report) from
   Fortive's Oracle HCM instance, and a way to stage/expose it to the agent
   (OIC, Object Storage, or direct Fusion custom function).
4. An approved email routing table and SMTP/notification channel
   (Fortive's own, or via OIC email action).
5. A handful of real (de-identified) Canada employee records to validate the
   rule catalog against before demoing to Fortive stakeholders.
