"""
Downloads a newer Prospectr release and swaps it in for the running
executable.

This only works in a packaged (PyInstaller) build — there is no running
executable to replace when developing with `python core/app.py`. The
running process can't overwrite its own file while it's executing, so
the actual replace-and-relaunch step is delegated to a short-lived helper
script (batch on Windows, shell on Mac/Linux) that waits for this process
to exit, moves the new file into place, relaunches it, and deletes itself.
"""

import os
import stat
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import requests
from platformdirs import user_config_dir

REQUEST_TIMEOUT_SECONDS = 30
UPDATES_DIR = Path(user_config_dir("Prospectr", appauthor=False)) / "updates"

_state_lock = threading.Lock()
_state = {"stage": "idle", "percent": 0, "message": ""}


def _set_state(stage, percent=0, message=""):
    with _state_lock:
        _state["stage"] = stage
        _state["percent"] = percent
        _state["message"] = message


def get_status():
    with _state_lock:
        return dict(_state)


def is_supported():
    """Self-update only makes sense against a packaged executable."""
    return bool(getattr(sys, "frozen", False))


def get_running_executable_path():
    """
    Return the path to the executable file that should be replaced, or
    None if self-update isn't supported in the current run mode.
    """
    if not is_supported():
        return None

    if sys.platform.startswith("linux"):
        appimage = os.environ.get("APPIMAGE")
        if appimage:
            return Path(appimage)

    return Path(sys.executable)


def _download(url, dest_path):
    _set_state("downloading", 0, "Downloading update…")

    response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    total = int(response.headers.get("Content-Length", 0) or 0)
    downloaded = 0

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=262144):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                percent = min(99, int(downloaded * 100 / total))
                _set_state("downloading", percent, "Downloading update…")


def _prepare(downloaded_path, asset_name):
    _set_state("preparing", 100, "Preparing update…")

    if asset_name.endswith(".zip"):
        with zipfile.ZipFile(downloaded_path) as zf:
            names = zf.namelist()
            if len(names) != 1:
                raise RuntimeError(f"Unexpected update archive contents: {names}")
            extracted_name = names[0]
            zf.extract(extracted_name, UPDATES_DIR)
        extracted_path = UPDATES_DIR / extracted_name
        downloaded_path.unlink(missing_ok=True)
        new_path = extracted_path
    else:
        new_path = downloaded_path

    if not sys.platform.startswith("win"):
        new_path.chmod(new_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    if sys.platform == "darwin":
        # Downloaded files get Gatekeeper's quarantine flag, which can
        # silently block the relaunch. Best-effort strip it; if this fails
        # (e.g. stricter Gatekeeper policy) the user may need to approve
        # the relaunch manually once, same as today's manual-download flow.
        subprocess.run(
            ["xattr", "-d", "com.apple.quarantine", str(new_path)],
            check=False,
            capture_output=True,
        )

    return new_path


def _write_windows_helper(pid, new_path, old_path):
    script_path = UPDATES_DIR / "apply_update.bat"
    script_path.write_text(
        "\n".join(
            [
                "@echo off",
                ":wait",
                f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL',
                "if not errorlevel 1 (",
                "    timeout /t 1 /nobreak >NUL",
                "    goto wait",
                ")",
                f'move /Y "{new_path}" "{old_path}"',
                f'start "" "{old_path}"',
                'del "%~f0"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def _write_unix_helper(pid, new_path, old_path):
    script_path = UPDATES_DIR / "apply_update.sh"
    script_path.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                f'while kill -0 {pid} 2>/dev/null; do sleep 0.5; done',
                f'mv -f "{new_path}" "{old_path}"',
                f'chmod +x "{old_path}"',
                f'nohup "{old_path}" >/dev/null 2>&1 &',
                'rm -- "$0"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script_path


def _launch_helper_and_exit(new_path, old_path):
    pid = os.getpid()

    if sys.platform.startswith("win"):
        script_path = _write_windows_helper(pid, new_path, old_path)
        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    else:
        script_path = _write_unix_helper(pid, new_path, old_path)
        subprocess.Popen(
            ["/bin/sh", str(script_path)],
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    _set_state("restarting", 100, "Restarting Prospectr…")

    def _exit_soon():
        os._exit(0)

    threading.Timer(1.0, _exit_soon).start()


def run_update(asset):
    """
    Download `asset` (a dict with "name"/"browser_download_url"), swap it
    in for the running executable, and relaunch. Runs entirely in the
    calling thread; the caller should invoke this from a background thread
    since it blocks until the process exits.
    """
    old_path = get_running_executable_path()
    if old_path is None:
        _set_state("error", 0, "Self-update is not available in this build.")
        return

    try:
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)

        asset_name = asset["name"]
        downloaded_path = UPDATES_DIR / asset_name
        _download(asset["browser_download_url"], downloaded_path)

        new_path = _prepare(downloaded_path, asset_name)

        _launch_helper_and_exit(new_path, old_path)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        _set_state("error", 0, f"Update failed: {exc}")
