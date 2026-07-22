# Fortive — Oracle HCM to ADP Data Validation Agent
## Executive Summary

**The problem:** Fortive sends payroll data from Oracle HCM to its payroll
processor, ADP GlobalView/Celergo. If that data has errors — a malformed
SIN, wrong province code, bad banking details — those errors can flow
through to ADP and affect an employee's pay. Today there's no automated
check before that data is sent.

**The proposal:** An AI agent, built on Oracle's AI Agent Studio, that
automatically reviews Oracle HCM payroll data against ADP's requirements
before it's transmitted, flags anything that looks wrong, and emails the
responsible HR/payroll contact to review and fix it. The agent only flags
issues — it never changes data itself and never blocks or delays the
existing payroll process. A person always makes the final call. Scope for
this first phase is limited to Canada, to prove the concept on a smaller,
lower-risk population before considering a wider rollout.

**Status: proof-of-concept built and working.** We've built and tested the
full detection logic against realistic sample payroll data and confirmed
it correctly catches the kinds of errors it's meant to catch. The
technical piece that lets Oracle's agent platform actually call this logic
has also been built and deployed, and is confirmed live and working. What
remains is finishing the configuration inside Oracle's agent platform
itself (a hands-on setup task, not new development) and testing it
end-to-end.

**What we still need from Fortive to move past the prototype stage:**
1. The official ADP Celergo Canada interface specification (what we're
   validating against today is a reasonable placeholder built from general
   knowledge, not Fortive's actual requirements).
2. Fortive's real payroll group codes and the confirmed list of who should
   be notified for which data issue.
3. A handful of real, de-identified Canada employee records to validate
   the logic against before it's shown to end users.

**Risk profile:** Low. The agent is read-only against source data (it
never writes to Oracle HCM or to ADP), scoped to one country, and requires
human review before anything changes — it's an early-warning system
layered alongside the existing process, not a replacement for it.

**Timeline driver:** the Oracle Agent Studio configuration work can proceed
in parallel with requesting the ADP spec and sample data from Fortive —
neither is blocking the other right now.

*(Technical detail, source code, and the exact configuration steps are
documented separately in `docs/HANDOFF.md` for the engineering team.)*
