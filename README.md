# Oracle Recruiting MCP Server

Connect Claude (or any MCP-compatible client) to **Oracle HCM Cloud Recruiting** via REST APIs and generate actionable hiring insights.

## Architecture

```
Claude / MCP Client
       │
       │  MCP (stdio / SSE)
       ▼
oracle-recruiting MCP Server  (mcp_server/server.py)
       │
       │  HTTPS REST
       ▼
Oracle HCM Cloud REST API  (/hcmRestApi/resources/latest/recruiting*)
```

## Features

| Area | Details |
|---|---|
| **Data fetch** | Job requisitions, applications, candidates, offers, interviews, source tracking |
| **Hiring funnel** | Stage-by-stage conversion rates, rejection & withdrawal rates |
| **Time-to-fill** | Avg / min / max days, per-department breakdown, at-risk (>60 day) roles |
| **Offer analytics** | Acceptance rate, decline reasons, salary range, days-to-decision |
| **Source effectiveness** | Hire rate and cost-per-hire ranked by source (LinkedIn, referral, etc.) |
| **Interview analytics** | Score distribution, interview type breakdown, top interviewers |
| **Department summary** | Per-department open roles, hires, and application volume |
| **Full report** | One-call comprehensive report with executive highlights |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Oracle HCM Cloud credentials
```

Key variables:

```
ORACLE_HCM_HOST=yourcompany.fa.us2.oraclecloud.com
ORACLE_USERNAME=your.user@company.com
ORACLE_PASSWORD=your_password
```

### 3. Run the demo (no Oracle connection needed)

```bash
ORACLE_USE_MOCK=true python demo.py
```

### 4. Start the MCP server

```bash
# With live Oracle HCM Cloud
python -m mcp_server.server

# With mock data (development / testing)
ORACLE_USE_MOCK=true python -m mcp_server.server
```

## MCP Tools

| Tool | Description |
|---|---|
| `list_job_requisitions` | Fetch requisitions with filters (status, department, location, date) |
| `list_job_applications` | Fetch applications with filters (requisition, phase, state, date) |
| `list_candidates` | Fetch candidate profiles |
| `list_offers` | Fetch offer records (status, salary, acceptance) |
| `list_interviews` | Fetch interview schedules and scores |
| `get_hiring_funnel` | Pipeline conversion metrics |
| `get_time_to_fill_analysis` | Time-to-fill stats and at-risk roles |
| `get_offer_analysis` | Offer acceptance rates and salary data |
| `get_source_effectiveness` | Rank recruiting sources by hire rate |
| `get_interview_analysis` | Interview scoring and type breakdown |
| `get_department_summary` | Per-department recruiting activity |
| `generate_full_report` | All metrics + executive highlights in one call |

## Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "oracle-recruiting": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Oracle-Recruiting",
      "env": {
        "ORACLE_HCM_HOST": "yourcompany.fa.us2.oraclecloud.com",
        "ORACLE_USERNAME": "your.user@company.com",
        "ORACLE_PASSWORD": "your_password"
      }
    }
  }
}
```

Then ask Claude questions like:
- *"Show me the hiring funnel for the Engineering department"*
- *"Which requisitions have been open for more than 60 days?"*
- *"What is our offer acceptance rate and what are the top decline reasons?"*
- *"Generate a full recruiting insights report"*

## Authentication

**Basic Auth (default):** Set `ORACLE_USERNAME` and `ORACLE_PASSWORD`.

**OAuth 2.0:** Set `ORACLE_CLIENT_ID`, `ORACLE_CLIENT_SECRET`, and optionally `ORACLE_TOKEN_URL`. The server auto-detects OAuth when client credentials are present.

## Project Structure

```
Oracle-Recruiting/
├── mcp_server/
│   ├── server.py          # MCP server — all tool definitions
│   ├── oracle_client.py   # Oracle HCM REST API client (real + mock)
│   ├── insights.py        # Analytics / insights engine
│   └── _mock_data.py      # Synthetic data for dev/testing
├── demo.py                # Standalone demo (no Oracle required)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Oracle HCM REST API Endpoints Used

| Resource | Oracle endpoint |
|---|---|
| Job Requisitions | `/hcmRestApi/resources/latest/recruitingCEJobRequisitions` |
| Job Applications | `/hcmRestApi/resources/latest/recruitingCEJobApplications` |
| Candidates | `/hcmRestApi/resources/latest/recruitingCECandidates` |
| Offers | `/hcmRestApi/resources/latest/recruitingCEOffers` |
| Interview Schedules | `/hcmRestApi/resources/latest/recruitingCEInterviewSchedules` |
| Source Tracking | `/hcmRestApi/resources/latest/recruitingCESourceTracking` |
