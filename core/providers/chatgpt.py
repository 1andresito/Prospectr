import requests
import json

CHATGPT_MODEL = "gpt-4o-mini"
CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"


def call(prompt, api_key):
    """Sends prompt to OpenAI's ChatGPT API. Returns the text response, or None on failure."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": CHATGPT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.5,
    }

    try:
        response = requests.post(CHATGPT_API_URL, headers=headers, json=body, timeout=90)
    except requests.exceptions.RequestException as e:
        print(f"ChatGPT request failed with an exception: {e}")
        return None

    if response.status_code != 200:
        print(f"ChatGPT API returned status {response.status_code}: {response.text}")
        return None

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None

def call_streaming(prompt, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": CHATGPT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.5,
        "stream": True,
    }

    try:
        response = requests.post(CHATGPT_API_URL, headers=headers, json=body, timeout=90, stream=True)
    except requests.exceptions.RequestException as e:
        print(f"ChatGPT streaming request failed: {e}")
        return

    if response.status_code != 200:
        print(f"ChatGPT API returned status {response.status_code}: {response.text}")
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