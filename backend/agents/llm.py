"""Shared LLM initialization for all agents — uses OpenRouter (OpenAI-compatible)."""
from __future__ import annotations
import os
from langchain_openai import ChatOpenAI

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=4096,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "DevOps Incident Suite"),
            },
        )
    return _llm
