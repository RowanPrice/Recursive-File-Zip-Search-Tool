"""Check the shared destinations, counts and errors, without hiding failures."""

import io
import logging
import re
from pathlib import Path
from zipfile import BadZipFile

import pytest

from zipsearch.categories import CategoryMatcher, load_categories
from zipsearch.csv_export import write_results_csv
from zipsearch.logging_setup import setup_logging
from zipsearch.models import Entry
from zipsearch.results import build_results, file_entry
from zipsearch.zip_reader import iter_zip_entries


@pytest.fixture
def logs(tmp_path):
    logger = logging.getLogger("zipsearch")
    old_handlers = logger.handlers[:]
    old_level, old_propagate = logger.level, logger.propagate
    logger.handlers = []
    console = io.StringIO()
    path = tmp_path / "run.log"
    setup_logging(path, console=console)
    yield console, path
    for handler in logger.handlers[:]:
        handler.close()
    logger.handlers = old_handlers
    logger.setLevel(old_level)
    logger.propagate = old_propagate


def test_both_destinations_and_levels(logs):
    console, path = logs
    logger = logging.getLogger("zipsearch.example")
    logger.info("Started café")
    logger.warning("Skipped something")
    logger.error("Something failed")
    logger.debug("Not enabled")
    text = path.read_text(encoding="utf-8")
    assert text == console.getvalue()
    assert "INFO zipsearch.example: Started café" in text
    assert "WARNING zipsearch.example: Skipped something" in text
    assert "ERROR zipsearch.example: Something failed" in text
    assert "Not enabled" not in text
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO", text)


def test_reconfigure_appends_without_duplicates(logs):
    console, path = logs
    logging.getLogger("zipsearch").info("First")
    setup_logging(path, console=console)
    logging.getLogger("zipsearch").info("Second")
    text = path.read_text()
    assert text.count("First") == text.count("Second") == 1
    assert len(logging.getLogger("zipsearch").handlers) == 2


def test_failed_setup_reports_and_keeps_previous_handlers(logs, tmp_path):
    console, path = logs
    old_handlers = logging.getLogger("zipsearch").handlers[:]
    with pytest.raises(OSError):
        setup_logging(tmp_path / "missing" / "run.log", console=console)
    assert logging.getLogger("zipsearch").handlers == old_handlers
    assert "ERROR" in console.getvalue()
    assert "Cannot open log file" in console.getvalue()
    logging.getLogger("zipsearch").info("Still working")
    assert "Still working" in path.read_text()


def test_setup_does_not_change_root_logger(logs):
    root = logging.getLogger()
    before = root.handlers[:], root.level
    setup_logging(logs[1], console=logs[0])
    assert (root.handlers, root.level) == before


@pytest.mark.parametrize("operation", [
    lambda path: file_entry(path),
    lambda path: list(iter_zip_entries(path)),
    lambda path: load_categories(path),
    lambda path: write_results_csv([], path / "out.csv"),
])
def test_helper_errors_are_logged_and_still_raise(logs, tmp_path, operation):
    with pytest.raises((OSError, BadZipFile)):
        operation(tmp_path / "missing")
    text = logs[1].read_text()
    assert "ERROR" in text
    assert "failed" in text
    assert "Traceback" in text


def test_invalid_categories_logged(logs):
    with pytest.raises(ValueError):
        CategoryMatcher({"bad": {}})
    assert "ERROR" in logs[1].read_text()


def test_generator_failure_during_results_is_logged(logs):
    def entries():
        yield Entry("a.txt", "", 1, False)
        raise PermissionError("lost access")

    with pytest.raises(PermissionError, match="lost access"):
        build_results(entries(), CategoryMatcher({"text": {"extensions": [".txt"]}}))
    assert "build_results failed" in logs[1].read_text()


def test_walk_logs_permission_error(logs, monkeypatch):
    from zipsearch import walker

    def fake_walk(root, onerror):
        onerror(PermissionError(13, "Permission denied", "private"))
        yield root, [], ["ok.txt"]

    monkeypatch.setattr(walker.os, "walk", fake_walk)
    assert list(walker.walk(Path("root"))) == [str(Path("root") / "ok.txt")]
    text = logs[1].read_text()
    assert "ERROR" in text and "private" in text


def test_counts_include_multiple_categories_and_zero_matches(logs):
    matcher = CategoryMatcher({
        "text": {"extensions": [".txt"]},
        "reports": {"patterns": ["report*"]},
        "images": {"extensions": [".png"]},
    })
    results = build_results([
        Entry("report.txt", "", 1, False),
        Entry("b.txt", "", 1, False),
        Entry("ignore.bin", "", 1, False),
        Entry("folder.txt", "", 0, False, is_dir=True),
    ], matcher)
    assert len(results) == 2
    text = logs[1].read_text()
    assert "Files matched in category text: 2" in text
    assert "Files matched in category reports: 1" in text
    assert "Files matched in category images: 0" in text


def test_empty_results_log_zero_for_every_category(logs):
    assert build_results([], CategoryMatcher({"text": {"extensions": [".txt"]}})) == []
    assert "Files matched in category text: 0" in logs[1].read_text()


def test_cli_start_root_end_and_file_match(tmp_path):
    import subprocess
    import sys

    root = tmp_path / "root"
    root.mkdir()
    (root / "file.txt").write_text("hello")
    log = tmp_path / "run.log"
    main = Path(__file__).resolve().parents[1] / "main.py"
    result = subprocess.run(
        [sys.executable, str(main), str(root), "--log-file", str(log),
         "--csv", str(tmp_path / "out.csv")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "[FILE] file.txt" in result.stdout
    text = log.read_text()
    assert result.stderr == text
    assert "Run started" in text
    assert "Root folder: {}".format(root) in text
    assert "Run ended (completed)" in text


def test_cli_cannot_open_log_file(tmp_path):
    import subprocess
    import sys

    main = Path(__file__).resolve().parents[1] / "main.py"
    result = subprocess.run(
        [sys.executable, str(main), str(tmp_path), "--log-file",
         str(tmp_path / "missing" / "run.log")],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "ERROR" in result.stderr
    assert "Cannot open log file" in result.stderr
    assert result.stdout == ""


def test_cli_unexpected_failure_still_logs_end(logs, tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "setup_logging", lambda path: logging.getLogger("zipsearch"))
    monkeypatch.setattr("sys.argv", ["main.py", str(tmp_path)])

    def fail(root):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(main.walker, "walk_directories", fail)
    with pytest.raises(RuntimeError):
        main.main()
    text = logs[1].read_text()
    assert "ERROR" in text and "unexpected failure" in text
    assert "Run ended (failed)" in text


def test_cli_interrupt_still_logs_end(logs, tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "setup_logging", lambda path: logging.getLogger("zipsearch"))
    monkeypatch.setattr("sys.argv", ["main.py", str(tmp_path)])

    def interrupt(root):
        raise KeyboardInterrupt

    monkeypatch.setattr(main.walker, "walk_directories", interrupt)
    with pytest.raises(KeyboardInterrupt):
        main.main()
    text = logs[1].read_text()
    assert "WARNING" in text
    assert "Run ended (interrupted)" in text
