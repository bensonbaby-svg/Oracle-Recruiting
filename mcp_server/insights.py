"""
Oracle Recruiting Insights Engine

Processes raw Oracle HCM data and produces actionable recruiting metrics
and insights including:
  - Hiring funnel / pipeline analysis
  - Time-to-fill and time-to-hire
  - Offer acceptance rates
  - Source effectiveness
  - Departmental and role-level comparisons
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, date
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Date helpers
# ──────────────────────────────────────────────────────────────────────────────

def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(str(value)[:19], fmt).date()
        except ValueError:
            continue
    return None


def _days_between(start: Any, end: Any) -> int | None:
    s, e = _parse_date(start), _parse_date(end)
    if s and e:
        return (e - s).days
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Hiring funnel
# ──────────────────────────────────────────────────────────────────────────────

PHASE_ORDER = ["Screening", "Interview", "Offer", "Hired"]


def analyze_hiring_funnel(applications: list[dict]) -> dict:
    """
    Break down applications by phase and state to produce funnel metrics.

    Returns:
        {
            "total_applications": int,
            "by_phase": {phase: count},
            "by_state": {state: count},
            "funnel_conversion": {phase: {"count": int, "conversion_rate": float}},
            "active_pipeline": int,
            "rejection_rate": float,
            "withdrawal_rate": float,
        }
    """
    total = len(applications)
    by_phase: dict[str, int] = defaultdict(int)
    by_state: dict[str, int] = defaultdict(int)

    for app in applications:
        by_phase[app.get("Phase", "Unknown")] += 1
        by_state[app.get("State", "Unknown")] += 1

    # Compute funnel conversion rates relative to previous stage
    funnel: dict[str, dict] = {}
    prev_count = total
    for phase in PHASE_ORDER:
        count = by_phase.get(phase, 0)
        rate = round((count / prev_count * 100), 1) if prev_count else 0.0
        funnel[phase] = {"count": count, "conversion_rate_pct": rate}
        prev_count = count if count else prev_count

    active = by_state.get("Active", 0)
    rejected = by_state.get("Rejected", 0)
    withdrawn = by_state.get("Withdrawn", 0)

    return {
        "total_applications": total,
        "by_phase": dict(by_phase),
        "by_state": dict(by_state),
        "funnel_conversion": funnel,
        "active_pipeline": active,
        "rejection_rate_pct": round(rejected / total * 100, 1) if total else 0.0,
        "withdrawal_rate_pct": round(withdrawn / total * 100, 1) if total else 0.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Time-to-fill / time-to-hire
# ──────────────────────────────────────────────────────────────────────────────

def analyze_time_to_fill(requisitions: list[dict]) -> dict:
    """
    Calculate time-to-fill for filled requisitions.

    Returns:
        {
            "filled_requisitions": int,
            "open_requisitions": int,
            "average_days_to_fill": float,
            "min_days_to_fill": int,
            "max_days_to_fill": int,
            "by_department": {dept: avg_days},
            "at_risk": [requisitions open > 60 days],
        }
    """
    filled = [r for r in requisitions if r.get("FilledDate") and r.get("CreationDate")]
    open_reqs = [r for r in requisitions if r.get("RequisitionStatus") == "Open"]

    days_list = []
    by_dept: dict[str, list[int]] = defaultdict(list)
    for r in filled:
        days = _days_between(r["CreationDate"], r["FilledDate"])
        if days is not None:
            days_list.append(days)
            dept = r.get("Department", "Unknown")
            by_dept[dept].append(days)

    today = date.today()
    at_risk = []
    for r in open_reqs:
        open_days = _days_between(r.get("CreationDate"), today)
        if open_days and open_days > 60:
            at_risk.append({
                "requisition_id": r.get("RequisitionId"),
                "title": r.get("Title"),
                "department": r.get("Department"),
                "days_open": open_days,
                "recruiter": r.get("Recruiter"),
            })

    dept_avg = {
        dept: round(sum(v) / len(v), 1)
        for dept, v in by_dept.items()
    }

    return {
        "filled_requisitions": len(filled),
        "open_requisitions": len(open_reqs),
        "average_days_to_fill": round(sum(days_list) / len(days_list), 1) if days_list else 0.0,
        "min_days_to_fill": min(days_list) if days_list else 0,
        "max_days_to_fill": max(days_list) if days_list else 0,
        "by_department": dept_avg,
        "at_risk_requisitions": sorted(at_risk, key=lambda x: x["days_open"], reverse=True),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Offer analytics
# ──────────────────────────────────────────────────────────────────────────────

def analyze_offers(offers: list[dict]) -> dict:
    """
    Analyze offer outcomes: acceptance rate, decline reasons, salary data.

    Returns:
        {
            "total_offers": int,
            "accepted": int, "declined": int, "pending": int,
            "acceptance_rate_pct": float,
            "decline_reasons": {reason: count},
            "avg_offered_salary": float,
            "salary_range": {"min": float, "max": float},
            "avg_days_to_decision": float,
        }
    """
    total = len(offers)
    accepted = [o for o in offers if o.get("OfferStatus") == "Accepted"]
    declined = [o for o in offers if o.get("OfferStatus") == "Declined"]
    pending  = [o for o in offers if o.get("OfferStatus") == "Pending"]

    decline_reasons: dict[str, int] = defaultdict(int)
    for o in declined:
        reason = o.get("DeclineReason") or "Not specified"
        decline_reasons[reason] += 1

    salaries = [o["OfferedSalary"] for o in offers if o.get("OfferedSalary")]

    # Days from offer to decision
    decision_days = []
    for o in accepted:
        d = _days_between(o.get("OfferDate"), o.get("AcceptedDate"))
        if d is not None:
            decision_days.append(d)
    for o in declined:
        d = _days_between(o.get("OfferDate"), o.get("DeclinedDate"))
        if d is not None:
            decision_days.append(d)

    return {
        "total_offers": total,
        "accepted": len(accepted),
        "declined": len(declined),
        "pending": len(pending),
        "acceptance_rate_pct": round(len(accepted) / total * 100, 1) if total else 0.0,
        "decline_reasons": dict(decline_reasons),
        "avg_offered_salary_usd": round(sum(salaries) / len(salaries), 0) if salaries else 0.0,
        "salary_range": {
            "min": min(salaries) if salaries else 0,
            "max": max(salaries) if salaries else 0,
        },
        "avg_days_to_decision": round(sum(decision_days) / len(decision_days), 1) if decision_days else 0.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Source effectiveness
# ──────────────────────────────────────────────────────────────────────────────

def analyze_source_effectiveness(
    applications: list[dict],
    sources: list[dict] | None = None,
) -> dict:
    """
    Rank recruiting sources by application volume, hire rate, and cost-per-hire.

    Returns:
        {
            "by_source": {source: {applications, hires, hire_rate_pct, cost_per_hire}},
            "top_source_by_volume": str,
            "top_source_by_hire_rate": str,
            "referral_hire_rate_pct": float,
        }
    """
    by_source: dict[str, dict] = defaultdict(lambda: {"applications": 0, "hires": 0})

    for app in applications:
        src = app.get("Source") or "Unknown"
        by_source[src]["applications"] += 1
        if app.get("State") == "Hired":
            by_source[src]["hires"] += 1

    # Merge cost-per-hire from source tracking if available
    cost_map: dict[str, float] = {}
    if sources:
        for s in sources:
            cost_map[s.get("SourceName", "")] = float(s.get("CostPerHire") or 0)

    result_sources = {}
    for src, data in by_source.items():
        apps = data["applications"]
        hires = data["hires"]
        result_sources[src] = {
            "applications": apps,
            "hires": hires,
            "hire_rate_pct": round(hires / apps * 100, 1) if apps else 0.0,
            "cost_per_hire_usd": cost_map.get(src, None),
        }

    top_volume = max(result_sources, key=lambda k: result_sources[k]["applications"]) if result_sources else ""
    top_rate = max(result_sources, key=lambda k: result_sources[k]["hire_rate_pct"]) if result_sources else ""

    referral_apps = [a for a in applications if a.get("Referral") is True]
    referral_hires = [a for a in referral_apps if a.get("State") == "Hired"]
    referral_rate = round(len(referral_hires) / len(referral_apps) * 100, 1) if referral_apps else 0.0

    return {
        "by_source": result_sources,
        "top_source_by_volume": top_volume,
        "top_source_by_hire_rate": top_rate,
        "referral_hire_rate_pct": referral_rate,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Interview analytics
# ──────────────────────────────────────────────────────────────────────────────

def analyze_interviews(interviews: list[dict]) -> dict:
    """
    Summarize interview activity and scoring.

    Returns:
        {
            "total_interviews": int,
            "by_type": {type: count},
            "by_status": {status: count},
            "avg_score": float,
            "score_distribution": {"90-100": n, "80-89": n, "70-79": n, "<70": n},
            "top_interviewers": [{name, count, avg_score}],
        }
    """
    total = len(interviews)
    by_type: dict[str, int] = defaultdict(int)
    by_status: dict[str, int] = defaultdict(int)
    scores = []
    interviewer_data: dict[str, dict] = defaultdict(lambda: {"count": 0, "scores": []})

    for iv in interviews:
        by_type[iv.get("InterviewType", "Unknown")] += 1
        by_status[iv.get("InterviewStatus", "Unknown")] += 1
        score = iv.get("Score")
        name = iv.get("InterviewerName", "Unknown")
        interviewer_data[name]["count"] += 1
        if score is not None:
            scores.append(score)
            interviewer_data[name]["scores"].append(score)

    dist = {"90-100": 0, "80-89": 0, "70-79": 0, "<70": 0}
    for s in scores:
        if s >= 90:
            dist["90-100"] += 1
        elif s >= 80:
            dist["80-89"] += 1
        elif s >= 70:
            dist["70-79"] += 1
        else:
            dist["<70"] += 1

    top_interviewers = []
    for name, data in interviewer_data.items():
        avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else None
        top_interviewers.append({"name": name, "interviews_conducted": data["count"], "avg_candidate_score": avg})
    top_interviewers.sort(key=lambda x: x["interviews_conducted"], reverse=True)

    return {
        "total_interviews": total,
        "by_type": dict(by_type),
        "by_status": dict(by_status),
        "avg_candidate_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "score_distribution": dist,
        "top_interviewers": top_interviewers[:5],
    }


# ──────────────────────────────────────────────────────────────────────────────
# Department summary
# ──────────────────────────────────────────────────────────────────────────────

def analyze_by_department(requisitions: list[dict], applications: list[dict]) -> dict:
    """
    Summarize recruiting activity by department.

    Returns:
        {dept: {open_roles, total_hires, total_applications, avg_apps_per_role}}
    """
    dept_data: dict[str, dict] = defaultdict(lambda: {
        "open_roles": 0, "filled_roles": 0, "canceled_roles": 0,
        "total_openings": 0, "total_hires": 0,
    })

    req_map: dict[str, str] = {}  # RequisitionId -> Department
    for r in requisitions:
        dept = r.get("Department", "Unknown")
        req_map[r.get("RequisitionId", "")] = dept
        status = r.get("RequisitionStatus", "")
        dept_data[dept]["total_openings"] += int(r.get("NumberOfOpenings") or 0)
        dept_data[dept]["total_hires"] += int(r.get("NumberOfHires") or 0)
        if status == "Open":
            dept_data[dept]["open_roles"] += 1
        elif status == "Filled":
            dept_data[dept]["filled_roles"] += 1
        elif status == "Canceled":
            dept_data[dept]["canceled_roles"] += 1

    # Count applications per department
    app_counts: dict[str, int] = defaultdict(int)
    for app in applications:
        dept = req_map.get(app.get("RequisitionId", ""), "Unknown")
        app_counts[dept] += 1

    result = {}
    for dept, data in dept_data.items():
        total_roles = data["open_roles"] + data["filled_roles"]
        result[dept] = {
            **data,
            "total_applications": app_counts.get(dept, 0),
            "avg_apps_per_role": round(app_counts.get(dept, 0) / total_roles, 1) if total_roles else 0.0,
        }
    return dict(sorted(result.items()))


# ──────────────────────────────────────────────────────────────────────────────
# Comprehensive report
# ──────────────────────────────────────────────────────────────────────────────

def generate_full_report(
    requisitions: list[dict],
    applications: list[dict],
    offers: list[dict],
    interviews: list[dict],
    sources: list[dict] | None = None,
) -> dict:
    """
    Generate a comprehensive Oracle Recruiting insights report.

    Returns a structured dict with all metrics sections and key highlights.
    """
    funnel       = analyze_hiring_funnel(applications)
    ttf          = analyze_time_to_fill(requisitions)
    offer_stats  = analyze_offers(offers)
    src_stats    = analyze_source_effectiveness(applications, sources)
    intv_stats   = analyze_interviews(interviews)
    dept_stats   = analyze_by_department(requisitions, applications)

    # Key highlights / executive summary
    highlights = []

    if ttf["at_risk_requisitions"]:
        n = len(ttf["at_risk_requisitions"])
        highlights.append(
            f"{n} requisition(s) have been open for more than 60 days — "
            f"review with recruiters to unblock."
        )

    acc_rate = offer_stats["acceptance_rate_pct"]
    if acc_rate < 70:
        highlights.append(
            f"Offer acceptance rate is {acc_rate}% — below the 70% benchmark. "
            f"Review compensation and competing offers."
        )
    else:
        highlights.append(f"Offer acceptance rate is healthy at {acc_rate}%.")

    top_src = src_stats["top_source_by_hire_rate"]
    if top_src:
        rate = src_stats["by_source"][top_src]["hire_rate_pct"]
        highlights.append(
            f"'{top_src}' is the most effective hiring source with a {rate}% hire rate."
        )

    ref_rate = src_stats["referral_hire_rate_pct"]
    if ref_rate:
        highlights.append(
            f"Employee referrals convert to hires at {ref_rate}% — "
            f"consider investing in referral programs."
        )

    avg_ttf = ttf["average_days_to_fill"]
    if avg_ttf:
        highlights.append(f"Average time-to-fill is {avg_ttf} days.")

    withdraw_rate = funnel["withdrawal_rate_pct"]
    if withdraw_rate > 10:
        highlights.append(
            f"Candidate withdrawal rate is {withdraw_rate}% — "
            f"consider improving the candidate experience and communication."
        )

    return {
        "report_generated_at": datetime.utcnow().isoformat() + "Z",
        "executive_summary": highlights,
        "hiring_funnel": funnel,
        "time_to_fill": ttf,
        "offer_analytics": offer_stats,
        "source_effectiveness": src_stats,
        "interview_analytics": intv_stats,
        "by_department": dept_stats,
    }
