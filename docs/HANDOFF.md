# Fortive — Oracle HCM to ADP Celergo Data Validation Agent (Canada MVP)
## Handoff Document

Repo: `https://github.com/bensonbaby-svg/Oracle-Recruiting` (public)
Branch: `claude/fortive-data-validation-agent-gctvor`

---

## 1. Use case

Fortive uses ADP GlobalView/Celergo for payroll processing, with data sent
from Oracle HCM to ADP. Before that data is transmitted, it needs to be
validated against ADP's specifications so errors don't reach ADP.

The proposal is a lean, **Canada-scoped MVP**: an AI agent built on Oracle
AI Agent Studio that:
- **Detects and flags** — reviews Oracle HCM data against ADP
  GlobalView/Celergo specifications and flags exceptions (bad SIN format,
  invalid province code, malformed banking details, mismatched
  termination/hire dates, etc.).
- **Notifies, doesn't fix** — routes flagged items to the relevant HR/data
  owner by email for review and remediation. The agent never edits Oracle
  HCM data and never blocks or alters the existing HCM-to-ADP
  transmission — a human stays in the loop.
- **Canada only for now** — scoped to one legislative data group to
  de-risk before any broader rollout.

---

## 2. How we're approaching the POC — build and prove the logic with demo data first

Rather than starting by requesting access to Fortive's real Oracle HCM
tenant, real ADP interface specs, and real employee data (all of which
take time to arrange and involve real PII), the approach was to build the
**entire detect-and-flag pipeline against mock, de-identified data** first:

1. Write a validation rule catalog based on generally known ADP
   GlobalView/Celergo Canada requirements (SIN format/checksum, province
   codes, banking format, TD1 codes, pay groups, effective dating, etc.) —
   understanding these are **placeholders** standing in for Fortive's real
   ADP interface control document (ICD).
2. Generate a mock Oracle HCM Canada extract (17 fake employee records)
   with deliberately injected errors covering every rule, so the catalog's
   correctness can be proven before any real data is involved.
3. Build the actual detect → flag → notify pipeline against that mock
   data, with a real test suite, so the logic is demonstrably correct.
4. Wrap that logic as an MCP server — the mechanism Oracle AI Agent Studio
   uses to call custom tools — and get it deployed and reachable so it can
   actually be registered and tested inside a real Studio agent.
5. Only once this whole pipeline is proven with mock data does it make
   sense to swap in Fortive's real ADP ICD, real pay group codes, real
   HR/data-owner routing, and real (de-identified) sample records — at
   that point the same code and same registration steps apply unchanged;
   only the rule catalog's specifics and the data source change.

This means everything below is fully working and demoable *today*, with
the explicit, documented caveat that the validation rules themselves are
placeholders until Fortive's real ADP spec replaces them.

---

## 3. What has been done

**Built and tested** (all in this repo):

- **A 16-rule ADP Canada validation catalog** (`src/rules.py`) — SIN
  format/checksum, province codes, postal code format, banking format
  (institution/transit/account), TD1 claim codes, pay group/frequency,
  hire/termination/effective date logic, currency, language code, and
  mandatory fields.
- **A detect-and-flag engine** (`src/validator.py`) that runs the rule
  catalog against a batch of employee records and produces a structured
  exception report.
- **An email notification module** (`src/email_notifier.py`) that groups
  exceptions by HR/data owner and renders an HTML digest email per owner —
  dry-run by default (writes to `output/`), or sends via SMTP if
  configured.
- **A CLI demo** (`main.py`) wiring all of the above together — retrieve →
  validate → notify, the same flow the real agent will run.
- **17 mock Canada employee records** (`data/sample_hcm_extract_canada.csv`)
  with deliberately injected errors, used to prove the rule catalog works.
  This is the **input file** — a stand-in for the real Oracle HCM Canada
  payroll extract. Its 19 columns: `employee_id`, `first_name`,
  `last_name`, `sin` (9-digit, checksum-validated), `province`,
  `postal_code`, `pay_group`, `pay_frequency`, `hire_date`,
  `termination_date`, `effective_date`, `bank_institution`,
  `bank_transit`, `bank_account`, `td1_federal_claim_code`,
  `td1_provincial_claim_code`, `currency`, `language_code`,
  `employment_status`. `main.py` reads this file directly; the MCP
  server's `validate_against_adp_spec` tool instead takes records passed
  in as JSON — once wired into Studio, Studio supplies the records (pulled
  from live Fusion HCM data), not this CSV.
