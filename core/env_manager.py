# env_manager.py
ENV_KEYS = [
    {"name": "GOOGLE_PLACES_API_KEY", "label": "Google Places API Key"},
    {"name": "AGENT_API_KEY", "label": "AI Agent API Key (Gemini / Claude / ChatGPT / NVIDIA)"},
]

AI_PROVIDERS = [
    {"value": "nvidia", "label": "NVIDIA"},
    {"value": "gemini", "label": "Google Gemini"},
    {"value": "claude", "label": "Anthropic Claude"},
    {"value": "chatgpt", "label": "OpenAI ChatGPT"},
]

DEFAULT_PROVIDER = "nvidia"


def _parse_env_file(path):
    # ... unchanged, keep your existing version ...
    values = {}
    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()

    return values


def _write_env_file(path, values):
    # ... unchanged ...
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n")


def get_key_status(env_path):
    # ... unchanged, keep your existing version ...
    current = _parse_env_file(env_path)
    status = []

    for key_def in ENV_KEYS:
        value = current.get(key_def["name"], "")
        if len(value) >= 4:
            preview = "••••" + value[-4:]
        elif value:
            preview = "••••"
        else:
            preview = ""

        status.append({
            "name": key_def["name"],
            "label": key_def["label"],
            "is_set": bool(value),
            "preview": preview,
        })

    return status


def save_keys(env_path, new_values):
    # ... unchanged ...
    current = _parse_env_file(env_path)
    for key, value in new_values.items():
        if value:
            current[key] = value

    _write_env_file(env_path, current)
    return current


def get_active_provider(env_path):
    """Returns the currently selected provider name, e.g. 'nvidia'."""
    current = _parse_env_file(env_path)
    return current.get("AI_PROVIDER", DEFAULT_PROVIDER)


def save_active_provider(env_path, provider_value):
    """Persists which provider is active. Raises ValueError for an unknown provider."""
    valid_values = {p["value"] for p in AI_PROVIDERS}
    if provider_value not in valid_values:
        raise ValueError(f"Unknown provider: {provider_value}")

    current = _parse_env_file(env_path)
    current["AI_PROVIDER"] = provider_value
    _write_env_file(env_path, current)
    return provider_value