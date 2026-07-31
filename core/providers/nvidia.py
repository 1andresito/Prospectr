import json
import requests

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"


def call(prompt, api_key):
    """Sends prompt to NVIDIA's API. Returns the text response, or None on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.5,
    }

    try:
        response = requests.post(NVIDIA_API_URL, headers=headers, json=body, timeout=240)
    except requests.exceptions.RequestException as e:
        print(f"NVIDIA request failed with an exception: {e}")
        return None

    if response.status_code != 200:
        print(f"NVIDIA API returned status {response.status_code}: {response.text}")
        return None

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None

def call_streaming(prompt, api_key):
    """
    Sends prompt to NVIDIA's API with streaming enabled. Yields text
    chunks as they're generated. Yields nothing (empty generator) on failure.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": NVIDIA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.5,
        "stream": True,
    }

    try:
        response = requests.post(NVIDIA_API_URL, headers=headers, json=body, timeout=90, stream=True)
    except requests.exceptions.RequestException as e:
        print(f"NVIDIA streaming request failed: {e}")
        return

    if response.status_code != 200:
        print(f"NVIDIA API returned status {response.status_code}: {response.text}")
        return

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        if payload.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
            delta = chunk["choices"][0]["delta"].get("content")
            if delta:
                yield delta
        except (json.JSONDecodeError, KeyError, IndexError):
            continue