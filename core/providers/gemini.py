import json

import requests

from providers import TRUNCATED, ProviderError, error_detail

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:streamGenerateContent"
)

MAX_OUTPUT_TOKENS = 16000
READ_TIMEOUT_SECONDS = 120


def _iter_text(candidate):
    for part in candidate.get("content", {}).get("parts", []):
        text = part.get("text")
        if text:
            yield text


def call_streaming(prompt, api_key):
    """Yield the analysis from Google's Gemini streaming endpoint."""
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key, "alt": "sse"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.5,
        },
    }

    try:
        response = requests.post(
            GEMINI_STREAM_URL,
            headers=headers,
            params=params,
            json=body,
            timeout=READ_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.exceptions.RequestException as exc:
        raise ProviderError(f"Could not contact Gemini: {exc}") from exc

    if response.status_code != 200:
        raise ProviderError(error_detail(response, "Gemini"))

    hit_cap = False

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue

        try:
            chunk = json.loads(line[len("data: "):])
            candidate = chunk["candidates"][0]
        except (json.JSONDecodeError, KeyError, IndexError):
            continue

        yield from _iter_text(candidate)

        if candidate.get("finishReason") == "MAX_TOKENS":
            hit_cap = True

    if hit_cap:
        yield TRUNCATED
