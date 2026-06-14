"""Agent 5: Slack Notification Agent — posts Block Kit messages with Jira ticket details."""
from __future__ import annotations
import os
import json
import urllib.request
import urllib.error
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..schemas import LogAnalysisResult, ActionableRunbook, JiraPayload, SlackNotification
from .llm import get_llm

_SEVERITY_EMOJI = {1: ":white_check_mark:", 2: ":large_green_circle:", 3: ":warning:",
                   4: ":red_circle:", 5: ":rotating_light:"}
_SEVERITY_COLOR = {1: "#36a64f", 2: "#2eb67d", 3: "#ecb22e", 4: "#e01e5a", 5: "#8B0000"}

_SYSTEM = """You are a Slack communication expert for a DevOps team. Generate Slack Block Kit JSON blocks for an incident alert that includes the linked Jira ticket.

Rules:
- Block 1: header — severity emoji + incident title (plain_text).
- Block 2: section — short root cause summary (2-3 sentences, mrkdwn).
- Block 3: divider.
- Block 4: section with fields — Severity, Affected Services, ETA, Steps.
- Block 5: divider.
- Block 6: section with Jira ticket info — ticket ID as a clickable link, priority, assignee. Use mrkdwn format: *Jira Ticket:* <url|KEY-123>
- Keep it scannable. Return ONLY a valid JSON array of Slack block objects. No markdown fences."""

_HUMAN = """Severity: {severity}/5
Services: {services}
Root Cause: {root_cause}
Runbook Title: {runbook_title}
ETA: {eta} minutes
Steps: {steps}

Jira Ticket ID: {jira_key}
Jira Ticket URL: {jira_url}
Jira Priority: {jira_priority}
Jira Summary: {jira_summary}

Generate the Slack Block Kit blocks array."""

_parser = JsonOutputParser()
_prompt = ChatPromptTemplate.from_messages([("system", _SYSTEM), ("human", _HUMAN)])


def _post_to_slack(blocks: list, text: str) -> str | None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url or "YOUR/WEBHOOK" in webhook_url:
        return None
    payload = {"text": text, "blocks": blocks}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.read().decode() == "ok":
                return webhook_url
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Slack webhook error {e.code}: {e.read().decode()}") from e
    return None


def _build_fallback_blocks(
    analysis: LogAnalysisResult,
    runbook: ActionableRunbook,
    jira: Optional[JiraPayload] = None,
) -> list:
    sev = analysis.overall_severity
    emoji = _SEVERITY_EMOJI.get(sev, ":warning:")
    services = ", ".join(analysis.affected_services)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Incident Alert: {runbook.title}"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root Cause:* {analysis.root_cause_hypothesis[:200]}"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Severity:*\n{sev}/5"},
                {"type": "mrkdwn", "text": f"*Services:*\n{services}"},
                {"type": "mrkdwn", "text": f"*ETA:*\n~{runbook.estimated_time_minutes} min"},
                {"type": "mrkdwn", "text": f"*Steps:*\n{len(runbook.steps)} steps"},
            ]
        },
    ]

    # Add Jira block if available
    if jira and jira.ticket_url:
        # Extract key from URL e.g. https://site.atlassian.net/browse/JIRA-3 → JIRA-3
        jira_key = jira.ticket_url.rstrip("/").split("/")[-1]
        blocks += [
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Jira Ticket:*\n<{jira.ticket_url}|{jira_key}>"},
                    {"type": "mrkdwn", "text": f"*Priority:*\n{jira.priority}"},
                    {"type": "mrkdwn", "text": f"*Summary:*\n{jira.summary[:80]}"},
                    {"type": "mrkdwn", "text": f"*Labels:*\n{', '.join(jira.labels) if jira.labels else 'incident'}"},
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🎫 Open Jira Ticket"},
                        "style": "primary",
                        "url": jira.ticket_url,
                    }
                ]
            },
        ]

    return blocks


def run_notification_agent(
    analysis: LogAnalysisResult,
    runbook: ActionableRunbook,
    jira: Optional[JiraPayload] = None,
) -> SlackNotification:
    channel = os.getenv("SLACK_CHANNEL", "#incidents")

    # Extract Jira details for prompt
    jira_key     = jira.ticket_url.rstrip("/").split("/")[-1] if jira and jira.ticket_url else "N/A"
    jira_url     = jira.ticket_url if jira and jira.ticket_url else "N/A"
    jira_priority = jira.priority if jira else "N/A"
    jira_summary  = jira.summary[:100] if jira else "N/A"

    try:
        chain = _prompt | get_llm() | _parser
        blocks = chain.invoke({
            "severity":      analysis.overall_severity,
            "services":      ", ".join(analysis.affected_services),
            "root_cause":    analysis.root_cause_hypothesis,
            "runbook_title": runbook.title,
            "eta":           runbook.estimated_time_minutes,
            "steps":         len(runbook.steps),
            "jira_key":      jira_key,
            "jira_url":      jira_url,
            "jira_priority": jira_priority,
            "jira_summary":  jira_summary,
        })
        if not isinstance(blocks, list):
            blocks = _build_fallback_blocks(analysis, runbook, jira)
    except Exception:
        blocks = _build_fallback_blocks(analysis, runbook, jira)

    fallback_text = (
        f"[{analysis.overall_severity}/5] {runbook.title} | "
        f"Services: {', '.join(analysis.affected_services)} | "
        f"Jira: {jira_key} {jira_url}"
    )

    webhook_url = _post_to_slack(blocks, fallback_text)
    thread_url = webhook_url if webhook_url else (
        f"https://slack.com/archives/{channel.lstrip('#')} (webhook not configured)"
    )

    return SlackNotification(channel=channel, blocks=blocks, thread_url=thread_url)