- **A passing test suite** (`tests/test_validator.py`, 8 tests, stdlib only).
- **An MCP server** (`mcp_server/server.py`) exposing the validation and
  notification logic as MCP tools — `validate_against_adp_spec`,
  `send_notification_email`, and a demo-only `get_hcm_extract` — built on
  the official MCP Python SDK. Verified end-to-end over the real MCP
  protocol (`initialize`, `tools/list`, `tools/call` all tested
  successfully), both locally and against a live deployment.
  - **Fixed gotcha**: the SDK's default DNS-rebinding protection only
    trusts `localhost`/`127.0.0.1` Host headers, which rejects every
    request once deployed behind a real public domain (`421 Invalid Host
    header`). This is disabled in the server's config since Studio calls
    it server-to-server over HTTPS, not from a browser session that
    protection is meant to guard.
- **Deployed to Render.com** and confirmed live (a real `initialize` call
  returned `200 OK` with the correct `serverInfo`).

**Documented** (all in `docs/`):
- `docs/architecture.md` — target end-state architecture and how each
  piece of this wireframe maps to a real Oracle AI Agent Studio component.
- `docs/adp_validation_rules_canada.md` — the rule catalog spelled out,
  plus exactly what Fortive needs to supply to replace the placeholders.
- `docs/oracle_agent_studio_setup.md` — agent instructions to paste in,
  tool registration steps (including the MCP tool type, step by step), and
  a full checklist to bring the POC to life.
- `docs/SETUP_GUIDE.md` — a start-to-finish, no-experience-assumed guide:
  installing Python/git, the virtual environment, running everything
  locally, and deploying to Render (including fixes for every real error
  hit during testing: Windows `python` vs `python3`, Git Bash venv paths,
  corporate Group Policy blocking winget, blocked `.exe` execution,
  blocked SSH tunneling, and TLS revocation-check failures).

---

## 4. What needs to be done

