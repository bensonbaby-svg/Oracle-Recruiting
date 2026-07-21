# Oracle AI Agent Studio — Build Guide

This translates the wireframe in this repo into the artifacts you configure
directly inside Oracle Fusion's **AI Agent Studio**. Confirmed against the
real "New Tool" screen (Tool Type options: Business Object, Connector, Deep
Link, Document, Email, External REST, MCP) — exact labels can still shift by
pod/release, but the shape below is what to expect.

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

## 2. Tools

Register three tools. Each maps to a native Fusion tool type where one
exists, falling back to a hosted service only where it doesn't.

### get_hcm_extract -> Tool Type: **Business Object**
Point this at the Fusion HCM business object holding the Canada payroll
fields (SIN, province, pay group, banking, TD1 codes, hire/termination
dates). No custom hosting needed — Studio queries Oracle HCM data directly.
Wireframe equivalent: `src.validator.load_extract(csv_path)`.

### validate_against_adp_spec -> Tool Type: **MCP** (recommended) or **External REST**
This is the one piece of custom logic (the rule catalog) with no native
Fusion equivalent — it has to be hosted somewhere Studio can call. This
repo includes a ready-to-run MCP server: `mcp_server/server.py`. See
**Section 2a** below for exact registration steps.
Wireframe equivalent: `src.validator.validate_extract(records)`.

### send_notification_email -> Tool Type: **Email**
Fusion has a native Email tool type — no OIC/custom hosting required.
Configure the recipient and template directly in Studio.
Wireframe equivalent: `src.email_notifier.notify(exceptions, records)`
(the MCP server also exposes this as a tool, in case you'd rather run
notification through MCP too instead of the native Email type — pick one).

### Optional: remediation link -> Tool Type: **Deep Link**
Send the HR/data owner straight to the flagged worker's record in Fusion
instead of (or alongside) the email digest.

## 2a. Registering `validate_against_adp_spec` as an MCP tool — step by step

**Host the MCP server somewhere Studio can reach it:**
1. This repo's `mcp_server/server.py` is a working MCP server (built on the
   official `mcp` Python SDK) exposing `validate_against_adp_spec`,
   `send_notification_email`, and a demo-only `get_hcm_extract`. It's
   already been tested end-to-end over the real MCP protocol
   (initialize -> tools/list -> tools/call all verified).
2. Install dependencies: `pip install -r requirements.txt`.
3. Run it as a network service: `python3 mcp_server/server.py` — this
   serves streamable-HTTP MCP at `http://<host>:8000/mcp`. For a real POC,
   deploy this to somewhere with a stable, Studio-reachable URL: an OCI
   Compute instance, an OCI Container Instance/Function, or any small VM —
   it just needs to keep running and be reachable over HTTPS from Fusion.
   Put a reverse proxy/TLS in front of it (e.g. via a load balancer) since
   Fusion SaaS will expect an `https://` endpoint, not raw HTTP.
