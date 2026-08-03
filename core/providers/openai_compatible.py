"""
Streaming helper shared by the providers that speak the OpenAI
chat-completions dialect (OpenAI itself and NVIDIA's NIM endpoint).
"""
import json

import requests

from providers import TRUNCATED, ProviderError, error_detail

READ_TIMEOUT_SECONDS = 120


def stream_chat_completions(url, api_key, model, prompt, max_tokens, label):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "stream": True,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=READ_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.exceptions.RequestException as exc:
        raise ProviderError(f"Could not contact {label}: {exc}") from exc

    if response.status_code != 200:
        raise ProviderError(error_detail(response, label))

    hit_cap = False

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue

        payload = line[len("data: "):]
        if payload.strip() == "[DONE]":
            break

        try:
            chunk = json.loads(payload)
            choice = chunk["choices"][0]
        except (json.JSONDecodeError, KeyError, IndexError):
            continue

        delta = choice.get("delta", {}).get("content")
        if delta:
            yield delta

        if choice.get("finish_reason") == "length":
            hit_cap = True

    if hit_cap:
        yield TRUNCATED
