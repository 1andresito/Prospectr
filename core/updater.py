import sys
from pathlib import Path
import json
import time
import requests
import re

if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    RESOURCE_DIR = Path(__file__).resolve().parent

VERSION_FILE = RESOURCE_DIR / "VERSION.txt"

def get_current_version():
    try:
        return VERSION_FILE.read_text().strip()
    except Exception:
        return "0.0.0"

GITHUB_REPO = "1andresito/Prospectr"
CACHE_FILE = Path.home() / ".prospectr" / "update_cache.json"
CACHE_TTL_SECONDS = 12 * 60 * 60

def _read_cache():
    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("checked_at", 0) < CACHE_TTL_SECONDS:
            return data
    except Exception:
        pass
    return None

def _write_cache(latest_tag):
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "checked_at": time.time(),
            "latest_version": latest_tag,
        }))
    except Exception:
        pass

def get_latest_release_tag():
    cached = _read_cache()
    if cached:
        return cached["latest_version"]

    try:
        resp = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=3,
        )
        resp.raise_for_status()
        latest = resp.json()["tag_name"].lstrip("v")
        _write_cache(latest)
        return latest
    except Exception:
        return None

def version_tuple(v):
    v = v.split("-")[0]
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts) if parts else (0,)

def get_update_status():
    current = get_current_version()
    latest = get_latest_release_tag()

    status = "up_to_date"
    if latest:
        try:
            current_t = version_tuple(current)
            latest_t = version_tuple(latest)
            if latest_t > current_t:
                status = "update_available"
            elif current_t > latest_t:
                status = "unreleased"
        except Exception:
            status = "unknown"

    return {
        "current_version": current,
        "latest_version": latest,
        "status": status,
        "update_available": status == "update_available",
        "release_url": f"https://github.com/{GITHUB_REPO}/releases/latest",
    }