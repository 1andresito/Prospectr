import sys
from pathlib import Path
import requests
import re

PLATFORM_ASSET_NAMES = {
    "win32": "Prospectr-Windows.zip",
    "darwin": "Prospectr-Mac.zip",
    "linux": "Prospectr-x86_64.AppImage",
}

if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    RESOURCE_DIR = Path(__file__).resolve().parent

VERSION_FILE = RESOURCE_DIR / "VERSION.txt"

GITHUB_REPO = "1andresito/Prospectr"
REQUEST_TIMEOUT_SECONDS = 10


def get_current_version():
    """Return the version of the currently running application."""
    try:
        version = VERSION_FILE.read_text(encoding="utf-8").strip()
        return version if version else "0.0.0"
    except Exception:
        return "0.0.0"


def get_latest_release():
    """
    Get the latest published GitHub release.

    A fresh GitHub request is made every time this function is called.
    There is intentionally no local cache because Prospectr checks for
    updates once when the app starts.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

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

        version = str(tag_name).strip()
        if version.lower().startswith("v"):
            version = version[1:].strip()

        if not version:
            return None

        return {
            "version": version,
            "tag_name": tag_name,
            "name": data.get("name"),
            "release_url": data.get(
                "html_url",
                f"https://github.com/{GITHUB_REPO}/releases/latest",
            ),
            "published_at": data.get("published_at"),
            "assets": [
                {
                    "name": asset.get("name"),
                    "browser_download_url": asset.get("browser_download_url"),
                }
                for asset in data.get("assets", [])
                if asset.get("name") and asset.get("browser_download_url")
            ],
        }

    except requests.exceptions.Timeout:
        return None
    except requests.exceptions.HTTPError:
        return None
    except requests.exceptions.RequestException:
        return None
    except (ValueError, TypeError, KeyError):
        return None


def pick_asset_for_platform(assets, platform=None):
    """
    Pick the release asset matching the current (or given) platform.

    Returns the asset dict (with "name" and "browser_download_url"), or
    None if no matching asset is published for this platform.
    """
    platform = platform if platform is not None else sys.platform

    asset_name = None
    for prefix, name in PLATFORM_ASSET_NAMES.items():
        if platform.startswith(prefix):
            asset_name = name
            break

    if asset_name is None:
        return None

    for asset in assets or []:
        if asset.get("name") == asset_name:
            return asset

    return None


def version_tuple(version):
    """Convert a version string into a tuple of integers."""
    if not version:
        return (0,)

    version = str(version).strip()
    if version.lower().startswith("v"):
        version = version[1:]

    version = version.split("-")[0]
    parts = re.findall(r"\d+", version)

    return tuple(int(part) for part in parts) if parts else (0,)


def get_update_status():
    """
    Check GitHub for an available Prospectr update.

    This performs a fresh check every time it is called.
    """
    current = get_current_version()
    release = get_latest_release()

    if release is None:
        return {
            "current_version": current,
            "latest_version": None,
            "status": "check_failed",
            "update_available": False,
            "release_url": f"https://github.com/{GITHUB_REPO}/releases/latest",
            "diagnostic": {
                "current_version": current,
                "github_version": None,
                "github_tag": None,
                "github_release_name": None,
                "github_release_url": None,
                "github_published_at": None,
                "message": "Unable to retrieve the latest GitHub release.",
            },
        }

    latest = release["version"]
    current_tuple = version_tuple(current)
    latest_tuple = version_tuple(latest)

    if latest_tuple > current_tuple:
        status = "update_available"
        update_available = True
        message = f"Update available: {current} → {latest}"
    elif latest_tuple == current_tuple:
        status = "up_to_date"
        update_available = False
        message = f"Prospectr is up to date ({current})."
    else:
        status = "unreleased"
        update_available = False
        message = (
            f"Local version {current} is newer than "
            f"GitHub release {latest}."
        )

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
            "message": message,
        },
    }