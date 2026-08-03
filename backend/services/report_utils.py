"""
Shared LLM-calling and response-parsing utilities for all "topic report"
generators (career, relationship, health, wealth). Extracted verbatim from
career_analysis.py, where the logic was already fully generic — nothing
here is career-specific.
"""
import json
import logging
import os
import re
import time
import requests
from typing import Optional

logger = logging.getLogger("starjyotish.report_utils")


def extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences and leading text."""
    stripped = re.sub(r"```(?:json)?\s*", "", raw).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    start = stripped.find("{")
    end   = stripped.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(stripped[start:end])
    raise ValueError(f"No valid JSON found in response (first 300 chars): {raw[:300]}")


# Model OpenRouter is asked for — set via OPENROUTER_MODEL so switching
# models is a config change, not a code change (see services/ai.py, which
# shares this same env var). Defaults to a $0/M-token free model.
_OPENROUTER_MODEL = (os.getenv("OPENROUTER_MODEL") or "openai/gpt-oss-20b:free").strip()


def _call_openrouter(prompt: str, system: str) -> str:
    """Call _OPENROUTER_MODEL via OpenRouter using OPENROUTER_API_KEY."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")
    or_messages = ([{"role": "system", "content": system}] if system else []) + \
                  [{"role": "user", "content": prompt}]
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://starjyotish.app"),
            "X-Title": os.getenv("OPENROUTER_SITE_NAME", "Star Jyotish"),
        },
        json={
            "model": _OPENROUTER_MODEL,
            "max_tokens": 7000,
            "messages": or_messages,
            "response_format": {"type": "json_object"},
        },
        timeout=90,
    )
    if resp.status_code in (402, 403):
        try:
            detail = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            detail = resp.text[:200]
        raise RuntimeError(f"OpenRouter {resp.status_code}: {detail}")
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_claude_direct(prompt: str, system: str) -> str:
    """Call Claude directly via the Anthropic SDK using ANTHROPIC_API_KEY."""
    import anthropic as _anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = _anthropic.Anthropic(api_key=api_key)
    create_kwargs: dict = dict(
        model="claude-sonnet-4-6",
        max_tokens=7000,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        create_kwargs["system"] = system
    msg = client.messages.create(**create_kwargs)
    return msg.content[0].text


def _call_groq(prompt: str, groq_system_prompt: str, groq_extra: str, groq_extra_header: str) -> str:
    """Call Groq/Llama with retry on 429, using the compact topic-specific system prompt."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        raise ValueError("GROQ_API_KEY not set")
    groq_system = groq_system_prompt
    if groq_extra:
        groq_system = groq_system + f"\n\n{groq_extra_header}\n" + groq_extra
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": groq_system},
                        {"role": "user",   "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=90,
            )
            if resp.status_code == 429:
                last_exc = RuntimeError(f"rate limited (HTTP 429) after {attempt + 1}/3 attempts")
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Groq API error: {last_exc}")


def call_llm(
    prompt: str,
    system: str = "",
    groq_extra: str = "",
    groq_system_prompt: str = "",
    groq_extra_header: str = "## ADDITIONAL CONTEXT",
    log_prefix: str = "report",
) -> tuple[dict, str]:
    """
    Tries providers in order: OpenRouter (OPENROUTER_MODEL) -> Anthropic
    (direct) -> Groq. Each stage is skipped if its API key isn't set in the
    environment; any other failure (timeout, rate limit, bad response) also
    falls through to the next stage.
    OpenRouter and Claude receive the full `system` prompt. `groq_system_prompt`
    is the compact, topic-specific system prompt Groq receives (to avoid 413
    Payload Too Large) — callers pass their own (e.g.
    skill_loader.GROQ_SYSTEM_PROMPT for career). `groq_extra` is a small,
    separately-bounded supplement appended on top of it under
    `groq_extra_header` (e.g. a single ascendant's gemstone excerpt, not the
    full skills bundle OpenRouter/Claude get). `log_prefix` tags console
    fallback logs by topic.
    A response that fails JSON parsing is raised immediately rather than
    falling back further, since a malformed response usually signals a
    prompt bug the next provider would likely also hit.
    Returns (parsed_json, provider_label) — provider_label reflects whichever
    one actually served this request, since the fallback can kick in silently.
    """
    stages = [
        (_call_openrouter, (prompt, system), "OpenRouter"),
        (_call_claude_direct, (prompt, system), "Claude"),
        (_call_groq, (prompt, groq_system_prompt, groq_extra, groq_extra_header), "Groq · Llama"),
    ]
    reasons: list[str] = []
    for fn, call_args, label in stages:
        try:
            text = fn(*call_args)
        except ValueError as exc:
            reasons.append(f"{label}: {exc}")
            continue
        except Exception as exc:
            reasons.append(f"{label}: {type(exc).__name__}: {exc}")
            logger.warning("[%s] %s error (%s), trying next provider.", log_prefix, label, exc)
            continue
        try:
            return extract_json(text), label
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"{label} returned non-JSON: {e}") from e

    raise RuntimeError(f"No LLM provider available — {'; '.join(reasons)}")


_FORBIDDEN_TERM_REPLACEMENTS = [
    (r"\bdebilitated\b",          "in a transformative placement"),
    (r"\bin (?:an? )?enemy sign\b", "in a resilience-building sign"),
    (r"\benemy sign\b",            "resilience-building sign"),
    (r"\bafflicted\b",             "on a powerful growth journey"),
    (r"\bweak\b",                  "developing its strength"),
    (r"\bchallenging placement\b", "unique growth placement"),
    (r"\bposes challenges\b",      "creates unique opportunities"),
    (r"\bmalefic\b",               "dynamic"),
    (r"\bdebility\b",              "transformative phase"),
    (r"\bdifficult placement\b",   "growth-oriented placement"),
]


def filter_report_language(report: dict) -> dict:
    """
    Defense-in-depth safety net: every topic's prompt already instructs the
    LLM to avoid negative astrological terms (the "forbidden words" tone
    rule), but this catches anything that slips through anyway and replaces
    it with the empowering equivalent — same word list across every topic,
    since "debilitated"/"afflicted"/"malefic" etc. aren't career-specific
    terms. Extracted verbatim from career_analysis.py's original behavior.
    """
    def _clean(text: str) -> str:
        for pattern, repl in _FORBIDDEN_TERM_REPLACEMENTS:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        return text

    for key, val in report.items():
        if isinstance(val, dict):
            if "content" in val:
                val["content"] = _clean(val["content"])
            if "title" in val:
                val["title"] = _clean(val["title"])
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for k, v in item.items():
                        if isinstance(v, str):
                            item[k] = _clean(v)
    return report
