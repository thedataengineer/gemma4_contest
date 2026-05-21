"""
Shared local-LLM client for GemmaAudit.

Wraps the OpenAI-compatible /chat/completions endpoint exposed by local
inference servers (Ollama, llama.cpp, vLLM, LM Studio). Both the chat agent
loop (`backend/main.py`) and the JCL semantic enrichment pass
(`backend/jcl_parser.py`) call into this module so there is exactly one
place that knows how to reach the model.
"""
import os
import re
import requests
from typing import List, Dict, Any, Optional, Tuple


# Reasoning-mode models (Qwen3, DeepSeek-R1, QwQ, gpt-oss-thinking, ...) emit a
# <think>...</think> monologue before their actual answer. For enrichment passes
# we want only the final answer, so strip those blocks defensively.
_REASONING_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def strip_reasoning_tags(text: str) -> str:
    """Removes <think>...</think> reasoning blocks and any orphaned tag."""
    if not text:
        return text
    cleaned = _REASONING_TAG_RE.sub("", text)
    # Drop a dangling/unclosed tag if the model truncated mid-monologue.
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _completions_url() -> str:
    url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1").rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    return url


def _model() -> str:
    return os.getenv("LOCAL_LLM_MODEL", "gemma4-unsloth")


def call_local_llm(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 0.3,
    timeout: Tuple[int, int] = (5, 60),
) -> Dict[str, Any]:
    """Low-level OpenAI-compatible chat completions call. Returns raw JSON."""
    payload: Dict[str, Any] = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools

    response = requests.post(
        _completions_url(),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def call_local_llm_simple(
    messages: List[Dict[str, Any]],
    timeout_seconds: int = 12,
    temperature: float = 0.2,
) -> Optional[str]:
    """Convenience wrapper: returns just the assistant content, or None on failure.

    Designed for enrichment passes that should silently fall back to regex/template
    output if the local model server is unreachable or slow.
    """
    try:
        res = call_local_llm(
            messages,
            tools=None,
            temperature=temperature,
            timeout=(3, timeout_seconds),
        )
        content = res["choices"][0]["message"].get("content", "")
        content = strip_reasoning_tags(content)
        return content or None
    except Exception:
        return None


def is_local_llm_available() -> bool:
    """Quick reachability probe against the model server root."""
    try:
        base = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1").rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        r = requests.get(base, timeout=2)
        return r.status_code < 500
    except Exception:
        return False
