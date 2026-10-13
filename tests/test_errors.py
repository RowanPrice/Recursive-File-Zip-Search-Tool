"""Bad zips, denied permissions and odd names are logged, skipped, survived."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from zipfile import BadZipFile

import pytest

from zipsearch.categories import CategoryMatcher
from zipsearch.csv_export import write_results_csv
from zipsearch.logging_setup import setup_logging
from zipsearch.results import build_results, safe_file_entry
from zipsearch.walker import root_problem, walk
from zipsearch.zip_reader import iter_zip_entries, iter_zip_entries_safe

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def logs(tmp_path):
    """Send zipsearch logs to a StringIO console and a real file, then undo."""
    logger = logging.getLogger("zipsearch")
    old_handlers = logger.handlers[:]
    old_level, old_propagate = logger.level, logger.propagate
    logger.handlers = []
    import io
    console = io.StringIO()
    path = tmp_path / "run.log"
    setup_logging(path, console=console)
    yield console, path
    for handler in logger.handlers[:]:
        handler.close()
    logger.handlers = old_handlers
    logger.setLevel(old_level)
    logger.propagate = old_propagate


def running_as_root():
    """chmod permission tests are meaningless when the user is root."""
    return hasattr(os, "geteuid") and os.geteuid() == 0


# --- Corrupt and password-protected ZIPs ---------------------------------


@pytest.mark.parametrize("truncated", [False, True])
def test_safe_iter_skips_corrupt_zip(logs, make_corrupt_zip, truncated):
    """A corrupt ZIP yields nothing, logs one clear ERROR, and raises nothing."""
    path = make_corrupt_zip(truncated=truncated)
    assert list(iter_zip_entries_safe(path)) == []
    text = logs[1].read_text()
    assert "ERROR" in text
    assert "Skipping ZIP '{}'".format(path) in text
    assert "BadZipFile" in text


def test_plain_iter_still_raises_on_corrupt_zip(make_corrupt_zip):
    """The original raising behaviour of iter_zip_entries is unchanged."""
    with pytest.raises(BadZipFile):
        list(iter_zip_entries(make_corrupt_zip()))


def test_safe_iter_lists_encrypted_zip_with_warning(logs, make_encrypted_zip):
    """Password-protected members are listed, flagged and logged, never read."""
    path = make_encrypted_zip()
    entries = list(iter_zip_entries_safe(path))
    assert [entry.inner_path for entry in entries] == ["secret.txt"]
    assert entries[0].encrypted
    text = logs[1].read_text()
    assert "WARNING" in text
    assert "Password-protected member 'secret.txt'" in text
    assert "contents not read" in text


def test_safe_iter_skips_missing_zip(logs, tmp_path):
    """A ZIP path that does not exist is logged and skipped, not raised."""
    missing = tmp_path / "missing.zip"
    assert list(iter_zip_entries_safe(missing)) == []
    assert "Skipping ZIP '{}'".format(missing) in logs[1].read_text()


# --- Permission-denied folders and files ----------------------------------


@pytest.mark.skipif(running_as_root(), reason="root ignores permission bits")
def test_safe_file_entry_skips_unreadable_file(logs, tmp_path):
    """A file inside a denied folder returns None and logs the exact reason."""
    folder = tmp_path / "private"
    folder.mkdir()
    target = folder / "secret.txt"
    target.write_text("secret")
    folder.chmod(0)
    try:
        assert safe_file_entry(target) is None
    finally:
        folder.chmod(0o755)  # let pytest clean the tmp folder afterwards
    text = logs[1].read_text()
    assert "Skipping file '{}'".format(target) in text
    assert "PermissionError" in text


def test_safe_file_entry_skips_missing_file(logs, tmp_path):
    """A vanished file is skipped with a logged reason instead of raising."""
    missing = tmp_path / "missing.txt"
    assert safe_file_entry(missing) is None
    assert "Skipping file '{}'".format(missing) in logs[1].read_text()


def test_safe_file_entry_reads_good_file(tmp_path):
    """A normal file is returned exactly as file_entry would return it."""
    path = tmp_path / "ok.txt"
    path.write_text("hello")
    entry = safe_file_entry(path)
    assert entry is not None
    assert entry.container_path == str(path)
    assert entry.size == 5


# --- Root folder problems ---------------------------------------------------


def test_root_problem_missing(tmp_path):
    assert root_problem(tmp_path / "missing") == "the folder does not exist"


def test_root_problem_file(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("hello")
    assert root_problem(path) == "it is a file, not a folder"


@pytest.mark.skipif(running_as_root(), reason="root ignores permission bits")
def test_root_problem_unreadable(tmp_path):
    folder = tmp_path / "private"
    folder.mkdir()
    folder.chmod(0)
    try:
        assert root_problem(folder) == "permission denied"
    finally:
        folder.chmod(0o755)


def test_root_problem_ok(tmp_path):
    assert root_problem(tmp_path) is None


def test_cli_unreadable_root_fails_clearly(tmp_path):
    """Exit 1, a helpful message, and no traceback for a denied root."""
    if running_as_root():
        pytest.skip("root ignores permission bits")
    folder = tmp_path / "private"
    folder.mkdir()
    folder.chmod(0)
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "main.py"), str(folder),
             "--log-file", str(tmp_path / "run.log")],
            capture_output=True, text=True,
        )
    finally:
        folder.chmod(0o755)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "Cannot search '{}': permission denied".format(folder) in result.stderr
    assert "Traceback" not in result.stderr


# --- Filenames with unusual characters --------------------------------------


def test_odd_filename_logs_and_exports(logs, tmp_path):
    """A filename with non-UTF-8 bytes is logged and exported, never fatal."""
    # b"\xff" is not valid UTF-8; Linux stores it via surrogateescape.
    odd = os.path.join(os.fsencode(str(tmp_path)), b"odd-\xff.txt")
    with open(odd, "wb") as file:
        file.write(b"hello")
    entry = safe_file_entry(os.fsdecode(odd))
    assert entry is not None
    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    results = build_results([entry], matcher)
    assert len(results) == 1
    out = tmp_path / "out.csv"
    write_results_csv(results, out)
    text = out.read_text(encoding="utf-8-sig")
    assert "odd-" in text  # the odd byte became a readable escape
    # Logging the same name must not break the log file either.
    logging.getLogger("zipsearch").error("Saw %s", entry.container_path)
    assert "odd-" in logs[1].read_text()


# --- The whole run still finishes and writes the CSV ------------------------


def test_run_finishes_and_writes_csv_of_working_files(
    logs, tmp_path, make_zip, make_corrupt_zip, make_encrypted_zip
):
    """Good files reach the CSV even with a bad ZIP, a locked ZIP and a
    denied folder in the same tree, and every skip is explained in the log."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "notes.txt").write_text("hello")
    make_zip({"inner.txt": "inside"}, name=str(root / "good.zip"))
    make_corrupt_zip(name=str(root / "corrupt.zip"))
    make_encrypted_zip(name=str(root / "locked.zip"))
    if not running_as_root():
        denied = root / "denied"
        denied.mkdir()
        (denied / "hidden.txt").write_text("secret")
        denied.chmod(0)

    matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})
    entries = []
    try:
        for name in walk(root):
            if name.lower().endswith(".zip"):
                entries.extend(iter_zip_entries_safe(name))
            else:
                entry = safe_file_entry(name)
                if entry is not None:
                    entries.append(entry)
        results = build_results(entries, matcher)
        out = tmp_path / "results.csv"
        write_results_csv(results, out)
    finally:
        if not running_as_root():
            denied.chmod(0o755)

    text = out.read_text(encoding="utf-8-sig")
    assert "notes.txt" in text          # ordinary file made it
    assert "inner.txt" in text          # good ZIP's member made it
    assert "good.zip" in text
    log_text = logs[1].read_text()
    assert "corrupt.zip" in log_text    # corrupt ZIP skip explained
    assert "Password-protected member" in log_text  # locked ZIP explained
    if not running_as_root():
        assert "denied" in log_text     # denied folder explained
