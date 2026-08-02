from pathlib import Path

CURRENT_DATA_VERSION = 2

VERSION_FILE_NAME = ".data_version"

OBSOLETE_RELATIVE_FILES = (
    "update_cache.json",
    ".prospectr/update_cache.json",
    ".prospectr/update-cache.json",
)


def _read_version(config_dir: Path) -> int:
    version_file = config_dir / VERSION_FILE_NAME
    try:
        return int(version_file.read_text().strip())
    except (OSError, ValueError):
        return 0


def _write_version(config_dir: Path, version: int) -> None:
    try:
        (config_dir / VERSION_FILE_NAME).write_text(str(version))
    except OSError:
        pass


def _migrate_to_2(config_dir: Path) -> list[str]:
    """
    Cleanup for installs <= 2.3.3: remove obsolete update-cache files
    left behind by the old updater.

    This is intentionally allow-list based: it will never recursively
    delete arbitrary user files from the configuration directory.
    """
    removed = []

    candidates = [config_dir / rel for rel in OBSOLETE_RELATIVE_FILES]
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

MIGRATIONS = {
    2: _migrate_to_2,
}


def run_migrations(config_dir: Path) -> list[str]:
    removed = []
    current = _read_version(config_dir)

    for version in sorted(MIGRATIONS):
        if version > current:
            removed.extend(MIGRATIONS[version](config_dir))

    if current < CURRENT_DATA_VERSION:
        _write_version(config_dir, CURRENT_DATA_VERSION)

    return removed