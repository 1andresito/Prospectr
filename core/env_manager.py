# env_manager.py
ENV_KEYS = [
    {"name": "GOOGLE_PLACES_API_KEY", "label": "Google Places API Key", "type": "secret"},
    {"name": "AGENT_API_KEY", "label": "AI API Key", "type": "secret"},
    {"name": "BRAVE_SEARCH_API_KEY", "label": "Research Search API Key", "type": "secret"},
]

AI_PROVIDERS = [
    {"value": "nvidia", "label": "NVIDIA", "prefixes": ("nvapi-",)},
    {"value": "gemini", "label": "Google Gemini", "prefixes": ("AIza",)},
    {"value": "claude", "label": "Anthropic Claude", "prefixes": ("sk-ant-",)},
    {"value": "chatgpt", "label": "OpenAI ChatGPT", "prefixes": ("sk-",)},
]

DEFAULT_PROVIDER = "nvidia"
MIN_GRID_SIZE = 1
MAX_GRID_SIZE = 5
DEFAULT_GRID_SIZE = 3


def _parse_env_file(path):
    values = {}
    if not path.exists():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()

    return values


def _write_env_file(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_key_status(env_path):
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
            "type": "secret",
            "is_set": bool(value),
            "preview": preview,
        })

    provider = get_active_provider(env_path)
    grid_size = get_grid_size(env_path)

    status.append({
        "name": "AI_PROVIDER",
        "label": "AI Provider",
        "type": "select",
        "value": provider,
        "options": [
            {"value": p["value"], "label": p["label"]}
            for p in AI_PROVIDERS
        ],
    })

    status.append({
        "name": "SEARCH_GRID_SIZE",
        "label": "Search Area",
        "type": "range",
        "value": grid_size,
        "min": MIN_GRID_SIZE,
        "max": MAX_GRID_SIZE,
        "description": "Larger areas search more locations and can use more Google Places API requests.",
    })

    return status


def save_keys(env_path, new_values):
    current = _parse_env_file(env_path)
    for key, value in new_values.items():
        if value:
            current[key] = value

    _write_env_file(env_path, current)
    return current


def clear_keys(env_path, names):
    """Remove saved keys entirely so a mistyped key can be taken back out."""
    current = _parse_env_file(env_path)
    removed = [name for name in names if current.pop(name, None) is not None]

    if removed:
        _write_env_file(env_path, current)

    return removed


def get_active_provider(env_path):
    current = _parse_env_file(env_path)
    provider = current.get("AI_PROVIDER", DEFAULT_PROVIDER)
    valid_values = {p["value"] for p in AI_PROVIDERS}
    return provider if provider in valid_values else DEFAULT_PROVIDER


def save_active_provider(env_path, provider_value):
    valid_values = {p["value"] for p in AI_PROVIDERS}
    if provider_value not in valid_values:
        raise ValueError(f"Unknown provider: {provider_value}")

    current = _parse_env_file(env_path)
    current["AI_PROVIDER"] = provider_value
    _write_env_file(env_path, current)
    return provider_value


def get_grid_size(env_path):
    current = _parse_env_file(env_path)
    try:
        value = int(current.get("SEARCH_GRID_SIZE", DEFAULT_GRID_SIZE))
    except (TypeError, ValueError):
        value = DEFAULT_GRID_SIZE
    return max(MIN_GRID_SIZE, min(MAX_GRID_SIZE, value))


def save_grid_size(env_path, value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("Search area must be a whole number.")

    if not MIN_GRID_SIZE <= value <= MAX_GRID_SIZE:
        raise ValueError(
            f"Search area must be between {MIN_GRID_SIZE} and {MAX_GRID_SIZE}."
        )

    current = _parse_env_file(env_path)
    current["SEARCH_GRID_SIZE"] = str(value)
    _write_env_file(env_path, current)
    return value


def validate_provider_key(provider, api_key):
    """
    Reject an obviously mismatched provider/key pair.

    Unknown/new key formats are allowed so provider APIs can evolve without
    forcing a client update. We only reject known prefixes belonging to a
    different provider.
    """
    if not api_key:
        return True, None

    key = api_key.strip()

    for provider_def in AI_PROVIDERS:
        for prefix in provider_def["prefixes"]:
            if key.startswith(prefix):
                if provider == provider_def["value"]:
                    return True, None
                return False, (
                    f"This key looks like a {provider_def['label']} key, "
                    f"but {provider} is selected."
                )

    return True, None
