# Fortive — Oracle HCM to ADP Celergo Data Validation Agent (Canada MVP)

A runnable wireframe/POC for the proposed Oracle AI Agent Studio agent that
validates Oracle HCM data against ADP GlobalView/Celergo specifications
before transmission, and emails exceptions to the responsible HR/data owner
(detect-and-flag, human-in-the-loop, Canada-scoped).

This repo is a **local simulation** of the agent's logic — it does not
connect to a real Oracle Fusion tenant or ADP. It's meant to let you (a) see
the detect-and-flag behavior working end to end today, and (b) hand the
tools/rules/instructions straight to Oracle AI Agent Studio once you have
tenant access. See `docs/oracle_agent_studio_setup.md` for exactly what to
paste in and what's still needed to go live.

## Setup and running it

**Full step-by-step instructions (no Python experience assumed, safe to
hand to a colleague) are in `docs/SETUP_GUIDE.md`.** It covers installing
Python/git, creating the virtual environment, installing dependencies,
running the tests and demo, running the MCP server, and exposing it
publicly so Oracle AI Agent Studio can call it.

Quick reference if you already have Python 3.9+ set up:
```
python3 main.py                              # run the detect-and-flag demo
python3 -m unittest discover -s tests -v      # run the test suite
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python3 mcp_server/server.py                  # run the MCP server (see docs/SETUP_GUIDE.md to expose it)
```

## Layout

| Path | Purpose |
|------|---------|
| `src/rules.py` | ADP Canada validation rule catalog (placeholder — see caveats below) |
| `src/validator.py` | Loads the HCM extract and applies the rule catalog |
| `src/email_notifier.py` | Groups exceptions by data owner and renders/sends the notification email |
| `main.py` | Orchestrates retrieve -> validate -> notify, the same flow the real agent runs |
| `mcp_server/server.py` | MCP server exposing `validate_against_adp_spec`, `send_notification_email`, and a demo `get_hcm_extract` as MCP tools |
| `data/sample_hcm_extract_canada.csv` | Mock Oracle HCM Canada extract with injected errors |
| `tests/test_validator.py` | Rule-by-rule and end-to-end regression tests |
| `docs/SETUP_GUIDE.md` | Full step-by-step: install Python/git, set up the virtual environment, run everything, expose the MCP server publicly |
| `docs/architecture.md` | Target Oracle AI Agent Studio architecture and how this wireframe maps to it |
| `docs/adp_validation_rules_canada.md` | The rule catalog spelled out, with what Fortive needs to supply to replace placeholders |
| `docs/oracle_agent_studio_setup.md` | Agent instructions, tool registration steps (including MCP), and the complete checklist to bring the POC to life |

## Important caveat

The validation rules here are illustrative, built from generally known
Canadian payroll/ADP interface requirements (SIN format/checksum, province
codes, banking format, TD1 codes, pay group/frequency, effective dating).
They are **not** sourced from Fortive's actual ADP Celergo interface control
document. Before this becomes anything more than a demo, swap the rule
catalog and data-owner routing table for Fortive's real specifications (see
`docs/adp_validation_rules_canada.md` for the exact list of what's needed).
