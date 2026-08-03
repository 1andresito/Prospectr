import json

import requests

from providers import TRUNCATED, ProviderError, error_detail

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-5"
ANTHROPIC_VERSION = "2023-06-01"

MAX_OUTPUT_TOKENS = 16000
READ_TIMEOUT_SECONDS = 120


def call_streaming(prompt, api_key):
    """Yield the analysis from Anthropic's Messages API."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    try:
        response = requests.post(
            CLAUDE_API_URL,
            headers=headers,
            json=body,
            timeout=READ_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.exceptions.RequestException as exc:
        raise ProviderError(f"Could not contact Claude: {exc}") from exc

    if response.status_code != 200:
        raise ProviderError(error_detail(response, "Claude"))

    hit_cap = False

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue

        try:
            chunk = json.loads(line[len("data: "):])
        except json.JSONDecodeError:
            continue

        chunk_type = chunk.get("type")

        if chunk_type == "content_block_delta":
            text = chunk.get("delta", {}).get("text")
            if text:
                yield text

        elif chunk_type == "message_delta":
            if chunk.get("delta", {}).get("stop_reason") == "max_tokens":
                hit_cap = True

        elif chunk_type == "error":
            message = chunk.get("error", {}).get("message", "unknown streaming error")
            raise ProviderError(f"Claude streaming error: {message}")

    if hit_cap:
        yield TRUNCATED
