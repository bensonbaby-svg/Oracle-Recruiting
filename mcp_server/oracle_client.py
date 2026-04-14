"""
Oracle HCM Cloud REST API Client

Connects to Oracle HCM Cloud and fetches recruiting data via REST APIs.
Supports Basic Auth and OAuth 2.0 authentication.

Oracle HCM REST API Docs:
  https://<host>/hcmRestApi/resources/latest/
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OracleAuthError(Exception):
    pass


class OracleAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Oracle API error {status_code}: {message}")


class OracleHCMClient:
    """
    Client for Oracle HCM Cloud REST APIs.

    Supports both Basic Auth and OAuth 2.0. Basic Auth is used by default.
    Set ORACLE_CLIENT_ID / ORACLE_CLIENT_SECRET env vars to switch to OAuth.
    """

    BASE_PATH = "/hcmRestApi/resources"

    def __init__(
        self,
        host: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_url: Optional[str] = None,
        api_version: str = "latest",
        timeout: int = 30,
    ):
        self.host = (host or os.getenv("ORACLE_HCM_HOST", "")).rstrip("/")
        self.username = username or os.getenv("ORACLE_USERNAME", "")
        self.password = password or os.getenv("ORACLE_PASSWORD", "")
        self.client_id = client_id or os.getenv("ORACLE_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("ORACLE_CLIENT_SECRET", "")
        self.token_url = token_url or os.getenv("ORACLE_TOKEN_URL", "")
        self.api_version = api_version or os.getenv("ORACLE_API_VERSION", "latest")
        self.timeout = int(os.getenv("ORACLE_REQUEST_TIMEOUT", str(timeout)))
        self.max_results = int(os.getenv("ORACLE_MAX_RESULTS", "500"))

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

        if not self.host:
            raise ValueError(
                "Oracle HCM host is required. Set ORACLE_HCM_HOST environment variable."
            )

        self.base_url = f"https://{self.host}{self.BASE_PATH}/{self.api_version}"

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _use_oauth(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get_oauth_token(self) -> str:
        if (
            self._access_token
            and self._token_expiry
            and datetime.utcnow() < self._token_expiry
        ):
            return self._access_token

        url = self.token_url or f"https://{self.host}/oauth/oauthservice/token"
        resp = httpx.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise OracleAuthError(f"OAuth token request failed: {resp.text}")

        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = datetime.utcnow() + timedelta(
            seconds=int(data.get("expires_in", 3600)) - 60
        )
        return self._access_token

    def _auth_headers(self) -> dict:
        if self._use_oauth():
            token = self._get_oauth_token()
            return {"Authorization": f"Bearer {token}"}
        import base64
        creds = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, resource: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{resource}"
        headers = {
            **self._auth_headers(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        logger.debug("GET %s params=%s", url, params)
        resp = httpx.get(url, headers=headers, params=params, timeout=self.timeout)
        if resp.status_code in (401, 403):
            raise OracleAuthError(f"Authentication failed ({resp.status_code})")
        if resp.status_code >= 400:
            raise OracleAPIError(resp.status_code, resp.text[:500])
        return resp.json()

    def _paginate(self, resource: str, params: Optional[dict] = None, limit: int = 0) -> list[dict]:
        """Fetch all pages for a collection resource."""
        params = dict(params or {})
        page_size = min(self.max_results, 100)
        params.setdefault("limit", page_size)
        params.setdefault("offset", 0)

        results: list[dict] = []
        while True:
            data = self._get(resource, params)
            items = data.get("items", [])
            results.extend(items)
            if limit and len(results) >= limit:
                return results[:limit]
            # Oracle uses 'hasMore' and 'offset' for pagination
            if not data.get("hasMore", False):
                break
            params["offset"] = params["offset"] + len(items)

        return results

    # ------------------------------------------------------------------
    # Recruiting Endpoints
    # ------------------------------------------------------------------

    def get_job_requisitions(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        location: Optional[str] = None,
        date_from: Optional[str] = None,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch job requisitions from Oracle Recruiting.

        Args:
            status: Filter by requisition status (e.g. 'Open', 'Filled', 'Canceled')
            department: Filter by department name
            location: Filter by location name
            date_from: ISO date string (YYYY-MM-DD) to filter by creation date
            limit: Max records (0 = all)
        """
        params: dict = {
            "fields": (
                "RequisitionId,RequisitionNumber,Title,RequisitionStatus,"
                "Department,Location,HiringManager,Recruiter,"
                "TargetStartDate,CreationDate,FilledDate,"
                "NumberOfOpenings,NumberOfHires,JobFamily,WorkLocation"
            ),
        }
        filters = []
        if status:
            filters.append(f'RequisitionStatus="{status}"')
        if department:
            filters.append(f'Department="{department}"')
        if location:
            filters.append(f'Location="{location}"')
        if date_from:
            filters.append(f"CreationDate>={date_from}")
        if filters:
            params["q"] = ";".join(filters)

        return self._paginate("recruitingCEJobRequisitions", params, limit=limit)

    def get_job_applications(
        self,
        requisition_id: Optional[str] = None,
        phase: Optional[str] = None,
        state: Optional[str] = None,
        date_from: Optional[str] = None,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch job applications.

        Args:
            requisition_id: Filter by requisition ID
            phase: Filter by phase (e.g. 'Screening', 'Interview', 'Offer')
            state: Filter by state (e.g. 'Active', 'Rejected', 'Withdrawn')
            date_from: ISO date string (YYYY-MM-DD)
            limit: Max records (0 = all)
        """
        params: dict = {
            "fields": (
                "JobApplicationId,RequisitionId,CandidateId,"
                "CandidateName,Phase,State,AppliedDate,"
                "LastUpdatedDate,Source,Referral,"
                "InterviewScore,OfferExtended,OfferAccepted"
            ),
        }
        filters = []
        if requisition_id:
            filters.append(f'RequisitionId="{requisition_id}"')
        if phase:
            filters.append(f'Phase="{phase}"')
        if state:
            filters.append(f'State="{state}"')
        if date_from:
            filters.append(f"AppliedDate>={date_from}")
        if filters:
            params["q"] = ";".join(filters)

        return self._paginate("recruitingCEJobApplications", params, limit=limit)

    def get_candidates(
        self,
        candidate_id: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch candidate profiles.

        Args:
            candidate_id: Fetch a single candidate by ID
            name: Filter by candidate name (partial match)
            limit: Max records (0 = all)
        """
        resource = "recruitingCECandidates"
        if candidate_id:
            resource = f"recruitingCECandidates/{candidate_id}"

        params: dict = {
            "fields": (
                "CandidateId,FirstName,LastName,Email,Phone,"
                "SourceMedium,SourceType,CreationDate,"
                "LastActivityDate,TotalApplications,Skills"
            ),
        }
        if name:
            params["q"] = f'Name LIKE "%{name}%"'

        if candidate_id:
            data = self._get(resource, params)
            return [data]
        return self._paginate(resource, params, limit=limit)

    def get_offers(
        self,
        requisition_id: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch offer records.

        Args:
            requisition_id: Filter by requisition
            status: Filter by offer status (e.g. 'Accepted', 'Declined', 'Pending')
            date_from: ISO date string (YYYY-MM-DD)
            limit: Max records (0 = all)
        """
        params: dict = {
            "fields": (
                "OfferId,JobApplicationId,RequisitionId,CandidateId,"
                "OfferStatus,OfferDate,ExpirationDate,AcceptedDate,"
                "DeclinedDate,DeclineReason,OfferedSalary,Currency"
            ),
        }
        filters = []
        if requisition_id:
            filters.append(f'RequisitionId="{requisition_id}"')
        if status:
            filters.append(f'OfferStatus="{status}"')
        if date_from:
            filters.append(f"OfferDate>={date_from}")
        if filters:
            params["q"] = ";".join(filters)

        return self._paginate("recruitingCEOffers", params, limit=limit)

    def get_interview_schedules(
        self,
        requisition_id: Optional[str] = None,
        date_from: Optional[str] = None,
        limit: int = 0,
    ) -> list[dict]:
        """
        Fetch interview schedule records.

        Args:
            requisition_id: Filter by requisition
            date_from: ISO date string (YYYY-MM-DD)
            limit: Max records (0 = all)
        """
        params: dict = {
            "fields": (
                "InterviewId,JobApplicationId,RequisitionId,"
                "CandidateId,InterviewType,ScheduledDate,"
                "InterviewStatus,InterviewerName,Score,Feedback"
            ),
        }
        filters = []
        if requisition_id:
            filters.append(f'RequisitionId="{requisition_id}"')
        if date_from:
            filters.append(f"ScheduledDate>={date_from}")
        if filters:
            params["q"] = ";".join(filters)

        return self._paginate("recruitingCEInterviewSchedules", params, limit=limit)

    def get_source_tracking(self, date_from: Optional[str] = None, limit: int = 0) -> list[dict]:
        """Fetch source tracking / referral analytics."""
        params: dict = {
            "fields": (
                "SourceId,SourceName,SourceType,SourceMedium,"
                "ApplicationCount,HireCount,CostPerHire"
            ),
        }
        if date_from:
            params["q"] = f"ApplicationDate>={date_from}"
        return self._paginate("recruitingCESourceTracking", params, limit=limit)


# ---------------------------------------------------------------------------
# Mock client for development / testing without a live Oracle instance
# ---------------------------------------------------------------------------

class MockOracleHCMClient(OracleHCMClient):
    """
    Returns realistic synthetic data so you can develop and test without
    a live Oracle HCM Cloud environment.
    """

    def __init__(self):
        # Skip parent __init__ (no host required)
        self.max_results = 500
        self._access_token = None
        self._token_expiry = None

    def get_job_requisitions(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_REQUISITIONS
        data = MOCK_REQUISITIONS
        if kwargs.get("status"):
            data = [r for r in data if r["RequisitionStatus"] == kwargs["status"]]
        if kwargs.get("department"):
            data = [r for r in data if r["Department"] == kwargs["department"]]
        lim = kwargs.get("limit", 0)
        return data[:lim] if lim else data

    def get_job_applications(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_APPLICATIONS
        data = MOCK_APPLICATIONS
        if kwargs.get("requisition_id"):
            data = [a for a in data if a["RequisitionId"] == kwargs["requisition_id"]]
        if kwargs.get("phase"):
            data = [a for a in data if a["Phase"] == kwargs["phase"]]
        if kwargs.get("state"):
            data = [a for a in data if a["State"] == kwargs["state"]]
        lim = kwargs.get("limit", 0)
        return data[:lim] if lim else data

    def get_candidates(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_CANDIDATES
        data = MOCK_CANDIDATES
        lim = kwargs.get("limit", 0)
        return data[:lim] if lim else data

    def get_offers(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_OFFERS
        data = MOCK_OFFERS
        if kwargs.get("status"):
            data = [o for o in data if o["OfferStatus"] == kwargs["status"]]
        lim = kwargs.get("limit", 0)
        return data[:lim] if lim else data

    def get_interview_schedules(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_INTERVIEWS
        data = MOCK_INTERVIEWS
        lim = kwargs.get("limit", 0)
        return data[:lim] if lim else data

    def get_source_tracking(self, **kwargs) -> list[dict]:
        from mcp_server._mock_data import MOCK_SOURCES
        return MOCK_SOURCES


def get_client(mock: bool = False) -> OracleHCMClient:
    """Factory: return a real or mock Oracle HCM client."""
    if mock or os.getenv("ORACLE_USE_MOCK", "false").lower() == "true":
        logger.info("Using MockOracleHCMClient (no live Oracle connection)")
        return MockOracleHCMClient()
    return OracleHCMClient()
