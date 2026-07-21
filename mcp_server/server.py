"""
MCP server exposing the Fortive Oracle HCM / ADP Celergo validation logic as
MCP tools, so Oracle AI Agent Studio can register them via the "MCP" tool
type on the New Tool screen.

Run (HTTP, remote-reachable -- what Studio needs):
    python3 mcp_server/server.py
    # serves streamable-http MCP at http://<host>:8000/mcp

Run (stdio, for local testing with an MCP Inspector or Claude Desktop):
    python3 mcp_server/server.py --stdio

Recommended primary use: register only `validate_against_adp_spec` (and
optionally `send_notification_email`) via MCP in Studio. `get_hcm_extract`
is included for end-to-end demo/testing but in production should be a
native Fusion "Business Object" tool instead -- Studio can read Oracle HCM
data directly without round-tripping through this server.
"""
import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rules import validate_record
from src.validator import load_extract
from src.email_notifier import render_digest_html, send_or_write

mcp = FastMCP("fortive-hcm-adp-validator")

DEFAULT_EXTRACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "sample_hcm_extract_canada.csv",
)


@mcp.tool()
def validate_against_adp_spec(records: list[dict]) -> list[dict]:
    """Validate Oracle HCM Canada employee records against the ADP GlobalView/
    Celergo interface specification and return any flagged exceptions.

    Args:
        records: List of employee records (field names must match the Oracle
            HCM Canada extract layout, e.g. employee_id, sin, province,
            pay_group, hire_date, bank_institution, etc.)

    Returns:
        A list of exception dicts: employee_id, rule_id, severity, field,
        message. Empty list means no exceptions were found.
    """
    exceptions = []
    for record in records:
        exceptions.extend(validate_record(record))
    return [
        {
            "employee_id": e.employee_id,
            "rule_id": e.rule_id,
            "severity": e.severity,
            "field": e.field,
            "message": e.message,
        }
        for e in exceptions
    ]


@mcp.tool()
def send_notification_email(recipient: str, exceptions: list[dict]) -> str:
    """Send (or, in dry-run mode, render) an HTML exception digest email to
    the HR/data owner responsible for the flagged records. Does not modify
    any HCM or ADP data -- notification only, human remediates.

    Args:
        recipient: Email address of the HR/data owner to notify.
        exceptions: List of exception dicts as returned by
            validate_against_adp_spec.

    Returns:
        "sent:<recipient>" if SMTP_HOST is configured and the email was
        sent, or "dry-run-written:<path>" if it was written to disk instead.
    """
    class _Exc:
        def __init__(self, d):
            self.__dict__.update(d)

    html = render_digest_html(recipient, [_Exc(e) for e in exceptions])
    return send_or_write(recipient, html)


@mcp.tool()
def get_hcm_extract(extract_date: str | None = None) -> list[dict]:
    """DEMO/FALLBACK ONLY: retrieve the mock Oracle HCM Canada data extract
    bundled with this POC. In production, replace this with a native Fusion
    "Business Object" tool that reads live Oracle HCM data directly --
    Studio does not need to round-trip through this server for that.

    Args:
        extract_date: Unused in the demo; present to match the intended
            production tool signature.

    Returns:
        A list of employee record dicts from the sample extract.
    """
    return load_extract(DEFAULT_EXTRACT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdio", action="store_true", help="Run over stdio instead of streamable-http")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.stdio:
        mcp.run(transport="stdio")
    else:
        mcp.settings.port = args.port
        mcp.settings.host = "0.0.0.0"
        mcp.run(transport="streamable-http")
