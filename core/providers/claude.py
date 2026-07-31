import requests
import json

CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


def call(prompt, api_key):
    """Sends prompt to Anthropic Claude. Returns the text response, or None on failure."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=90)
    except requests.exceptions.RequestException as e:
        print(f"Claude request failed with an exception: {e}")
        return None

    if response.status_code != 200:
        print(f"Claude API returned status {response.status_code}: {response.text}")
        return None

    try:
        return response.json()["content"][0]["text"]
    except (KeyError, IndexError):
        return None

def call_streaming(prompt, api_key):
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=body, timeout=90, stream=True)
    except requests.exceptions.RequestException as e:
        print(f"Claude streaming request failed: {e}")
        return

    if response.status_code != 200:
        print(f"Claude API returned status {response.status_code}: {response.text}")
        return

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            chunk = json.loads(line[len("data: "):])
        except json.JSONDecodeError:
            continue
        if chunk.get("type") == "content_block_delta":
            text = chunk.get("delta", {}).get("text")
            if text:
                yield text