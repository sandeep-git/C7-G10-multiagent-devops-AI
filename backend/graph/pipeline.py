"""LangGraph pipeline — HITL implemented via threading.Event for reliability."""
from __future__ import annotations
import threading
import uuid
from typing import Literal
from langgraph.graph import StateGraph, END
from ..schemas import AgentState
from ..agents import (
    run_log_classifier,
    run_remediation_agent,
    run_cookbook_synthesizer,
    run_jira_agent,
    run_notification_agent,
)

# ------------------------------------------------------------------
# In-memory state store  {run_id -> AgentState dict}
# HITL events           {run_id -> threading.Event}
# ------------------------------------------------------------------
_states: dict[str, dict] = {}
_hitl_events: dict[str, threading.Event] = {}


def _get(run_id: str) -> dict:
    return _states.get(run_id, {})


def _set(run_id: str, state: dict) -> None:
    _states[run_id] = state


# ------------------------------------------------------------------
# Node functions
# ------------------------------------------------------------------

def node_log_classifier(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "log_classifier"
    s.messages.append("Agent 1: Classifying logs and detecting anomalies...")
    _set(s.run_id, s.model_dump())
    try:
        result = run_log_classifier(s.raw_logs)
        s.log_analysis = result
        s.messages.append(
            f"Agent 1 complete: {len(result.anomalies)} anomaly(ies) found, "
            f"severity={result.overall_severity}/5, benign={result.is_benign}"
        )
    except Exception as exc:
        s.error = f"LogClassifier failed: {exc}"
        s.messages.append(f"ERROR in log_classifier: {exc}")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


def node_remediation(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "remediation_agent"
    s.messages.append("Agent 2: Querying vector store and planning remediation (RAG)...")
    _set(s.run_id, s.model_dump())
    try:
        result = run_remediation_agent(s.log_analysis)
        s.remediation_strategy = result
        s.messages.append(
            f"Agent 2 complete: {len(result.issues)} issue(s) addressed, "
            f"overall confidence={result.overall_confidence:.0%}"
        )
    except Exception as exc:
        s.error = f"RemediationAgent failed: {exc}"
        s.messages.append(f"ERROR in remediation_agent: {exc}")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


def node_cookbook(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "cookbook_synthesizer"
    s.messages.append("Agent 3: Synthesizing executable runbook...")
    _set(s.run_id, s.model_dump())
    try:
        result = run_cookbook_synthesizer(s.remediation_strategy)
        s.runbook = result
        s.messages.append(
            f"Agent 3 complete: Runbook '{result.title}' created, "
            f"{len(result.steps)} step(s), ~{result.estimated_time_minutes} min"
        )
    except Exception as exc:
        s.error = f"CookbookSynthesizer failed: {exc}"
        s.messages.append(f"ERROR in cookbook_synthesizer: {exc}")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


def node_hitl_gate(state: dict) -> dict:
    """Block here until the API sets the threading.Event (approval/rejection)."""
    s = AgentState(**state)
    s.current_node = "hitl_approval"
    s.messages.append("HITL: Awaiting human approval before triggering external systems...")
    _set(s.run_id, s.model_dump())

    # Wait for human decision — blocks the pipeline thread, not the API thread
    event = _hitl_events.get(s.run_id)
    if event:
        event.wait(timeout=3600)  # wait up to 1 hour

    # Read the decision that was written by the approve endpoint
    latest = _get(s.run_id)
    s = AgentState(**latest)
    return s.model_dump()


def node_jira(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "jira_agent"
    s.messages.append("Agent 4: Creating Jira ticket...")
    _set(s.run_id, s.model_dump())
    try:
        result = run_jira_agent(s.log_analysis, s.runbook)
        s.jira_result = result
        s.external_links["jira"] = result.ticket_url or ""
        s.messages.append(f"Agent 4 complete: Jira ticket created → {result.ticket_url}")
    except Exception as exc:
        s.error = f"JiraAgent failed: {exc}"
        s.messages.append(f"ERROR in jira_agent: {exc}")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


def node_slack(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "notification_agent"
    s.messages.append("Agent 5: Sending Slack notification...")
    _set(s.run_id, s.model_dump())
    try:
        # Pass jira_result so the Slack message includes ticket link + priority
        result = run_notification_agent(s.log_analysis, s.runbook, s.jira_result)
        s.slack_result = result
        s.external_links["slack"] = result.thread_url or ""
        s.messages.append(f"Agent 5 complete: Slack notification sent → {result.thread_url}")
    except Exception as exc:
        s.error = f"NotificationAgent failed: {exc}"
        s.messages.append(f"ERROR in notification_agent: {exc}")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


def node_end(state: dict) -> dict:
    s = AgentState(**state)
    s.current_node = "end"
    s.messages.append("Pipeline complete.")
    _set(s.run_id, s.model_dump())
    return s.model_dump()


# ------------------------------------------------------------------
# Routing
# ------------------------------------------------------------------

def route_after_classifier(state: dict) -> Literal["remediation_agent", "end"]:
    s = AgentState(**state)
    if s.error or (s.log_analysis and s.log_analysis.is_benign):
        return "end"
    return "remediation_agent"


def route_after_hitl(state: dict) -> Literal["jira_agent", "end"]:
    s = AgentState(**state)
    if s.approval_status == "approved":
        return "jira_agent"
    return "end"


# ------------------------------------------------------------------
# Build graph (no checkpointer needed — state lives in _states dict)
# ------------------------------------------------------------------

def build_graph() -> StateGraph:
    builder = StateGraph(dict)
    builder.add_node("log_classifier",       node_log_classifier)
    builder.add_node("remediation_agent",    node_remediation)
    builder.add_node("cookbook_synthesizer", node_cookbook)
    builder.add_node("hitl_approval",        node_hitl_gate)
    builder.add_node("jira_agent",           node_jira)
    builder.add_node("notification_agent",   node_slack)
    builder.add_node("end",                  node_end)

    builder.set_entry_point("log_classifier")
    builder.add_conditional_edges("log_classifier", route_after_classifier,
                                   {"remediation_agent": "remediation_agent", "end": "end"})
    builder.add_edge("remediation_agent",    "cookbook_synthesizer")
    builder.add_edge("cookbook_synthesizer", "hitl_approval")
    builder.add_conditional_edges("hitl_approval", route_after_hitl,
                                   {"jira_agent": "jira_agent", "end": "end"})
    builder.add_edge("jira_agent",           "notification_agent")
    builder.add_edge("notification_agent",   "end")
    builder.add_edge("end",                  END)
    return builder.compile()


_graph = build_graph()


def get_graph():
    return _graph


def new_run_id() -> str:
    return str(uuid.uuid4())


def get_run_state(run_id: str) -> dict:
    return _get(run_id)


def set_run_state(run_id: str, state: dict) -> None:
    _set(run_id, state)


def create_hitl_event(run_id: str) -> threading.Event:
    event = threading.Event()
    _hitl_events[run_id] = event
    return event


def signal_hitl(run_id: str) -> None:
    """Called by the approve endpoint to unblock the pipeline thread."""
    event = _hitl_events.get(run_id)
    if event:
        event.set()
