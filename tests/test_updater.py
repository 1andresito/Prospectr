import pytest

import updater


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1.2.3", (1, 2, 3)),
        ("v1.2.3", (1, 2, 3)),
        ("V2.4.0", (2, 4, 0)),
        ("  2.4.0  ", (2, 4, 0)),
        ("2.4.0-beta.1", (2, 4, 0)),
        ("2.4", (2, 4)),
        ("", (0,)),
        (None, (0,)),
        ("not-a-version", (0,)),
    ],
)
def test_version_tuple(raw, expected):
    assert updater.version_tuple(raw) == expected


def test_version_tuple_orders_numerically_not_lexically():
    assert updater.version_tuple("2.10.0") > updater.version_tuple("2.9.0")


def _release(version):
    return {
        "version": version,
        "tag_name": f"v{version}",
        "name": f"Prospectr {version}",
        "release_url": "https://example.invalid/release",
        "published_at": "2026-01-01T00:00:00Z",
    }


@pytest.fixture
def fake_versions(monkeypatch):
    def apply(current, latest):
        monkeypatch.setattr(updater, "get_current_version", lambda: current)
        monkeypatch.setattr(
            updater,
            "get_latest_release",
            lambda: _release(latest) if latest is not None else None,
        )

    return apply


def test_update_available(fake_versions):
    fake_versions("2.4.0", "2.5.0")
    status = updater.get_update_status()

    assert status["status"] == "update_available"
    assert status["update_available"] is True
    assert status["latest_version"] == "2.5.0"


def test_up_to_date(fake_versions):
    fake_versions("2.4.0", "2.4.0")
    status = updater.get_update_status()

    assert status["status"] == "up_to_date"
    assert status["update_available"] is False


def test_local_build_ahead_of_release(fake_versions):
    fake_versions("2.5.0", "2.4.0")
    status = updater.get_update_status()

    assert status["status"] == "unreleased"
    assert status["update_available"] is False


def test_check_failure_is_not_reported_as_an_update(fake_versions):
    fake_versions("2.4.0", None)
    status = updater.get_update_status()

    assert status["status"] == "check_failed"
    assert status["update_available"] is False
    assert status["latest_version"] is None


def test_padded_release_is_not_treated_as_newer(fake_versions):
    """2.4 and 2.4.0 differ as strings but must not trigger a false update."""
    fake_versions("2.4.0", "2.4")
    status = updater.get_update_status()

    assert status["update_available"] is False


ALL_ASSETS = [
    {"name": "Prospectr-Windows.zip", "browser_download_url": "https://example.invalid/win"},
    {"name": "Prospectr-Mac.zip", "browser_download_url": "https://example.invalid/mac"},
    {"name": "Prospectr-x86_64.AppImage", "browser_download_url": "https://example.invalid/linux"},
]


@pytest.mark.parametrize(
    "platform, expected_url",
    [
        ("win32", "https://example.invalid/win"),
        ("darwin", "https://example.invalid/mac"),
        ("linux", "https://example.invalid/linux"),
        ("linux2", "https://example.invalid/linux"),
    ],
)
def test_pick_asset_for_platform(platform, expected_url):
    asset = updater.pick_asset_for_platform(ALL_ASSETS, platform=platform)
    assert asset is not None
    assert asset["browser_download_url"] == expected_url


def test_pick_asset_for_platform_unknown_platform():
    assert updater.pick_asset_for_platform(ALL_ASSETS, platform="sunos") is None


def test_pick_asset_for_platform_missing_asset():
    assert updater.pick_asset_for_platform([], platform="win32") is None
