"""
Oracle Recruiting MCP Server

Exposes Oracle HCM Cloud Recruiting data as MCP tools so any
MCP-compatible client (Claude, etc.) can query and analyse it.

Run:
    python -m mcp_server.server                  # stdio (default)
    ORACLE_USE_MOCK=true python -m mcp_server.server  # use mock data

MCP Tool catalogue
──────────────────
  list_job_requisitions       – Fetch open/closed job requisitions
  list_job_applications       – Fetch applications with optional filters
  list_candidates             – Fetch candidate profiles
  list_offers                 – Fetch offer records
  list_interviews             – Fetch interview schedules
  get_hiring_funnel           – Application funnel metrics
  get_time_to_fill_analysis   – Time-to-fill metrics and at-risk requisitions
  get_offer_analysis          – Offer acceptance rates and salary insights
  get_source_effectiveness    – Which sources generate the best hires
  get_interview_analysis      – Interview scoring and type breakdown
  get_department_summary      – Per-department recruiting activity
  generate_full_report        – Comprehensive recruiting insights report
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ── MCP import ────────────────────────────────────────────────────────────────
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from mcp.server import FastMCP  # type: ignore[no-redef]

# ── Local imports ─────────────────────────────────────────────────────────────
from mcp_server.oracle_client import get_client
from mcp_server import insights as ins

# ── Oracle client ─────────────────────────────────────────────────────────────
USE_MOCK = os.getenv("ORACLE_USE_MOCK", "false").lower() == "true"
oracle = get_client(mock=USE_MOCK)

# ── MCP server ────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name=os.getenv("MCP_SERVER_NAME", "oracle-recruiting"),
    instructions=(
        "You are an Oracle Recruiting analytics assistant. "
        "Use the available tools to fetch recruiting data from Oracle HCM Cloud "
        "and generate insights about the hiring pipeline, candidates, offers, and sources."
    ),
)


# ═════════════════════════════════════════════════════════════════════════════
# Data-fetch tools
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def list_job_requisitions(
    status: str = "",
    department: str = "",
    location: str = "",
    date_from: str = "",
    limit: int = 50,
) -> str:
    """
    Fetch job requisitions from Oracle Recruiting Cloud.

    Args:
        status:     Filter by status. Common values: Open, Filled, Canceled.
        department: Filter by department name (exact match).
        location:   Filter by location name (exact match).
        date_from:  Only return requisitions created on or after this date (YYYY-MM-DD).
        limit:      Max number of records to return (default 50, 0 = all).

    Returns:
        JSON array of requisition objects.
    """
    try:
        data = oracle.get_job_requisitions(
            status=status or None,
            department=department or None,
            location=location or None,
            date_from=date_from or None,
            limit=limit,
        )
        logger.info("list_job_requisitions returned %d records", len(data))
        return json.dumps(data, indent=2)
    except Exception as exc:
        logger.error("list_job_requisitions error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def list_job_applications(
    requisition_id: str = "",
    phase: str = "",
    state: str = "",
    date_from: str = "",
    limit: int = 100,
) -> str:
    """
    Fetch job applications from Oracle Recruiting Cloud.

    Args:
        requisition_id: Filter by a specific requisition ID.
        phase:          Filter by phase. Values: Screening, Interview, Offer, Hired.
        state:          Filter by state. Values: Active, Rejected, Withdrawn, Hired, Declined.
        date_from:      Only return applications submitted on or after this date (YYYY-MM-DD).
        limit:          Max number of records (default 100, 0 = all).

    Returns:
        JSON array of application objects.
    """
    try:
        data = oracle.get_job_applications(
            requisition_id=requisition_id or None,
            phase=phase or None,
            state=state or None,
            date_from=date_from or None,
            limit=limit,
        )
        logger.info("list_job_applications returned %d records", len(data))
        return json.dumps(data, indent=2)
    except Exception as exc:
        logger.error("list_job_applications error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def list_candidates(
    candidate_id: str = "",
    name: str = "",
    limit: int = 50,
) -> str:
    """
    Fetch candidate profiles from Oracle Recruiting Cloud.

    Args:
        candidate_id: Fetch a single candidate by their Oracle candidate ID.
        name:         Search by candidate name (partial match).
        limit:        Max number of records (default 50, 0 = all).

    Returns:
        JSON array of candidate objects.
    """
    try:
        data = oracle.get_candidates(
            candidate_id=candidate_id or None,
            name=name or None,
            limit=limit,
        )
        logger.info("list_candidates returned %d records", len(data))
        return json.dumps(data, indent=2)
    except Exception as exc:
        logger.error("list_candidates error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def list_offers(
    requisition_id: str = "",
    status: str = "",
    date_from: str = "",
    limit: int = 100,
) -> str:
    """
    Fetch offer records from Oracle Recruiting Cloud.

    Args:
        requisition_id: Filter by requisition.
        status:         Filter by offer status: Accepted, Declined, Pending.
        date_from:      Only return offers created on or after this date (YYYY-MM-DD).
        limit:          Max number of records (default 100, 0 = all).

    Returns:
        JSON array of offer objects including salary, acceptance status, and decline reasons.
    """
    try:
        data = oracle.get_offers(
            requisition_id=requisition_id or None,
            status=status or None,
            date_from=date_from or None,
            limit=limit,
        )
        logger.info("list_offers returned %d records", len(data))
        return json.dumps(data, indent=2)
    except Exception as exc:
        logger.error("list_offers error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def list_interviews(
    requisition_id: str = "",
    date_from: str = "",
    limit: int = 100,
) -> str:
    """
    Fetch interview schedules from Oracle Recruiting Cloud.

    Args:
        requisition_id: Filter by requisition ID.
        date_from:      Only return interviews scheduled on or after this date (YYYY-MM-DD).
        limit:          Max number of records (default 100, 0 = all).

    Returns:
        JSON array of interview objects including type, status, score, and feedback.
    """
    try:
        data = oracle.get_interview_schedules(
            requisition_id=requisition_id or None,
            date_from=date_from or None,
            limit=limit,
        )
        logger.info("list_interviews returned %d records", len(data))
        return json.dumps(data, indent=2)
    except Exception as exc:
        logger.error("list_interviews error: %s", exc)
        return json.dumps({"error": str(exc)})


# ═════════════════════════════════════════════════════════════════════════════
# Insights / analytics tools
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_hiring_funnel(
    requisition_id: str = "",
    department: str = "",
) -> str:
    """
    Analyse the hiring pipeline / funnel across all or filtered applications.

    Shows application volume at each stage (Screening → Interview → Offer → Hired),
    stage-to-stage conversion rates, rejection rates, and withdrawal rates.

    Args:
        requisition_id: Scope the funnel to a single requisition (optional).
        department:     Scope the funnel to a single department (optional).

    Returns:
        JSON object with funnel metrics.
    """
    try:
        apps = oracle.get_job_applications(
            requisition_id=requisition_id or None,
            limit=0,
        )
        if department:
            reqs = oracle.get_job_requisitions(department=department, limit=0)
            req_ids = {r["RequisitionId"] for r in reqs}
            apps = [a for a in apps if a.get("RequisitionId") in req_ids]

        result = ins.analyze_hiring_funnel(apps)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_hiring_funnel error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_time_to_fill_analysis(department: str = "") -> str:
    """
    Calculate time-to-fill metrics across requisitions.

    Includes average, min, and max days to fill, per-department breakdown,
    and a list of requisitions that have been open for more than 60 days (at-risk).

    Args:
        department: Scope analysis to a single department (optional).

    Returns:
        JSON object with time-to-fill metrics and at-risk requisitions.
    """
    try:
        reqs = oracle.get_job_requisitions(
            department=department or None,
            limit=0,
        )
        result = ins.analyze_time_to_fill(reqs)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_time_to_fill_analysis error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_offer_analysis(requisition_id: str = "") -> str:
    """
    Analyse offer outcomes: acceptance rates, decline reasons, and salary data.

    Args:
        requisition_id: Scope analysis to a single requisition (optional).

    Returns:
        JSON object with offer acceptance metrics, decline reason breakdown,
        average salary, and average days-to-decision.
    """
    try:
        offers = oracle.get_offers(
            requisition_id=requisition_id or None,
            limit=0,
        )
        result = ins.analyze_offers(offers)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_offer_analysis error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_source_effectiveness() -> str:
    """
    Rank recruiting sources by hire rate, application volume, and cost-per-hire.

    Compares sources such as LinkedIn, Indeed, Employee Referral, University, etc.

    Returns:
        JSON object with per-source metrics and highlights for the top source
        by volume and by hire rate. Also includes the referral-specific hire rate.
    """
    try:
        apps    = oracle.get_job_applications(limit=0)
        sources = oracle.get_source_tracking(limit=0)
        result  = ins.analyze_source_effectiveness(apps, sources)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_source_effectiveness error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_interview_analysis(requisition_id: str = "") -> str:
    """
    Summarise interview activity, types, and candidate scoring.

    Args:
        requisition_id: Scope analysis to a single requisition (optional).

    Returns:
        JSON object with interview counts by type and status, average scores,
        score distribution, and the most active interviewers.
    """
    try:
        interviews = oracle.get_interview_schedules(
            requisition_id=requisition_id or None,
            limit=0,
        )
        result = ins.analyze_interviews(interviews)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_interview_analysis error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_department_summary() -> str:
    """
    Show recruiting activity broken down by department.

    Includes open and filled role counts, total openings vs. hires, total
    applications received, and average applications per role per department.

    Returns:
        JSON object keyed by department name.
    """
    try:
        reqs = oracle.get_job_requisitions(limit=0)
        apps = oracle.get_job_applications(limit=0)
        result = ins.analyze_by_department(reqs, apps)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("get_department_summary error: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
def generate_full_report() -> str:
    """
    Generate a comprehensive Oracle Recruiting insights report.

    Pulls all data from Oracle HCM (requisitions, applications, offers,
    interviews, sources) and produces a unified report covering:
      - Executive highlights
      - Hiring funnel metrics
      - Time-to-fill analysis with at-risk roles
      - Offer acceptance rates and salary insights
      - Source effectiveness ranking
      - Interview scoring summary
      - Department-level breakdown

    Returns:
        JSON object with all metrics sections and executive summary bullets.
    """
    try:
        reqs       = oracle.get_job_requisitions(limit=0)
        apps       = oracle.get_job_applications(limit=0)
        offers     = oracle.get_offers(limit=0)
        interviews = oracle.get_interview_schedules(limit=0)
        sources    = oracle.get_source_tracking(limit=0)

        result = ins.generate_full_report(reqs, apps, offers, interviews, sources)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("generate_full_report error: %s", exc)
        return json.dumps({"error": str(exc)})


# ═════════════════════════════════════════════════════════════════════════════
# Entrypoint
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mode = os.getenv("MCP_TRANSPORT", "stdio")
    logger.info("Starting Oracle Recruiting MCP server (transport=%s, mock=%s)", mode, USE_MOCK)
    if mode == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