4. If Fortive's network policy requires an allowlisted domain for outbound
   calls from Fusion, get that URL/domain approved before registering the
   tool (check with Fortive's Oracle Cloud/network team).

**Register it in Studio:**
5. Agent Studio -> your agent -> **Tools** tab -> **New Tool**.
6. **Tool Type**: `MCP`.
7. **Tool Name**: `validate_against_adp_spec` (or a family-prefixed name if
   your tenant enforces a naming convention).
8. **Family**: whatever grouping your tenant uses (check the dropdown —
   this wasn't visible from the initial screenshot; likely a business-area
   or agent-project grouping).
9. Provide the MCP server's URL (`https://<your-host>/mcp`) when prompted
   for the MCP endpoint/connection.
10. Studio should introspect the server and list its available tools
    (`validate_against_adp_spec`, `send_notification_email`,
    `get_hcm_extract`) — select which one(s) this Tool entry exposes to the
    agent. If Studio requires one Tool registration per MCP tool rather than
    a single connection exposing all three, repeat steps 5-9 for each.
11. **Description**: use the docstring already in `mcp_server/server.py` —
    it's written specifically so the agent's LLM knows when to call it.
12. **Require human approval**: leave off for the validator (read-only,
    non-destructive). Consider turning it on for `send_notification_email`
    during initial testing so nothing emails a real inbox before the rule
    catalog is validated.
13. **Create**, then attach/enable this tool on the agent if Studio
    requires an explicit attach step separate from creation.
14. Test via Studio's preview/test chat — ask it to validate a sample
    record and confirm the trace shows a successful `tools/call` to
    `validate_against_adp_spec` with the expected exceptions back.

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

## 5. Complete checklist to bring this POC to life

**Access/environment**
- [ ] Confirm AI Agent Studio is licensed/visible in the target Fusion tenant
      (Navigator -> look for "AI Agent Studio"); if not visible, escalate to
      Oracle account team/CSM before anything else.
- [ ] Confirm your Fusion role includes AI Agent Studio admin/build privileges.
- [ ] Somewhere to host `mcp_server/server.py` reachable via HTTPS from
      Fusion (OCI Compute/Container/Function or equivalent), with a domain
      Fortive's network policy allows Fusion to call outbound.

**Build**
- [ ] Create the agent, paste instructions (Section 1).
- [ ] Register `get_hcm_extract` as a **Business Object** tool against the
      real Fusion HCM Canada payroll object.
- [ ] Deploy `mcp_server/server.py`, register `validate_against_adp_spec` as
      an **MCP** tool (Section 2a).
- [ ] Register `send_notification_email` as a native **Email** tool (or via
      the same MCP server if you prefer one integration path).
- [ ] Attach Knowledge sources (Section 3).
- [ ] Configure the scheduled trigger (Section 4).

**Data/spec dependencies (replace this repo's placeholders)**
- [ ] Real ADP Celergo Canada interface control document (ICD) — replaces
      `docs/adp_validation_rules_canada.md` and the rule catalog in
      `src/rules.py`.
- [ ] Fortive's actual Canada pay group / pay frequency code lists
      (`VALID_PAY_GROUPS` in `src/rules.py` is a placeholder).
- [ ] Confirmed HR/data-owner routing table (`DATA_OWNER_ROUTING` in
      `src/email_notifier.py` is a placeholder).
- [ ] A handful of real, de-identified Canada employee records to validate
      the rule catalog against before demoing to Fortive stakeholders.

**Test and sign off**
- [ ] Run the agent end-to-end in Studio's preview chat; confirm the tool
      call sequence (get_hcm_extract -> validate_against_adp_spec ->
      send_notification_email) fires correctly and only when there are
      exceptions.
- [ ] Dry run against real (de-identified) data, reviewed by Fortive
      payroll/HR SMEs for correctness and false-positive rate.
- [ ] Email digest format/content approved by the receiving HR/data owners.
- [ ] Scheduled trigger timed correctly against the ADP transmission cutoff.
- [ ] Runbook agreed for "agent fails / tool errors" escalation.
- [ ] Publish/activate the agent; assign to the correct role/user group.

## What this repo gives you today vs. what's still needed

**Already built and tested (runnable now):**
- Full detect-and-flag logic with a 16-rule Canada catalog (`src/rules.py`).
- Sample data with injected errors, CLI demo (`python3 main.py`), and a
  passing test suite (`tests/test_validator.py`).
- A working MCP server (`mcp_server/server.py`) exposing the validation and
  notification logic — verified end-to-end over the real MCP protocol
  (initialize, tools/list, and tools/call all tested successfully).

**Still needed to go live:**
1. AI Agent Studio access in a real Fortive/Deloitte Fusion tenant.
2. A hosting location for the MCP server reachable over HTTPS from Fusion.
3. The real ADP Celergo Canada ICD, pay group list, and HR routing table.
4. Real (de-identified) Canada extract data for validation testing.
