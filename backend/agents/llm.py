"""Shared LLM initialization — supports OpenAI directly or OpenRouter."""
from __future__ import annotations
import os
from langchain_openai import ChatOpenAI

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        openai_key  = os.getenv("OPENAI_API_KEY", "")
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        if openai_key:
            # Direct OpenAI
            _llm = ChatOpenAI(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                openai_api_key=openai_key,
                max_tokens=4096,
            )
        else:
            # Fallback to OpenRouter
            _llm = ChatOpenAI(
                model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                openai_api_key=openrouter_key,
                openai_api_base="https://openrouter.ai/api/v1",
                max_tokens=4096,
                default_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000"),
                    "X-Title": os.getenv("OPENROUTER_SITE_NAME", "DevOps Incident Suite"),
                },
            )
    return _llm
