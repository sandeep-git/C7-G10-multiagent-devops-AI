from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Anomaly(BaseModel):
    timestamp: Optional[str] = None
    service: str
    severity: int = Field(..., ge=1, le=5)
    description: str
    stack_trace: Optional[str] = None


class LogAnalysisResult(BaseModel):
    anomalies: list[Anomaly]
    overall_severity: int = Field(..., ge=1, le=5)
    affected_services: list[str]
    root_cause_hypothesis: str
    is_benign: bool = False


class IssueRemediation(BaseModel):
    issue: str
    fix: str
    rationale: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class RemediationStrategy(BaseModel):
    issues: list[IssueRemediation]
    retrieved_playbooks: list[str] = Field(default_factory=list)
    overall_confidence: float


class RunbookStep(BaseModel):
    order: int
    description: str
    command: Optional[str] = None
    is_destructive: bool = False
    warning: Optional[str] = None


class ActionableRunbook(BaseModel):
    title: str
    estimated_time_minutes: int
    steps: list[RunbookStep]
    rollback_steps: list[RunbookStep]
    markdown: str


class JiraPayload(BaseModel):
    summary: str
    description: str
    priority: Literal["Highest", "High", "Medium", "Low", "Lowest"]
    epic: str
    story_points: int
    assignee: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
    ticket_url: Optional[str] = None


class SlackNotification(BaseModel):
    channel: str
    blocks: list[dict[str, Any]]
    thread_url: Optional[str] = None


class AgentState(BaseModel):
    run_id: str
    raw_logs: str = ""
    log_analysis: Optional[LogAnalysisResult] = None
    remediation_strategy: Optional[RemediationStrategy] = None
    runbook: Optional[ActionableRunbook] = None
    approval_status: Literal["pending", "approved", "rejected"] = "pending"
    jira_result: Optional[JiraPayload] = None
    slack_result: Optional[SlackNotification] = None
    external_links: dict[str, str] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)
    current_node: str = "start"
    error: Optional[str] = None