1. **Get your own independent deployment running** (see Section 5 —
   required since accounts aren't being shared between team members).
2. **Create the agent** in Oracle AI Agent Studio and paste the
   instructions from `docs/oracle_agent_studio_setup.md` section 1 — this
   defines the detect-and-flag, human-in-the-loop behavior.
3. **Register the validator as an MCP tool** in Studio, pointing at your
   deployed server's URL (Tools → New Tool → Tool Type: MCP).
4. **Register `get_hcm_extract` as a native Business Object tool instead**
   (recommended over routing it through MCP) — point it at the real
   Fusion HCM object holding Canada payroll fields, so the agent reads
   live Oracle HCM data directly rather than the mock CSV.
5. **Register `send_notification_email` as a native Email tool** (Fusion
   has this built in — no custom hosting needed), *or* keep using the MCP
   server's version of it if that's simpler for now.
6. **Attach Knowledge sources**: `docs/adp_validation_rules_canada.md`
   (placeholder) and, once available, Fortive's real ADP Celergo Canada ICD.
7. **Configure the scheduled trigger** — timed before Fortive's ADP
   transmission cutoff (e.g. nightly).
8. **Test in Studio's preview/test chat** — validate a sample record and
   confirm the tool-call trace succeeds and returns the expected
   exceptions.
9. **Get the real data dependencies from Fortive** before this is more
   than a demo (all placeholders currently — see
   `docs/adp_validation_rules_canada.md` for the full list):
   - The real ADP Celergo Canada ICD (replaces the placeholder rule catalog).
   - Fortive's actual Canada pay group / pay frequency codes.
   - The confirmed HR/data-owner email routing table.
   - A handful of real, de-identified Canada employee records to validate against.

Full checklist with checkboxes: `docs/oracle_agent_studio_setup.md`,
section 5.

---

## 5. How to do it — step by step

### 5a. Get the code

The repo is **public**, so no GitHub account needs to be shared and no
invite is required:
```bash
git clone https://github.com/bensonbaby-svg/Oracle-Recruiting.git
cd Oracle-Recruiting
git checkout claude/fortive-data-validation-agent-gctvor
```
No git? Go to the repo URL above, switch the branch dropdown to
`claude/fortive-data-validation-agent-gctvor`, and use **Code → Download ZIP**.

If you want your own copy to push changes to independently, **fork** the
repo to your own GitHub account first (Fork button on the repo page,
works on any public repo with no permission needed from anyone), then
clone your fork instead of the URL above.

### 5b. Run it locally

Full detail with a troubleshooting table is in `docs/SETUP_GUIDE.md` —
condensed version:
```bash
python3 -m venv .venv                 # Windows: python -m venv .venv
source .venv/bin/activate             # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt

python3 -m unittest discover -s tests -v   # should print OK, 8 tests
python3 main.py                            # runs the detect-and-flag demo
python3 mcp_server/server.py               # runs the MCP server locally on :8000
```
**Windows note:** use `python`, not `python3`, for every command above —
Windows virtual environments don't create a `python3.exe`, so `python3`
silently runs the wrong (system) Python instead of the venv, causing
`ModuleNotFoundError`. Full explanation in `docs/SETUP_GUIDE.md`.

### 5c. Deploy your own MCP server (independent Render deployment)

Since accounts (GitHub, Render) aren't being shared between team members,
each person deploys their **own** instance from the same public code —
no invite, no shared login, no coordination required:

1. Fork the repo to your own GitHub account (see 5a) if you haven't already.
2. Go to [render.com](https://render.com), sign up/log in with your own
   GitHub account.
3. **New +** → **Web Service** → connect your fork (or paste the public
   repo URL directly if Render offers that option).
4. **Branch**: `claude/fortive-data-validation-agent-gctvor`.
5. **Environment**: Python 3. **Build Command**: `pip install -r requirements.txt`.
   **Start Command**: `python mcp_server/server.py`.
6. **Instance Type**: free tier is fine for a demo.
7. **Create Web Service** — Render builds and deploys automatically,
   giving you a URL like `https://your-app-name.onrender.com`.
8. Your MCP endpoint for Studio is that URL plus `/mcp`.

**Verify it** (works from any machine, no local setup needed):
```bash
curl -i --ssl-no-revoke -X POST https://your-app-name.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
Expect `HTTP/1.1 200 OK` with `"serverInfo":{"name":"fortive-hcm-adp-validator"...}`.
(`--ssl-no-revoke` works around a Windows/corporate-proxy TLS
revocation-check quirk — omit it if you're not on Windows or don't hit that error.)

**Free-tier note:** Render spins the service down after inactivity; the
first request after idle time can take 30-60 seconds to wake back up —
expected, not a bug.

### 5d. Register it in Oracle AI Agent Studio

Full click-by-click steps: `docs/oracle_agent_studio_setup.md` section 2a.
Condensed:
1. Tools tab → **New Tool** → Tool Type: **MCP**.
2. Paste your Render URL + `/mcp` as the endpoint.
3. Select which tool(s) to expose (`validate_against_adp_spec` at minimum;
   `send_notification_email` and `get_hcm_extract` optionally — see
   Section 4, items 4-5, for the recommended native alternatives to those two).
4. Leave "Require human approval" off for the validator (read-only).
5. Create, attach to the agent, and test in Studio's preview chat.

---

## 6. Known issues already solved (so you don't have to re-debug them)

| Issue | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Virtual environment not activated, or (Windows) typed `python3` instead of `python` | Activate the venv; on Windows use `python`, never `python3` |
| `.venv/bin/activate: No such file or directory` (Windows) | Windows uses `Scripts/`, not `bin/` | `source .venv/Scripts/activate` (Git Bash) |
| `This operation is disabled by Group Policy` (winget) | Corporate policy blocks the Windows Package Manager | Skip local tunnel tooling entirely — deploy to Render instead (Section 5c) |
| Downloaded `.exe` won't run | Corporate endpoint security blocks new executables | Same — deploy to Render instead |
| `Connection to localhost.run closed.` (SSH tunnel) | Corporate network blocks/kills SSH port-forwarding | Same — deploy to Render instead |
| `curl: (35) schannel: ... CRYPT_E_NO_REVOCATION_CHECK` | Windows TLS revocation check fails behind a corporate SSL-inspecting proxy | Add `--ssl-no-revoke` to the curl command |
| `421 Misdirected Request` / `Invalid Host header` on the deployed server | MCP SDK's DNS-rebinding protection only trusts `localhost` Host headers | Already fixed in `mcp_server/server.py` via `TransportSecuritySettings(enable_dns_rebinding_protection=False)` — carries over automatically since you're using the same code |

Full troubleshooting table (more detail per row): `docs/SETUP_GUIDE.md`.

---

## 7. Repo map

| Path | What it is |
|---|---|
| `main.py` | CLI demo: retrieve → validate → notify |
| `src/rules.py` | ADP Canada validation rule catalog |
| `src/validator.py` | Loads the extract, applies the rule catalog |
| `src/email_notifier.py` | Groups exceptions by data owner, renders/sends the email |
| `mcp_server/server.py` | MCP server — deploy this to get a Studio-registerable URL |
| `data/sample_hcm_extract_canada.csv` | Mock Canada employee data with injected errors |
| `tests/test_validator.py` | Test suite |
| `requirements.txt` | Python dependencies (just `mcp`) |
| `docs/architecture.md` | Target architecture and wireframe-to-Studio mapping |
| `docs/adp_validation_rules_canada.md` | Rule catalog detail + what Fortive needs to supply |
| `docs/oracle_agent_studio_setup.md` | Agent instructions, tool registration steps, full checklist |
| `docs/SETUP_GUIDE.md` | Full local setup + Render deployment walkthrough + troubleshooting |
| `docs/HANDOFF.md` | This document |
