import os

import pytest

from src.storage import available_bytes, directory_usage, storage_locations


def test_storage_counts_hardlinked_bytes_once_and_bounded_scan_reports_partial(tmp_path):
    (tmp_path / "original").write_bytes(b"12345")
    os.link(tmp_path / "original", tmp_path / "hardlink")
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "other").write_bytes(b"678")
    assert directory_usage(tmp_path).bytes == 8
    assert directory_usage(tmp_path).files == 2
    limited = directory_usage(tmp_path, max_files=1)
    assert limited.partial and limited.files == 1
    assert available_bytes(tmp_path / "does-not-exist" / "yet") > 0


def test_storage_never_traverses_a_directory_symlink_even_when_it_is_the_root(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "file").write_bytes(b"secret")
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires a Windows privilege")
    assert directory_usage(link).bytes == 0
    assert directory_usage(link).partial
    assert directory_usage(tmp_path).bytes == 6


def test_storage_locations_follow_custom_exports_settings_and_history(tmp_path):
    rows = dict(storage_locations(tmp_path / "exports", tmp_path / "config" / "settings.json",
                                  tmp_path / "private" / "history.sqlite3"))
    assert rows["storage_exports"] == tmp_path / "exports"
    assert rows["storage_settings"] == tmp_path / "config" / "settings.json"
    assert rows["storage_recovery"] == tmp_path / "private" / "unsaved_session.json"

