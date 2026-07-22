# Handoff — Fortive Oracle HCM to ADP Celergo Data Validation Agent (Canada MVP)

Status as of the date this was last updated: MCP server built, tested, and
deployed to Render — **confirmed live and responding correctly** at
`https://mcp-server-data-validation.onrender.com/mcp` (verified with a real
`initialize` call returning `200 OK`). Next step is registering it in
Oracle AI Agent Studio and finishing the remaining tool/knowledge/trigger
configuration there.

---

## 1. The use case

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

## 2. What's been done so far

**Built and tested (all in this repo, branch `claude/fortive-data-validation-agent-gctvor`):**

- **A 16-rule ADP Canada validation catalog** (`src/rules.py`) covering SIN
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
- **A CLI demo** (`main.py`) wiring all of the above together — this is
  the same retrieve → validate → notify flow the real agent will run.
- **17 mock Canada employee records** (`data/sample_hcm_extract_canada.csv`)
  with deliberately injected errors, used to prove the rule catalog works.
- **A passing test suite** (`tests/test_validator.py`, 8 tests, stdlib only).
- **An MCP server** (`mcp_server/server.py`) exposing the validation and
  notification logic as MCP tools — `validate_against_adp_spec`,
  `send_notification_email`, and a demo-only `get_hcm_extract` — built on
  the official MCP Python SDK. Verified end-to-end over the real MCP
  protocol (`initialize`, `tools/list`, `tools/call` all tested
  successfully), both locally and against the live Render deployment.
  (One gotcha already fixed: the SDK's default DNS-rebinding protection
  only trusts `localhost`/`127.0.0.1` Host headers, which rejected every
  request once deployed behind Render's public domain with a `421 Invalid
  Host header` error. It's disabled in this server's config since Studio
  calls it server-to-server over HTTPS, not from a browser session that
  protection is meant to guard. If you ever recreate this server from
  scratch, make sure that fix carries over.)
- **Deployed the MCP server to Render.com**, giving it a public HTTPS
  endpoint Oracle AI Agent Studio can call:
  **`https://mcp-server-data-validation.onrender.com/mcp`**.

**Documented (also in this repo, under `docs/`):**
- `docs/architecture.md` — target end-state architecture and how each
  piece of this wireframe maps to a real Oracle AI Agent Studio component.
- `docs/adp_validation_rules_canada.md` — the rule catalog spelled out,
  plus exactly what Fortive needs to supply to replace the placeholders.
- `docs/oracle_agent_studio_setup.md` — agent instructions to paste in,
  tool registration steps (including the MCP tool type, step by step), and
  a full checklist to bring the POC to life.
- `docs/SETUP_GUIDE.md` — a start-to-finish, no-experience-assumed guide:
  installing Python/git, the virtual environment, running everything
  locally, and deploying to Render.

---

## 3. What's remaining — your coworker's next steps

The MCP server is already live at **`https://mcp-server-data-validation.onrender.com/mcp`** — your coworker
does **not** need to redeploy anything. Their job is to finish wiring the
agent together inside Oracle AI Agent Studio:

1. **Create the agent** in Oracle AI Agent Studio (e.g. name it
   "HCM-ADP-CA-Validator") and paste the instructions from
   `docs/oracle_agent_studio_setup.md` section 1 — this defines the
   detect-and-flag, human-in-the-loop behavior.

2. **Register the validator as an MCP tool** — this is the main
   remaining action:
   - Tools tab → **New Tool** → Tool Type: **MCP**
   - Paste the endpoint: **`https://mcp-server-data-validation.onrender.com/mcp`**
   - Studio should introspect the server and list its tools
     (`validate_against_adp_spec`, `send_notification_email`,
     `get_hcm_extract`) — select which to expose (may need one Tool
     registration per MCP tool depending on how Studio's UI handles it).
   - Use the descriptions already written into `mcp_server/server.py`'s
     docstrings — full step-by-step is in
     `docs/oracle_agent_studio_setup.md` section 2a.

3. **Register `get_hcm_extract` as a native Business Object tool instead**
   (recommended over routing it through MCP) — point it at the real
   Fusion HCM object holding Canada payroll fields, so the agent reads
   live Oracle HCM data directly rather than the mock CSV.

4. **Register `send_notification_email` as a native Email tool** (Fusion
   has this built in — no custom hosting needed), *or* keep using the MCP
   server's version of it if that's simpler for now.

5. **Attach Knowledge sources**: `docs/adp_validation_rules_canada.md`
   (placeholder) and, once available, Fortive's real ADP Celergo Canada
   interface control document (ICD).

6. **Configure the scheduled trigger** — timed before Fortive's ADP
   transmission cutoff (e.g. nightly).

7. **Test in Studio's preview/test chat** — validate a sample record and
   confirm the tool-call trace hits `https://mcp-server-data-validation.onrender.com/mcp` successfully and
   returns the expected exceptions.

8. **Data dependencies still needed from Fortive** before this is more
   than a demo (all placeholders currently, see
   `docs/adp_validation_rules_canada.md` for the full list):
   - The real ADP Celergo Canada ICD (replaces the placeholder rule catalog).
   - Fortive's actual Canada pay group / pay frequency codes.
   - The confirmed HR/data-owner email routing table.
   - A handful of real, de-identified Canada employee records to validate against.

Full checklist with checkboxes: `docs/oracle_agent_studio_setup.md`,
section 5.

---

## 4. How to run this locally (for your coworker to explore/modify the code)

Full detail with troubleshooting is in `docs/SETUP_GUIDE.md` — condensed
version here:

```bash
git clone https://github.com/bensonbaby-svg/Oracle-Recruiting.git
cd Oracle-Recruiting
git checkout claude/fortive-data-validation-agent-gctvor

python3 -m venv .venv                 # Windows: python -m venv .venv
source .venv/bin/activate             # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt

python3 -m unittest discover -s tests -v   # should print OK, 8 tests
python3 main.py                            # runs the detect-and-flag demo
python3 mcp_server/server.py                # runs the MCP server locally on :8000
```
**Windows note:** use `python`, not `python3`, for every command above —
Windows virtual environments don't create a `python3.exe`, so `python3`
silently runs the wrong (system) Python instead of the venv, causing
`ModuleNotFoundError`. Full explanation in `docs/SETUP_GUIDE.md`.

They don't need to redeploy to Render unless they're changing the MCP
server's code — the live one at `https://mcp-server-data-validation.onrender.com/mcp` is already what Studio
should point at.

---

## 5. Repo map

| Path | What it is |
|---|---|
| `main.py` | CLI demo: retrieve → validate → notify |
| `src/rules.py` | ADP Canada validation rule catalog |
| `src/validator.py` | Loads the extract, applies the rule catalog |
| `src/email_notifier.py` | Groups exceptions by data owner, renders/sends the email |
| `mcp_server/server.py` | MCP server — this is what's deployed on Render |
| `data/sample_hcm_extract_canada.csv` | Mock Canada employee data with injected errors |
| `tests/test_validator.py` | Test suite |
| `requirements.txt` | Python dependencies (just `mcp`) |
| `docs/architecture.md` | Target architecture and wireframe-to-Studio mapping |
| `docs/adp_validation_rules_canada.md` | Rule catalog detail + what Fortive needs to supply |
| `docs/oracle_agent_studio_setup.md` | Agent instructions, tool registration steps, full checklist |
| `docs/SETUP_GUIDE.md` | Full local setup + Render deployment walkthrough |
| `docs/HANDOFF.md` | This document |

---

## 6. Render access / continuity while the primary owner is out

The MCP server is deployed under one Render account. Your coworker should
**not** spin up a second Render service from this repo "just in case" —
that creates a second URL, and Studio would need re-registering against
whichever one is actually being maintained. Instead:

- **For routine code fixes**: if auto-deploy is enabled on the Render
  service (Render dashboard → service → Settings → Build & Deploy →
  Auto-Deploy), any push to `claude/fortive-data-validation-agent-gctvor`
  redeploys automatically. Anyone with push access to this GitHub repo can
  fix code without ever touching Render directly.
- **For anything Render-dashboard-specific** (checking logs, a manual
  deploy if auto-deploy is off, environment variables, restarting the
  service, diagnosing an outage): the coworker needs to be added to the
  Render account/team itself — Render dashboard → Account/Team Settings →
  Members → Invite by email. This gives them the same service, not a copy.
- Current live endpoint (keep this the single source of truth):
  **`https://mcp-server-data-validation.onrender.com/mcp`**
