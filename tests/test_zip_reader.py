"""Tests for zipsearch.zip_reader."""

import io

from zipsearch.models import Entry
from zipsearch.zip_reader import is_zip, iter_zip_entries


def test_empty_zip_has_no_entries(make_zip):
    """A ZIP with no members yields nothing."""
    path = make_zip({})
    assert list(iter_zip_entries(path)) == []


def test_flat_zip_lists_files(make_zip):
    """Each file shows up with its name and uncompressed size."""
    path = make_zip({"a.txt": "hello", "b.txt": "hi"})
    entries = list(iter_zip_entries(path))
    assert [e.inner_path for e in entries] == ["a.txt", "b.txt"]
    assert [e.size for e in entries] == [5, 2]
    assert all(isinstance(e, Entry) for e in entries)
    assert all(e.container_path == str(path) for e in entries)
    assert not any(e.is_dir or e.is_zip or e.encrypted for e in entries)


def test_zip_with_folders_flags_directories(make_zip):
    """Folder entries are flagged is_dir and files inside are not."""
    path = make_zip({"docs/": "", "docs/readme.txt": "x"})
    by_name = {e.inner_path: e for e in iter_zip_entries(path)}
    assert by_name["docs/"].is_dir is True
    assert by_name["docs/readme.txt"].is_dir is False


def test_inner_zip_is_hinted(make_nested_zip):
    """A .zip member is marked is_zip but is not opened here."""
    path = make_nested_zip()
    entries = list(iter_zip_entries(path))
    assert [(e.inner_path, e.is_zip) for e in entries] == [("inner1.zip", True)]


def test_encrypted_member_is_flagged(make_encrypted_zip):
    """Password-protected members are listed with encrypted=True."""
    entries = list(iter_zip_entries(make_encrypted_zip()))
    assert [(e.inner_path, e.encrypted) for e in entries] == [("secret.txt", True)]


def test_file_object_without_name(make_zip):
    """An open file object works; container_path falls back to ''."""
    data = make_zip({"a.txt": "x"}).read_bytes()
    entries = list(iter_zip_entries(io.BytesIO(data)))
    assert entries[0].container_path == ""
    assert entries[0].inner_path == "a.txt"


def test_is_zip_true_for_real_zip(make_zip):
    """A real ZIP with a .zip name passes."""
    assert is_zip(str(make_zip({"a.txt": "x"})))


def test_is_zip_extension_is_case_insensitive(make_zip):
    """.ZIP in capitals still counts."""
    assert is_zip(str(make_zip({"a.txt": "x"}, name="UPPER.ZIP")))


def test_is_zip_rejects_wrong_extension(make_zip):
    """A real ZIP renamed to .txt is not accepted."""
    assert not is_zip(str(make_zip({"a.txt": "x"}, name="data.txt")))


def test_is_zip_rejects_fake_and_missing(make_corrupt_zip, tmp_path):
    """Bad bytes and missing files return False instead of raising."""
    assert not is_zip(str(make_corrupt_zip()))
    assert not is_zip(str(tmp_path / "nope.zip"))
