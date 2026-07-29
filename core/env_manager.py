ENV_KEYS = [
    {"name": "GOOGLE_PLACES_API_KEY", "label": "Google Places API Key"},
    {"name": "NVIDIA_API_KEY", "label": "Nvidia API Key"}
]


def _parse_env_file(path):
    """
    Reads a .env file into a plain dictionary, e.g.
    {'GOOGLE_PLACES_API_KEY': 'abc123'}.
    Returns an empty dict if the file doesn't exist yet — this is
    what lets 'save' work whether or not .env has been created.
    """
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
    """Writes a dictionary back out as a .env file, one KEY=value per line."""
    lines = [f"{key}={value}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n")


def get_key_status(env_path):
    """
    Returns which known keys are currently set — WITHOUT exposing the
    real values. Only a boolean and a masked preview (last 4 chars)
    are returned, so the frontend can display status without ever
    holding the actual secret.
    """
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
    """
    Updates (or creates) the .env file with new key/value pairs,
    preserving any existing keys not included in this particular save.
    Empty/blank submitted values are ignored, so leaving a field blank
    in the UI doesn't accidentally erase an already-saved key.
    """
    current = _parse_env_file(env_path)
    for key, value in new_values.items():
        if value:
            current[key] = value

    _write_env_file(env_path, current)
    return current