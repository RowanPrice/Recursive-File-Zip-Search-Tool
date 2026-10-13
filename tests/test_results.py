"""Check result metadata without reading file contents."""

import os
from datetime import datetime, timezone

import pytest

from zipsearch.results import file_entry


def test_file_metadata(tmp_path):
    """Get the base file's byte size and an explicit UTC timestamp."""
    path = tmp_path / "report.txt"
    path.write_bytes(b"hello")
    modified = datetime(2020, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
    os.utime(path, (modified.timestamp(), modified.timestamp()))
    entry = file_entry(path)
    assert entry.container_path == str(path)
    assert entry.inner_path == ""
    assert entry.size == 5
    assert not entry.is_zip
    assert not entry.is_dir
    assert entry.last_modified == "2020-02-03T04:05:06+00:00"


def test_relative_metadata(tmp_path, monkeypatch):
    """Do not resolve the caller's relative paths or follow a directory walk."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "file.txt"
    path.write_bytes(b"")
    assert file_entry("./file.txt").container_path == "file.txt"
    assert file_entry("file.txt").size == 0


def test_missing_file_metadata_raises(tmp_path):
    """Never return an invented size or timestamp for a missing file."""
    with pytest.raises(OSError):
        file_entry(tmp_path / "missing.txt")


def test_directory_is_flagged(tmp_path):
    """Metadata can mark a directory so the results builder can ignore it."""
    assert file_entry(tmp_path).is_dir


def test_archive_file_is_only_hinted(tmp_path):
    """A .ZIP extension is a hint, not a claim its contents are valid."""
    path = tmp_path / "archive.ZIP"
    path.write_bytes(b"not a zip")
    assert file_entry(path).is_zip


def test_plain_result_has_all_categories(tmp_path):
    """Two categories still give one result and one copy of the metadata."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.results import build_results

    path = tmp_path / "report.txt"
    path.write_bytes(b"hello")
    entry = file_entry(path)
    matcher = CategoryMatcher({
        "documents": {"extensions": [".txt"]},
        "reports": {"patterns": ["report*"]},
    })
    assert build_results([entry], matcher) == [{
        "category": ["documents", "reports"],
        "filename": "report.txt",
        "folder_location": str(tmp_path),
        "zipfile": "",
        "filesizebytes": 5,
        "last_modified": entry.last_modified,
    }]


def test_zip_result_uses_internal_folder(tmp_path):
    """Keep archive location separate from the folder inside the archive."""
    from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

    from zipsearch.categories import CategoryMatcher
    from zipsearch.results import build_results
    from zipsearch.zip_reader import iter_zip_entries

    path = tmp_path / "archive.zip"
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        info = ZipInfo("docs/reports/a.txt", (2020, 2, 3, 4, 5, 6))
        archive.writestr(info, b"a" * 1000, compress_type=ZIP_DEFLATED)
    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    assert build_results(iter_zip_entries(path), matcher) == [{
        "category": ["text"],
        "filename": "a.txt",
        "folder_location": "docs/reports",
        "zipfile": str(path),
        "filesizebytes": 1000,
        "last_modified": "2020-02-03T04:05:06",
    }]


def test_results_skip_unmatched_and_directories():
    """Results contain matching files only and accept a generator."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.models import Entry
    from zipsearch.results import build_results

    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    entries = (
        entry for entry in [
            Entry("docs/folder.txt", "", 0, False, is_dir=True),
            Entry("photo.jpg", "", 2, False),
            Entry("archive.zip", "docs/", 0, False, is_dir=True),
        ]
    )
    assert build_results(entries, matcher) == []


def test_current_folder_and_zip_root():
    """A parent of '.' means the current folder or the root of the ZIP."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.models import Entry
    from zipsearch.results import build_results

    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    entries = [
        Entry("a.txt", "", 0, False),
        Entry("archive.zip", "b.txt", 0, False),
    ]
    results = build_results(entries, matcher)
    assert [result["folder_location"] for result in results] == [".", "."]
    assert [result["zipfile"] for result in results] == ["", "archive.zip"]
    assert all(result["last_modified"] is None for result in results)


def test_result_paths_and_order():
    """Keep relative paths and input order; normalize ZIP separators only."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.models import Entry
    from zipsearch.results import build_results

    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    results = build_results([
        Entry("relative/archive.zip", "docs\\b.txt", 2, False),
        Entry("relative/a.txt", "", 1, False),
    ], matcher)
    assert [r["filename"] for r in results] == ["b.txt", "a.txt"]
    assert [r["folder_location"] for r in results] == ["docs", "relative"]
    assert results[0]["zipfile"] == "relative/archive.zip"


def test_encrypted_zip_results_need_no_password(make_encrypted_zip):
    """Metadata for password-protected members does not read their contents."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.results import build_results
    from zipsearch.zip_reader import iter_zip_entries

    path = make_encrypted_zip()
    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    results = build_results(iter_zip_entries(path), matcher)
    assert len(results) == 1
    assert results[0]["filename"] == "secret.txt"
    assert results[0]["zipfile"] == str(path)


def test_empty_results():
    """No source entries means an empty array, not a placeholder record."""
    from zipsearch.categories import CategoryMatcher
    from zipsearch.results import build_results

    assert build_results([], CategoryMatcher({})) == []
