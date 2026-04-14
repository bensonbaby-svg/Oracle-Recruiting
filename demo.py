"""
Oracle Recruiting Insights - Demo Script

Runs all insight functions against mock data and prints a formatted report.
No live Oracle HCM Cloud connection is required.

Usage:
    python demo.py
"""

import json
import os

os.environ["ORACLE_USE_MOCK"] = "true"

from mcp_server.oracle_client import get_client
from mcp_server import insights as ins

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH = True
    console = Console()
except ImportError:
    RICH = False


def header(title: str) -> None:
    if RICH:
        console.rule(f"[bold cyan]{title}[/]")
    else:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")


def print_json(data: dict) -> None:
    if RICH:
        console.print_json(json.dumps(data))
    else:
        print(json.dumps(data, indent=2))


def main():
    client = get_client(mock=True)

    # ── Fetch all data ────────────────────────────────────────────────────────
    reqs       = client.get_job_requisitions()
    apps       = client.get_job_applications()
    offers     = client.get_offers()
    interviews = client.get_interview_schedules()
    sources    = client.get_source_tracking()

    # ── 1. Job Requisitions ───────────────────────────────────────────────────
    header("Job Requisitions")
    if RICH:
        t = Table(show_header=True, header_style="bold magenta")
        for col in ["ID", "Title", "Department", "Status", "Openings", "Hires", "Location"]:
            t.add_column(col)
        for r in reqs:
            status_color = {"Open": "green", "Filled": "blue", "Canceled": "red"}.get(r["RequisitionStatus"], "white")
            t.add_row(
                r["RequisitionId"], r["Title"], r["Department"],
                f"[{status_color}]{r['RequisitionStatus']}[/]",
                str(r["NumberOfOpenings"]), str(r["NumberOfHires"]), r["Location"],
            )
        console.print(t)
    else:
        for r in reqs:
            print(f"  {r['RequisitionId']:10} | {r['Title']:35} | {r['RequisitionStatus']:10} | {r['Department']}")

    # ── 2. Hiring Funnel ──────────────────────────────────────────────────────
    header("Hiring Funnel Analysis")
    funnel = ins.analyze_hiring_funnel(apps)
    if RICH:
        t = Table(show_header=True, header_style="bold magenta")
        t.add_column("Phase")
        t.add_column("Count", justify="right")
        t.add_column("Conversion %", justify="right")
        for phase, data in funnel["funnel_conversion"].items():
            t.add_row(phase, str(data["count"]), f"{data['conversion_rate_pct']}%")
        console.print(t)
        console.print(f"  Total Applications : {funnel['total_applications']}")
        console.print(f"  Active Pipeline    : {funnel['active_pipeline']}")
        console.print(f"  Rejection Rate     : {funnel['rejection_rate_pct']}%")
        console.print(f"  Withdrawal Rate    : {funnel['withdrawal_rate_pct']}%")
    else:
        print_json(funnel)

    # ── 3. Time-to-Fill ───────────────────────────────────────────────────────
    header("Time-to-Fill Analysis")
    ttf = ins.analyze_time_to_fill(reqs)
    if RICH:
        console.print(f"  Filled Requisitions   : {ttf['filled_requisitions']}")
        console.print(f"  Open Requisitions     : {ttf['open_requisitions']}")
        console.print(f"  Avg Days to Fill      : {ttf['average_days_to_fill']}")
        console.print(f"  Min / Max Days        : {ttf['min_days_to_fill']} / {ttf['max_days_to_fill']}")
        if ttf["by_department"]:
            t = Table(title="By Department", show_header=True, header_style="bold magenta")
            t.add_column("Department")
            t.add_column("Avg Days", justify="right")
            for dept, avg in ttf["by_department"].items():
                t.add_row(dept, str(avg))
            console.print(t)
        if ttf["at_risk_requisitions"]:
            console.print(Panel(
                "\n".join(
                    f"[red]{r['requisition_id']}[/] — {r['title']} ({r['department']}) — [bold]{r['days_open']} days open[/]"
                    for r in ttf["at_risk_requisitions"]
                ),
                title="[red]At-Risk Requisitions (>60 days)[/]",
            ))
    else:
        print_json(ttf)

    # ── 4. Offer Analysis ─────────────────────────────────────────────────────
    header("Offer Analysis")
    offer_stats = ins.analyze_offers(offers)
    if RICH:
        console.print(f"  Total Offers          : {offer_stats['total_offers']}")
        console.print(f"  Accepted              : {offer_stats['accepted']}")
        console.print(f"  Declined              : {offer_stats['declined']}")
        console.print(f"  Pending               : {offer_stats['pending']}")
        console.print(f"  Acceptance Rate       : [bold green]{offer_stats['acceptance_rate_pct']}%[/]")
        console.print(f"  Avg Offered Salary    : ${offer_stats['avg_offered_salary_usd']:,.0f}")
        console.print(f"  Salary Range          : ${offer_stats['salary_range']['min']:,} – ${offer_stats['salary_range']['max']:,}")
        console.print(f"  Avg Days to Decision  : {offer_stats['avg_days_to_decision']}")
        if offer_stats["decline_reasons"]:
            console.print("  Decline Reasons:", offer_stats["decline_reasons"])
    else:
        print_json(offer_stats)

    # ── 5. Source Effectiveness ───────────────────────────────────────────────
    header("Source Effectiveness")
    src_stats = ins.analyze_source_effectiveness(apps, sources)
    if RICH:
        t = Table(show_header=True, header_style="bold magenta")
        for col in ["Source", "Applications", "Hires", "Hire Rate %", "Cost/Hire ($)"]:
            t.add_column(col, justify="right" if col not in ["Source"] else "left")
        for src, data in sorted(src_stats["by_source"].items(), key=lambda x: -x[1]["hire_rate_pct"]):
            cph = f"${data['cost_per_hire_usd']:,.0f}" if data.get("cost_per_hire_usd") else "N/A"
            t.add_row(src, str(data["applications"]), str(data["hires"]), f"{data['hire_rate_pct']}%", cph)
        console.print(t)
        console.print(f"  Top Source (Volume)   : {src_stats['top_source_by_volume']}")
        console.print(f"  Top Source (Hire Rate): {src_stats['top_source_by_hire_rate']}")
        console.print(f"  Referral Hire Rate    : {src_stats['referral_hire_rate_pct']}%")
    else:
        print_json(src_stats)

    # ── 6. Interview Analysis ─────────────────────────────────────────────────
    header("Interview Analysis")
    intv_stats = ins.analyze_interviews(interviews)
    if RICH:
        console.print(f"  Total Interviews      : {intv_stats['total_interviews']}")
        console.print(f"  Avg Candidate Score   : {intv_stats['avg_candidate_score']}")
        console.print(f"  Score Distribution    : {intv_stats['score_distribution']}")
        console.print(f"  By Type               : {intv_stats['by_type']}")
    else:
        print_json(intv_stats)

    # ── 7. Department Summary ─────────────────────────────────────────────────
    header("Department Summary")
    dept_stats = ins.analyze_by_department(reqs, apps)
    if RICH:
        t = Table(show_header=True, header_style="bold magenta")
        for col in ["Department", "Open Roles", "Filled", "Openings", "Hires", "Applications", "Apps/Role"]:
            t.add_column(col, justify="right" if col != "Department" else "left")
        for dept, d in dept_stats.items():
            t.add_row(
                dept,
                str(d["open_roles"]), str(d["filled_roles"]),
                str(d["total_openings"]), str(d["total_hires"]),
                str(d["total_applications"]), str(d["avg_apps_per_role"]),
            )
        console.print(t)
    else:
        print_json(dept_stats)

    # ── 8. Full Report Executive Summary ──────────────────────────────────────
    header("Executive Summary (Full Report)")
    report = ins.generate_full_report(reqs, apps, offers, interviews, sources)
    if RICH:
        for bullet in report["executive_summary"]:
            console.print(f"  • {bullet}")
    else:
        for bullet in report["executive_summary"]:
            print(f"  * {bullet}")

    if RICH:
        console.rule("[bold green]Demo complete[/]")
    else:
        print("\n" + "="*60 + "\nDemo complete.\n")


if __name__ == "__main__":
    main()
