"""Helpers for parsing structured LLM output."""

from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of LLM output (handles code fences)."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]!r}")
    return json.loads(match.group(0))
