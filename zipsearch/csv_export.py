"""Write the matched-file results array to a CSV file that Excel can open."""

import csv
from pathlib import Path
from typing import Iterable

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


def write_results_csv(results: Iterable[Result], path: FilePath) -> None:
    """Save results as a CSV file: a header row, then one row per result.

    - The file is UTF-8 with a byte order mark (utf-8-sig) so Excel reads
      accented letters and other non-English characters correctly.
    - The csv module adds quotes where needed, so commas, quotes and line
      breaks inside a filename do not break the columns.
    - A file with several categories gets one row; the categories are joined
      with "; " (for example "documents; reports").
    - A last_modified of None becomes an empty cell.
    - An existing file at this path is replaced. The folder must already
      exist; a missing folder or unwritable path raises OSError.
    """
    # newline="" lets the csv module control line endings (needed on Windows).
    with Path(path).open("w", encoding="utf-8-sig", newline="") as file:
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
