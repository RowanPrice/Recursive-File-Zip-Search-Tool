"""Verify the scaffold keeps the old folder walk and CLI behaviour intact."""

import io
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import GeneratorType
from zipfile import BadZipFile, ZipFile

import pytest

from zipsearch.models import Entry, SearchHit
from zipsearch.walker import walk, walk_directories

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_walk_matches_os_walk(tmp_path, make_zip):
    """Keep the same files and traversal order as the original os.walk loop."""
    (tmp_path / "empty").mkdir()
    (tmp_path / "sub").mkdir()
    (tmp_path / "first.txt").write_text("hello")
    (tmp_path / "sub" / "second.txt").write_text("world")
    make_zip({"inside.txt": "not traversed yet"})
    expected = [os.path.join(folder, name)
                for folder, _, files in os.walk(tmp_path) for name in files]
    result = walk(tmp_path)
    assert isinstance(result, GeneratorType)
    assert list(result) == expected
    assert list(walk_directories(tmp_path)) == list(os.walk(tmp_path))


def test_empty_and_missing_roots(tmp_path):
    """An empty or missing root yields no files, as os.walk does."""
    assert list(walk(tmp_path)) == []
    assert list(walk(tmp_path / "missing")) == []
    assert list(walk_directories(tmp_path)) == [(str(tmp_path), [], [])]


def test_relative_root(tmp_path, monkeypatch):
    """Do not silently convert a caller's relative paths into absolute
    paths."""
    monkeypatch.chdir(tmp_path)
    Path("folder").mkdir()
    Path("folder/file.txt").write_text("hello")
    assert list(walk("folder")) == [os.path.join("folder", "file.txt")]


def test_directory_symlinks_not_followed(tmp_path):
    """Keep os.walk's default refusal to recurse through directory symlinks."""
    real = tmp_path / "real"
    real.mkdir()
    (real / "file.txt").write_text("hello")
    try:
        (tmp_path / "link").symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks are unavailable on this system")
    assert list(walk(tmp_path)) == [str(real / "file.txt")]


def test_cli_preserves_listing(tmp_path):
    """Compare the CLI output with the original algorithm, including
    empties."""
    (tmp_path / "empty").mkdir()
    (tmp_path / "file.txt").write_text("hello")
    expected = "Walking: {}\n".format(tmp_path)
    for folder, dirs, files in os.walk(tmp_path):
        expected += "\nDirectory: {}\n".format(folder)
        expected += "".join("  [DIR] {}\n".format(name) for name in dirs)
        expected += "".join("  [FILE] {}\n".format(name) for name in files)
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout == expected
    assert result.stderr == ""


def test_cli_invalid_root(tmp_path):
    """Keep the original error text, output stream and exit status."""
    missing = tmp_path / "missing"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), str(missing)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Error: '{}' is not a valid directory\n".format(
        missing
    )


def test_shared_records():
    """Shared entries are immutable; line details are optional on name hits."""
    entry = Entry("outer.zip", "folder/file.txt", 6, False)
    assert not entry.is_dir
    assert not entry.encrypted
    assert SearchHit(entry).line_number is None
    assert SearchHit(entry, 1, "hello").line_text == "hello"
    with pytest.raises(FrozenInstanceError):
        entry.size = 7


def test_zip_helpers(make_zip, make_nested_zip):
    """Plain, empty and three-level archives can be read with only zipfile."""
    with ZipFile(make_zip({}, name="empty.zip")) as archive:
        assert archive.namelist() == []
    with ZipFile(make_zip({"dir/": b"", "dir/file.txt": "hello"})) as archive:
        assert archive.getinfo("dir/").is_dir()
        assert archive.read("dir/file.txt") == b"hello"
    with ZipFile(make_nested_zip(levels=3)) as outer:
        with ZipFile(io.BytesIO(outer.read("inner1.zip"))) as middle:
            with ZipFile(io.BytesIO(middle.read("inner2.zip"))) as inner:
                assert inner.read("file.txt") == b"hello\n"


@pytest.mark.parametrize("truncated", [False, True])
def test_corrupt_helper(make_corrupt_zip, truncated):
    """Both non-ZIP and truncated ZIP fixtures must really be unreadable."""
    with pytest.raises(BadZipFile):
        ZipFile(make_corrupt_zip(truncated=truncated))


def test_encrypted_helper(make_password_protected_zip):
    """The fixture requires its password and decrypts to the expected bytes."""
    with ZipFile(make_password_protected_zip()) as archive:
        assert archive.getinfo("secret.txt").flag_bits & 1
        with pytest.raises(RuntimeError, match="password"):
            archive.read("secret.txt")
        contents = archive.read("secret.txt", pwd=b"scaffold-password")
        assert contents == b"secret\n"
