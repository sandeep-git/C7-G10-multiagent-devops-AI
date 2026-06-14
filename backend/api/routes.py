"""FastAPI application: REST + SSE endpoints for the DevOps Incident Analysis Suite."""
from __future__ import annotations
import asyncio
import json
import os
import threading
from typing import Any
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..schemas import AgentState
from ..graph import (
    get_graph, new_run_id,
    get_run_state, set_run_state,
    create_hitl_event, signal_hitl,
)

app = FastAPI(title="DevOps Incident Analysis Suite", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tracks which run_ids exist in this session
_run_ids: set[str] = set()


# ------------------------------------------------------------------ #
# Request / Response models
# ------------------------------------------------------------------ #

class AnalyzeRequest(BaseModel):
    logs: str


class ApprovalRequest(BaseModel):
    run_id: str
    decision: str  # "approved" | "rejected"


class RunStatusResponse(BaseModel):
    run_id: str
    current_node: str
    approval_status: str
    messages: list[str]
    external_links: dict[str, str]
    log_analysis: Any
    remediation_strategy: Any
    runbook: Any
    jira_result: Any
    slack_result: Any
    error: str | None


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _state_to_response(state: dict) -> RunStatusResponse:
    s = AgentState(**state)
    return RunStatusResponse(
        run_id=s.run_id,
        current_node=s.current_node,
        approval_status=s.approval_status,
        messages=s.messages,
        external_links=s.external_links,
        log_analysis=s.log_analysis.model_dump() if s.log_analysis else None,
        remediation_strategy=s.remediation_strategy.model_dump() if s.remediation_strategy else None,
        runbook=s.runbook.model_dump() if s.runbook else None,
        jira_result=s.jira_result.model_dump() if s.jira_result else None,
        slack_result=s.slack_result.model_dump() if s.slack_result else None,
        error=s.error,
    )


def _run_pipeline(run_id: str, initial_state: dict):
    """Run the full LangGraph pipeline in a background thread."""
    graph = get_graph()
    try:
        for _ in graph.stream(initial_state, config={"configurable": {"thread_id": run_id}}):
            pass
    except Exception as exc:
        state = get_run_state(run_id) or initial_state
        state["error"] = str(exc)
        state["messages"] = state.get("messages", []) + [f"Fatal error: {exc}"]
        state["current_node"] = "end"
        set_run_state(run_id, state)


# ------------------------------------------------------------------ #
# Endpoints
# ------------------------------------------------------------------ #

@app.post("/api/analyze", response_model=RunStatusResponse)
async def analyze_logs(request: AnalyzeRequest):
    run_id = new_run_id()
    initial_state = AgentState(run_id=run_id, raw_logs=request.logs).model_dump()
    _run_ids.add(run_id)
    set_run_state(run_id, initial_state)
    create_hitl_event(run_id)
    threading.Thread(target=_run_pipeline, args=(run_id, initial_state), daemon=True).start()
    return _state_to_response(initial_state)


@app.post("/api/analyze/upload", response_model=RunStatusResponse)
async def analyze_upload(file: UploadFile = File(...)):
    content = await file.read()
    logs = content.decode("utf-8", errors="replace")
    run_id = new_run_id()
    initial_state = AgentState(run_id=run_id, raw_logs=logs).model_dump()
    _run_ids.add(run_id)
    set_run_state(run_id, initial_state)
    create_hitl_event(run_id)
    threading.Thread(target=_run_pipeline, args=(run_id, initial_state), daemon=True).start()
    return _state_to_response(initial_state)


@app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str):
    if run_id not in _run_ids:
        raise HTTPException(status_code=404, detail="Run not found")
    state = get_run_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run state not found")
    return _state_to_response(state)


@app.post("/api/runs/{run_id}/approve", response_model=RunStatusResponse)
async def approve_run(run_id: str, body: ApprovalRequest):
    if run_id not in _run_ids:
        raise HTTPException(status_code=404, detail="Run not found")
    decision = body.decision.lower()
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")

    state = get_run_state(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="Run state not found")
    if state.get("current_node") != "hitl_approval":
        raise HTTPException(status_code=400, detail="Run is not awaiting approval")

    # Write decision into state BEFORE signalling the pipeline thread
    state["approval_status"] = decision
    state["messages"] = state.get("messages", []) + [f"HITL: Human decision → {decision}"]
    set_run_state(run_id, state)

    # Unblock the pipeline thread waiting in node_hitl_gate
    signal_hitl(run_id)

    return _state_to_response(state)


@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    """Server-Sent Events: polls state dict and streams diffs to the client."""
    async def event_generator():
        last_msg_count = 0
        last_node = ""
        for _ in range(1200):
            await asyncio.sleep(0.5)
            if run_id not in _run_ids:
                yield f"data: {json.dumps({'error': 'run not found'})}\n\n"
                return
            state = get_run_state(run_id)
            if not state:
                continue
            try:
                s = AgentState(**state)
            except Exception:
                continue

            new_msgs = s.messages[last_msg_count:]
            if new_msgs or s.current_node != last_node:
                last_msg_count = len(s.messages)
                last_node = s.current_node
                payload = {
                    "current_node": s.current_node,
                    "approval_status": s.approval_status,
                    "new_messages": new_msgs,
                    "external_links": s.external_links,
                    "error": s.error,
                    "log_analysis": s.log_analysis.model_dump() if s.log_analysis else None,
                    "remediation_strategy": s.remediation_strategy.model_dump() if s.remediation_strategy else None,
                    "runbook": s.runbook.model_dump() if s.runbook else None,
                    "jira_result": s.jira_result.model_dump() if s.jira_result else None,
                    "slack_result": s.slack_result.model_dump() if s.slack_result else None,
                }
                yield f"data: {json.dumps(payload)}\n\n"
            if s.current_node in ("end", "hitl_approval") or s.error:
                yield f"data: {json.dumps({'done': True, 'current_node': s.current_node})}\n\n"
                return
        yield f"data: {json.dumps({'error': 'stream timeout'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
