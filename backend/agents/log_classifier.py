"""Agent 1: Log Ingestion & Anomaly Classifier."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas import LogAnalysisResult
from .llm import get_llm

_SYSTEM = """You are an elite Site Reliability Engineer specializing in log analysis and anomaly detection.
Your task is to analyze raw operational logs and identify all anomalies with precision.

Use few-shot reasoning: look for ERROR, WARN, FATAL, OOM, timeout, exception, stack traces,
latency spikes, connection failures, and unexpected service restarts.

Be systematic: identify timestamp patterns, correlate events across services, and hypothesize root causes.
Severity scale: 1=informational, 2=low, 3=medium, 4=high, 5=critical.

{format_instructions}"""

_HUMAN = """Analyze the following operational logs and extract all anomalies:

<logs>
{raw_logs}
</logs>

Return your structured analysis."""

_parser = PydanticOutputParser(pydantic_object=LogAnalysisResult)

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
]).partial(format_instructions=_parser.get_format_instructions())


def run_log_classifier(raw_logs: str) -> LogAnalysisResult:
    chain = _prompt | get_llm() | _parser
    return chain.invoke({"raw_logs": raw_logs})
