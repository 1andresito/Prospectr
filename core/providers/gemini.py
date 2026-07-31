import json
import requests

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

GEMINI_STREAM_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent"

def call(prompt, api_key):
    """Sends prompt to Google Gemini. Returns the text response, or None on failure."""
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.5},
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body, timeout=90)
    except requests.exceptions.RequestException as e:
        print(f"Gemini request failed with an exception: {e}")
        return None

    if response.status_code != 200:
        print(f"Gemini API returned status {response.status_code}: {response.text}")
        return None

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None

def call_streaming(prompt, api_key):
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key, "alt": "sse"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.5},
    }

    try:
        response = requests.post(GEMINI_STREAM_URL, headers=headers, params=params, json=body, timeout=90, stream=True)
    except requests.exceptions.RequestException as e:
        print(f"Gemini streaming request failed: {e}")
        return

    if response.status_code != 200:
        print(f"Gemini API returned status {response.status_code}: {response.text}")
        return

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            chunk = json.loads(line[len("data: "):])
            text = chunk["candidates"][0]["content"]["parts"][0]["text"]
            if text:
                yield text
        except (json.JSONDecodeError, KeyError, IndexError):
            continue