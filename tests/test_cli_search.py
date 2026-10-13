"""The wired command line: a real run searches and writes the CSV."""

import csv
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    """Run main.py in a subprocess, exactly as a user would."""
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), *[str(a) for a in args]],
        capture_output=True, text=True,
    )


def read_csv(path):
    """Return the CSV rows as dicts, keyed by the header row."""
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def test_run_searches_zips_and_writes_csv(tmp_path, make_zip, make_corrupt_zip):
    """Ordinary files and good ZIP members reach the CSV; a corrupt ZIP is
    logged and skipped; the listing still prints; the exit code stays 0."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "notes.txt").write_text("hello")
    (root / "photo.png").write_text("png")
    make_zip({"inner.txt": "inside"}, name=str(root / "good.zip"))
    make_corrupt_zip(name=str(root / "corrupt.zip"))
    log = tmp_path / "run.log"
    out = tmp_path / "results.csv"

    result = run_cli(root, "--log-file", log, "--csv", out)

    assert result.returncode == 0
    assert "[FILE] notes.txt" in result.stdout
    assert "CSV written: {} (".format(out) in result.stdout
    rows = read_csv(out)
    by_name = {row["filename"]: row for row in rows}
    # The bundled default categories cover .txt and .png.
    assert by_name["notes.txt"]["category"] == "documents"
    assert by_name["photo.png"]["category"] == "images"
    assert by_name["inner.txt"]["zipfile"].endswith("good.zip")
    text = log.read_text()
    assert "Skipping ZIP" in text and "corrupt.zip" in text
    assert "Files matched in category documents: 2" in text
    assert "Run ended (completed)" in text
    assert "Traceback" not in result.stderr


def test_run_with_custom_categories_json(tmp_path):
    """--categories swaps the rules: here only report files are collected."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "notes.txt").write_text("hello")
    (root / "report_oct.txt").write_text("sales")
    categories = tmp_path / "cats.json"
    categories.write_text('{"reports": {"patterns": ["report_*"]}}')
    out = tmp_path / "results.csv"

    result = run_cli(root, "--log-file", tmp_path / "run.log",
                     "--categories", categories, "--csv", out)

    assert result.returncode == 0
    assert [row["filename"] for row in read_csv(out)] == ["report_oct.txt"]


def test_missing_categories_file_fails_clearly(tmp_path):
    """A missing config is one clear ERROR and exit 1, never a traceback."""
    result = run_cli(tmp_path, "--log-file", tmp_path / "run.log",
                     "--categories", tmp_path / "missing.json",
                     "--csv", tmp_path / "out.csv")
    assert result.returncode == 1
    assert "Cannot load categories from" in result.stderr
    assert "missing.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "out.csv").exists()


def test_bad_categories_json_fails_clearly(tmp_path):
    """Broken JSON rules are one clear ERROR and exit 1, never a crash."""
    categories = tmp_path / "cats.json"
    categories.write_text("{not json")
    result = run_cli(tmp_path, "--log-file", tmp_path / "run.log",
                     "--categories", categories, "--csv", tmp_path / "out.csv")
    assert result.returncode == 1
    assert "Cannot load categories from" in result.stderr
    assert "Traceback" not in result.stderr


def test_unwritable_csv_path_fails_clearly(tmp_path):
    """An unsavable CSV is reported clearly after the search, with exit 1."""
    (tmp_path / "file.txt").write_text("hello")
    result = run_cli(tmp_path, "--log-file", tmp_path / "run.log",
                     "--csv", tmp_path / "missing" / "out.csv")
    assert result.returncode == 1
    assert "Cannot write CSV" in result.stderr
    assert "Traceback" not in result.stderr


def test_encrypted_zip_members_reach_csv_flagged_in_log(
    tmp_path, make_encrypted_zip
):
    """Password-protected members are listed in the CSV (metadata is all the
    tool reads) and the log warns their contents cannot be read."""
    root = tmp_path / "tree"
    root.mkdir()
    make_encrypted_zip(name=str(root / "locked.zip"))
    log = tmp_path / "run.log"
    out = tmp_path / "results.csv"
    result = run_cli(root, "--log-file", log, "--csv", out)
    assert result.returncode == 0
    rows = read_csv(out)
    assert [row["filename"] for row in rows] == ["secret.txt"]
    assert rows[0]["zipfile"].endswith("locked.zip")
    assert "Password-protected member 'secret.txt'" in log.read_text()
