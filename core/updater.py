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
        version = VERSION_FILE.read_text(encoding="utf-8").strip()

        if not version:
            return "0.0.0"

        return version

    except Exception:
        return "0.0.0"

GITHUB_REPO = "1andresito/Prospectr"

CACHE_FILE = Path.home() / ".prospectr" / "update_cache.json"

CACHE_TTL_SECONDS = 30 * 60
REQUEST_TIMEOUT_SECONDS = 10


def _read_cache():
    """Read cached GitHub release information."""

    try:
        if not CACHE_FILE.exists():
            return None

        data = json.loads(
            CACHE_FILE.read_text(encoding="utf-8")
        )

        checked_at = data.get("checked_at", 0)
        latest_version = data.get("latest_version")

        if not latest_version:
            return None
        if time.time() - checked_at < CACHE_TTL_SECONDS:
            return data

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass

    return None


def _write_cache(latest_tag, release_url=None):
    """Save GitHub release information to the cache."""

    try:
        CACHE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        CACHE_FILE.write_text(
            json.dumps(
                {
                    "checked_at": time.time(),
                    "latest_version": latest_tag,
                    "release_url": release_url,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    except OSError:
        pass


def get_latest_release():
    """
    Get information about the latest published GitHub release.

    Returns:
        dict containing:
            version
            tag_name
            release_url
            name
            published_at

        None if the request fails.
    """

    cached = _read_cache()

    if cached:
        return {
            "version": cached.get("latest_version"),
            "tag_name": cached.get("tag_name"),
            "release_url": cached.get(
                "release_url",
                f"https://github.com/{GITHUB_REPO}/releases/latest",
            ),
            "name": cached.get("name"),
            "published_at": cached.get("published_at"),
            "from_cache": True,
        }

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPO}/releases/latest"
    )

    try:
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

        version = str(tag_name).lstrip("v").strip()

        if not version:
            return None

        release_url = data.get(
            "html_url",
            f"https://github.com/{GITHUB_REPO}/releases/latest",
        )

        release = {
            "version": version,
            "tag_name": tag_name,
            "release_url": release_url,
            "name": data.get("name"),
            "published_at": data.get("published_at"),
            "from_cache": False,
        }

        try:
            CACHE_FILE.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            CACHE_FILE.write_text(
                json.dumps(
                    {
                        "checked_at": time.time(),
                        "latest_version": version,
                        "tag_name": tag_name,
                        "release_url": release_url,
                        "name": data.get("name"),
                        "published_at": data.get("published_at"),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        except OSError:
            pass

        return release

    except requests.exceptions.Timeout:
        return None

    except requests.exceptions.HTTPError:
        return None

    except requests.exceptions.RequestException:
        return None

    except (ValueError, TypeError, KeyError):
        return None

def version_tuple(version):
    """
    Convert a version string into a tuple of integers.
    """

    if not version:
        return (0,)

    version = str(version).strip()
    version = version.lstrip("v")
    version = version.split("-")[0]

    parts = re.findall(r"\d+", version)

    if not parts:
        return (0,)

    return tuple(int(part) for part in parts)

def get_update_status():
    """
    Check whether a newer Prospectr release is available.

    Returns diagnostic information so the frontend can see
    exactly what happened.
    """

    current = get_current_version()
    release = get_latest_release()

    if release is None:
        return {
            "current_version": current,
            "latest_version": None,
            "status": "check_failed",
            "update_available": False,

            "release_url": (
                f"https://github.com/{GITHUB_REPO}/releases/latest"
            ),

            "diagnostic": {
                "current_version": current,
                "github_version": None,
                "github_tag": None,
                "github_release_name": None,
                "github_release_url": None,
                "from_cache": False,
                "message": "Unable to retrieve the latest GitHub release.",
            },
        }

    latest = release["version"]

    current_tuple = version_tuple(current)
    latest_tuple = version_tuple(latest)

    if latest_tuple > current_tuple:

        status = "update_available"

        message = (
            f"Update available: "
            f"{current} → {latest}"
        )

        update_available = True

    elif current_tuple == latest_tuple:

        status = "up_to_date"

        message = (
            f"Prospectr is up to date "
            f"({current})."
        )

        update_available = False

    else:
        status = "unreleased"

        message = (
            f"Local version {current} is newer than "
            f"GitHub release {latest}."
        )

        update_available = False

    return {
        "current_version": current,
        "latest_version": latest,

        "status": status,

        "update_available": update_available,

        "release_url": release["release_url"],

        "diagnostic": {
            "current_version": current,
            "github_version": latest,
            "github_tag": release["tag_name"],
            "github_release_name": release["name"],
            "github_release_url": release["release_url"],
            "github_published_at": release["published_at"],
            "from_cache": release["from_cache"],
            "message": message,
        },
    }