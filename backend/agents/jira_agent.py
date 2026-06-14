"""Agent 4: Jira Ticketing Agent — creates a real Jira issue via REST API."""
from __future__ import annotations
import os
import base64
import json
import urllib.request
import urllib.error
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas import LogAnalysisResult, ActionableRunbook, JiraPayload
from .llm import get_llm

_SYSTEM = """You are a Jira project management expert. Create a well-structured Jira ticket from an incident analysis.

Priority mapping:
- Severity 5 → Highest
- Severity 4 → High
- Severity 3 → Medium
- Severity 2 → Low
- Severity 1 → Lowest

Story points: 1 (trivial) to 13 (complex multi-day effort).
Assignee routing: route to the team responsible for the first affected service.

{format_instructions}"""

_HUMAN = """## Incident Analysis
Overall Severity: {overall_severity}/5
Affected Services: {affected_services}
Root Cause: {root_cause}

## Runbook Summary
Title: {runbook_title}
Steps: {step_count} steps, ~{eta} minutes to resolve

Create the Jira ticket payload."""

_parser = PydanticOutputParser(pydantic_object=JiraPayload)
_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
]).partial(format_instructions=_parser.get_format_instructions())

PRIORITY_MAP = {
    "Highest": "Highest", "High": "High",
    "Medium": "Medium", "Low": "Low", "Lowest": "Lowest",
}


def _jira_auth_header() -> str:
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    creds = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {creds}"


def _create_jira_issue(payload: JiraPayload) -> str | None:
    """POST to Jira REST API v3 and return the created issue URL, or None on failure."""
    base_url  = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    project   = os.getenv("JIRA_PROJECT_KEY", "OPS")
    email     = os.getenv("JIRA_EMAIL", "")
    api_token = os.getenv("JIRA_API_TOKEN", "")

    # Skip real call if credentials not configured
    if not base_url or not email or not api_token or "your-" in base_url or "your-" in api_token:
        return None

    description_adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": payload.description}],
            }
        ],
    }

    body = {
        "fields": {
            "project":     {"key": project},
            "summary":     payload.summary,
            "description": description_adf,
            "issuetype":   {"name": "Bug"},
            "priority":    {"name": PRIORITY_MAP.get(payload.priority, "Medium")},
            "labels":      payload.labels or ["incident", "auto-generated"],
        }
    }

    url = f"{base_url}/rest/api/3/issue"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": _jira_auth_header(),
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            key = result.get("key", "")
            return f"{base_url}/browse/{key}" if key else None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Jira API error {e.code}: {error_body}") from e


def run_jira_agent(analysis: LogAnalysisResult, runbook: ActionableRunbook) -> JiraPayload:
    chain = _prompt | get_llm() | _parser
    payload = chain.invoke({
        "overall_severity": analysis.overall_severity,
        "affected_services": ", ".join(analysis.affected_services),
        "root_cause": analysis.root_cause_hypothesis,
        "runbook_title": runbook.title,
        "step_count": len(runbook.steps),
        "eta": runbook.estimated_time_minutes,
    })

    # Try real Jira API first; fall back to mock URL if creds not set
    real_url = _create_jira_issue(payload)
    if real_url:
        payload.ticket_url = real_url
    else:
        # Fallback mock URL (used when JIRA_API_TOKEN not configured yet)
        import uuid
        project = os.getenv("JIRA_PROJECT_KEY", "OPS")
        base_url = os.getenv("JIRA_BASE_URL", "https://your-site.atlassian.net").rstrip("/")
        ticket_id = f"{project}-{uuid.uuid4().hex[:4].upper()}"
        payload.ticket_url = f"{base_url}/browse/{ticket_id}"

    return payload
