"""Agent 3: Cookbook Synthesizer — turns strategy into an executable runbook."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas import RemediationStrategy, ActionableRunbook
from .llm import get_llm

_SYSTEM = """You are a technical documentation expert and runbook author for a Fortune-500 engineering team.
Convert the remediation strategy into a precise, executable runbook checklist.

Constraints (MUST follow):
- Every shell command must be syntactically valid and copy-pasteable.
- Any destructive operation (rm, drop, delete, kill, restart) MUST have is_destructive=true and a warning.
- Include rollback steps for every significant action.
- Output valid Markdown in the markdown field.
- Estimate realistic time in minutes.

{format_instructions}"""

_HUMAN = """## Remediation Strategy
{strategy_text}

Synthesize this into an actionable runbook with specific shell commands and rollback steps."""

_parser = PydanticOutputParser(pydantic_object=ActionableRunbook)

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
]).partial(format_instructions=_parser.get_format_instructions())


def run_cookbook_synthesizer(strategy: RemediationStrategy) -> ActionableRunbook:
    strategy_text = "\n".join(
        f"Issue: {i.issue}\nFix: {i.fix}\nRationale: {i.rationale}\nConfidence: {i.confidence_score:.0%}"
        for i in strategy.issues
    )
    chain = _prompt | get_llm() | _parser
    return chain.invoke({"strategy_text": strategy_text})
