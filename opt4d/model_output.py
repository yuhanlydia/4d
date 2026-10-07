"""Parsing helpers for structured model responses."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_response(response: str) -> Any:
    code_blocks = re.findall(
        r"```(?:json)?\s*(.*?)```", response, flags=re.DOTALL | re.IGNORECASE
    )
    payload = code_blocks[0].strip() if code_blocks else response.strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, count=1, flags=re.IGNORECASE)

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        start = next((i for i, char in enumerate(payload) if char in "{"), -1)
        if start < 0:
            start = next((i for i, char in enumerate(payload) if char == "["), -1)
        if start < 0:
            raise ValueError("model response contains no JSON object or array")
        try:
            parsed, _ = json.JSONDecoder().raw_decode(payload, start)
        except json.JSONDecodeError as exc:
            raise ValueError("model response contains no complete top-level JSON value") from exc
        return parsed

