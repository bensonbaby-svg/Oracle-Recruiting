"""
Notification mechanism: routes flagged exceptions to the relevant HR/data
owner by email, keeping a human in the loop for remediation.

In the wireframe this renders one HTML digest per data owner and, by
default, writes it to output/ instead of sending (DRY RUN). Set
SMTP_HOST/SMTP_PORT/SMTP_FROM env vars to actually send via smtplib -- in the
real Oracle AI Agent Studio build this function is replaced by the agent's
"send notification" tool (e.g. an Oracle Integration Cloud email action or
Fusion BI Publisher email delivery, see docs/oracle_agent_studio_setup.md).
"""
import os
import smtplib
from collections import defaultdict
from email.mime.text import MIMEText

from .rules import ValidationException

# Placeholder routing table: province -> HR/data owner mailbox.
# Replace with Fortive's actual RACI / data-owner mapping before go-live.
DATA_OWNER_ROUTING = {
    "ON": "hr-data-owner-on@fortive.example",
    "QC": "hr-data-owner-qc@fortive.example",
    "BC": "hr-data-owner-bc@fortive.example",
    "AB": "hr-data-owner-ab@fortive.example",
    "DEFAULT": "hr-data-owner-ca@fortive.example",
}


def _owner_for(province: str) -> str:
    return DATA_OWNER_ROUTING.get(province, DATA_OWNER_ROUTING["DEFAULT"])


def group_exceptions_by_owner(exceptions: list[ValidationException], records_by_id: dict) -> dict:
    grouped = defaultdict(list)
    for exc in exceptions:
        record = records_by_id.get(exc.employee_id, {})
        owner = _owner_for(record.get("province", ""))
        grouped[owner].append(exc)
    return grouped


def render_digest_html(owner: str, exceptions: list[ValidationException]) -> str:
    rows = "\n".join(
        f"<tr><td>{e.employee_id}</td><td>{e.rule_id}</td><td>{e.severity}</td>"
        f"<td>{e.field}</td><td>{e.message}</td></tr>"
        for e in exceptions
    )
    return f"""\
<html><body>
<h2>Fortive - Oracle HCM to ADP Celergo Data Validation Exceptions</h2>
<p>Recipient: {owner}</p>
<p>{len(exceptions)} exception(s) require review before the next ADP transmission.</p>
<table border="1" cellpadding="4" cellspacing="0">
<tr><th>Employee ID</th><th>Rule</th><th>Severity</th><th>Field</th><th>Message</th></tr>
{rows}
</table>
<p>This is an automated detect-and-flag notification. No data has been changed
or transmitted to ADP; please review and remediate in Oracle HCM.</p>
</body></html>
"""


def send_or_write(owner: str, html: str, output_dir: str = "output") -> str:
    smtp_host = os.environ.get("SMTP_HOST")
    if smtp_host:
        msg = MIMEText(html, "html")
        msg["Subject"] = "Fortive: Oracle HCM / ADP Celergo Validation Exceptions"
        msg["From"] = os.environ.get("SMTP_FROM", "hcm-adp-validation-agent@fortive.example")
        msg["To"] = owner
        with smtplib.SMTP(smtp_host, int(os.environ.get("SMTP_PORT", "25"))) as server:
            server.send_message(msg)
        return f"sent:{owner}"

    os.makedirs(output_dir, exist_ok=True)
    safe_name = owner.replace("@", "_at_").replace(".", "_")
    path = os.path.join(output_dir, f"{safe_name}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"dry-run-written:{path}"


def notify(exceptions: list[ValidationException], records: list[dict], output_dir: str = "output") -> list[str]:
    records_by_id = {r["employee_id"]: r for r in records}
    grouped = group_exceptions_by_owner(exceptions, records_by_id)
    results = []
    for owner, owner_exceptions in grouped.items():
        html = render_digest_html(owner, owner_exceptions)
        results.append(send_or_write(owner, html, output_dir))
    return results
