from pathlib import Path
import shutil

CURRENT_DATA_VERSION = 2

OBSOLETE_RELATIVE_FILES = (
    "update_cache.json",
    ".prospectr/update_cache.json",
    ".prospectr/update-cache.json",
)


def run_migrations(config_dir: Path):
    """
    Remove known obsolete Prospectr files left by older versions.

    This is intentionally allow-list based: it will never recursively delete
    arbitrary user files from the configuration directory.
    """
    removed = []

    candidates = []
    for relative in OBSOLETE_RELATIVE_FILES:
        candidates.append(config_dir / relative)

    candidates.append(Path.home() / ".prospectr" / "update_cache.json")

    for path in candidates:
        try:
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        except OSError:
            pass

    legacy_dir = Path.home() / ".prospectr"
    try:
        if legacy_dir.is_dir() and not any(legacy_dir.iterdir()):
            legacy_dir.rmdir()
            removed.append(str(legacy_dir))
    except OSError:
        pass

    return removed
