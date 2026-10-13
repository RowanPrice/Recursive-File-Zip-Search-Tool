"""Write the matched-file results array to a CSV file that Excel can open."""

import csv
import logging
from pathlib import Path
from typing import Iterable

from zipsearch.logging_setup import log_errors
from zipsearch.models import Path as FilePath
from zipsearch.results import Result

# Column order: the same as the fields of a Result dict.
COLUMNS = (
    "category",
    "filename",
    "folder_location",
    "zipfile",
    "filesizebytes",
    "last_modified",
)

# Several categories share one cell, so they need a separator.
CATEGORY_SEPARATOR = "; "


def _write_results_csv(results: Iterable[Result], path: FilePath) -> None:
    """Save results as a CSV file: a header row, then one row per result.

    - The file is UTF-8 with a byte order mark (utf-8-sig) so Excel reads
      accented letters and other non-English characters correctly.
    - The csv module adds quotes where needed, so commas, quotes and line
      breaks inside a filename do not break the columns.
    - A file with several categories gets one row; the categories are joined
      with "; " (for example "documents; reports").
    - A last_modified of None becomes an empty cell.
    - A filename with unusual bytes is written as a readable escape instead
      of crashing the export (see errors="backslashreplace" below).
    - An existing file at this path is replaced. The folder must already
      exist; a missing folder or unwritable path raises OSError.
    """
    # newline="" lets the csv module control line endings (needed on Windows).
    # errors="backslashreplace" writes a filename containing bytes that UTF-8
    # cannot store as a readable \xNN-style escape, so one odd filename can
    # never lose the whole CSV.
    with Path(path).open(
        "w", encoding="utf-8-sig", newline="", errors="backslashreplace"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for result in results:
            row = []
            for column in COLUMNS:
                value = result[column]
                if column == "category":
                    value = CATEGORY_SEPARATOR.join(value)
                elif value is None:
                    value = ""
                row.append(value)
            writer.writerow(row)


@log_errors
def write_results_csv(results: Iterable[Result], path: FilePath) -> None:
    """Save results as a CSV file: a header row, then one row per result.

    Raises OSError when the file cannot be written. Use
    safe_write_results_csv to log one clear line instead of raising.
    """
    _write_results_csv(results, path)


def safe_write_results_csv(results: Iterable[Result], path: FilePath) -> bool:
    """Like write_results_csv, but return False instead of raising OSError.

    One ERROR line keeps the CSV path and the exact reason, so the caller
    can stop with a clear message instead of a traceback.
    """
    try:
        _write_results_csv(results, path)
        return True
    except OSError as error:
        logging.getLogger(__name__).error(
            "Cannot write CSV '%s': %s: %s", path, type(error).__name__, error
        )
        return False
