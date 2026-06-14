"""Agent 2: Remediation & Retrieval Engineer (RAG-powered)."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas import LogAnalysisResult, RemediationStrategy
from ..vectorstore import retrieve_similar_playbooks
from .llm import get_llm

_SYSTEM = """You are a senior DevOps engineer and incident responder with deep expertise in distributed systems.
You have been given an anomaly analysis report and relevant historical playbooks retrieved from the incident knowledge base.

Your job:
1. Carefully read each anomaly and the retrieved playbooks.
2. For EACH issue, propose a specific, actionable fix grounded in the playbooks.
3. Assign a confidence score (0.0-1.0) based on how well the playbooks match the current incident.
4. If no playbook matches, reason from first principles and set a lower confidence.

{format_instructions}"""

_HUMAN = """## Anomaly Analysis
Affected Services: {affected_services}
Root Cause Hypothesis: {root_cause_hypothesis}
Overall Severity: {overall_severity}/5

Anomalies:
{anomalies_text}

## Retrieved Historical Playbooks
{playbooks}

Generate the remediation strategy."""

_parser = PydanticOutputParser(pydantic_object=RemediationStrategy)

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
]).partial(format_instructions=_parser.get_format_instructions())


def run_remediation_agent(analysis: LogAnalysisResult) -> RemediationStrategy:
    query = f"{analysis.root_cause_hypothesis} {' '.join(analysis.affected_services)}"
    playbooks = retrieve_similar_playbooks(query, top_k=3)
    playbooks_text = "\n\n---\n\n".join(playbooks) if playbooks else "No matching playbooks found."

    anomalies_text = "\n".join(
        f"- [{a.severity}/5] {a.service}: {a.description}" for a in analysis.anomalies
    )

    chain = _prompt | get_llm() | _parser
    result = chain.invoke({
        "affected_services": ", ".join(analysis.affected_services),
        "root_cause_hypothesis": analysis.root_cause_hypothesis,
        "overall_severity": analysis.overall_severity,
        "anomalies_text": anomalies_text,
        "playbooks": playbooks_text,
    })
    result.retrieved_playbooks = playbooks
    return result
