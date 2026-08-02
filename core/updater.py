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
    """Return the version of the currently running application."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"

GITHUB_REPO = "1andresito/Prospectr"

CACHE_FILE = Path.home() / ".prospectr" / "update_cache.json"
CACHE_TTL_SECONDS = 30 * 60
REQUEST_TIMEOUT_SECONDS = 10



def _read_cache():
    """Read the cached GitHub release information."""
    try:
        if not CACHE_FILE.exists():
            return None

        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

        checked_at = data.get("checked_at", 0)
        latest_version = data.get("latest_version")

        if not latest_version:
            return None
        if time.time() - checked_at < CACHE_TTL_SECONDS:
            return data

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass

    return None


def _write_cache(latest_tag):
    """Save the latest GitHub version to the local cache."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        CACHE_FILE.write_text(
            json.dumps(
                {
                    "checked_at": time.time(),
                    "latest_version": latest_tag,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError:
        pass

def get_latest_release_tag():
    """
    Return the latest GitHub release version.

    Returns:
        str: Latest release version.
        None: If GitHub cannot be reached or the response is invalid.
    """
    cached = _read_cache()

    if cached:
        return cached["latest_version"]

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Prospectr-Updater",
            },
        )

        response.raise_for_status()

        data = response.json()

        tag_name = data.get("tag_name")

        if not tag_name:
            return None
        latest = str(tag_name).lstrip("v").strip()

        if not latest:
            return None

        _write_cache(latest)

        return latest

    except requests.exceptions.Timeout:
        return None

    except requests.exceptions.RequestException:
        return None

    except (ValueError, KeyError, TypeError):
        return None

def version_tuple(version):
    """
    Convert a version string into a tuple of integers.

    Examples:
        "2.3.1"       -> (2, 3, 1)
        "v2.3.1"      -> (2, 3, 1)
        "2.3.1-beta"  -> (2, 3, 1)
    """

    if not version:
        return (0,)

    version = str(version).strip()

    version = version.split("-")[0]

    parts = re.findall(r"\d+", version)

    return tuple(int(part) for part in parts) if parts else (0,)

def get_update_status():
    """
    Check whether a newer Prospectr release is available.

    Returns a dictionary containing:

        current_version
        latest_version
        status
        update_available
        release_url
    """

    current = get_current_version()
    latest = get_latest_release_tag()

    if latest is None:
        return {
            "current_version": current,
            "latest_version": None,
            "status": "check_failed",
            "update_available": False,
            "release_url": f"https://github.com/{GITHUB_REPO}/releases/latest",
        }

    try:
        current_tuple = version_tuple(current)
        latest_tuple = version_tuple(latest)

        if latest_tuple > current_tuple:
            status = "update_available"

        elif current_tuple > latest_tuple:
            status = "unreleased"

        else:
            status = "up_to_date"

    except (ValueError, TypeError):
        status = "unknown"

    return {
        "current_version": current,
        "latest_version": latest,
        "status": status,
        "update_available": status == "update_available",
        "release_url": f"https://github.com/{GITHUB_REPO}/releases/latest",
    }