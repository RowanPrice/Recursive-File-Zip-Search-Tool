# Error handling

A search can meet broken things: a corrupt ZIP, a password-protected ZIP, a
folder or file you are not allowed to read, or a filename with unusual bytes.
The rule everywhere is the same: log exactly what went wrong and where, skip
that one item, and carry on with the rest, so the run still finishes and the
CSV contains everything that did work.

## What each problem does

- **Corrupt or truncated ZIP.** `iter_zip_entries_safe` logs one ERROR line
  with the ZIP's path and the exact reason, yields nothing for that ZIP, and
  the search moves on.
- **Password-protected ZIP.** Its members can usually still be listed, so
  they appear flagged `encrypted=True` and each gets a WARNING saying the
  contents cannot be read without the password. A protected ZIP that cannot
  even be listed is skipped like a corrupt one.
- **Permission-denied folder.** The walk logs an ERROR naming the folder and
  continues with the folders it can read.
- **Permission-denied or vanished file.** `safe_file_entry` logs one ERROR
  with the file's path and the exact reason, and returns None so the caller
  can skip it.
- **Unusual filename.** A name with bytes UTF-8 cannot store is written to
  the log and the CSV as a readable escape instead of crashing either one.
- **Missing or unreadable root folder.** `main.py` stops before searching
  with one clear message and exit code 1, never a traceback:

```text
2026-10-13 10:00:00 ERROR zipsearch: Cannot search 'private': permission denied
```

## Safe vs plain functions

The plain functions (`iter_zip_entries`, `file_entry`) still raise on a
problem, with the traceback logged. The safe ones
(`iter_zip_entries_safe`, `safe_file_entry`) log a single clear line and
skip. Callers that process many files use the safe pair, so one bad item
never stops the whole run.

## Example: a run that survives a broken tree

```python
from zipsearch.categories import CategoryMatcher
from zipsearch.csv_export import write_results_csv
from zipsearch.logging_setup import setup_logging
from zipsearch.results import build_results, safe_file_entry
from zipsearch.walker import walk
from zipsearch.zip_reader import iter_zip_entries_safe

setup_logging("search.log")
matcher = CategoryMatcher({"text": {"extensions": [".txt"]}})

entries = []
for name in walk("/path/to/root_folder"):
    if name.lower().endswith(".zip"):
        entries.extend(iter_zip_entries_safe(name))
    else:
        entry = safe_file_entry(name)
        if entry is not None:  # None means the file was skipped
            entries.append(entry)

results = build_results(entries, matcher)
write_results_csv(results, "results.csv")
```

Even with a corrupt ZIP, a locked ZIP and a denied folder in the tree, this
finishes and `results.csv` holds every match that worked. The log explains
each skip:

```text
2026-10-13 10:00:00 ERROR zipsearch.zip_reader: Skipping ZIP 'corrupt.zip': BadZipFile: File is not a zip file
2026-10-13 10:00:00 WARNING zipsearch.zip_reader: Password-protected member 'secret.txt' in ZIP 'locked.zip': listed only, contents not read
2026-10-13 10:00:00 ERROR zipsearch.walker: Cannot access folder denied: [Errno 13] Permission denied: 'denied'
```

## The command line now runs the whole search

`main.py` connects the pieces above: it walks the folders, opens every ZIP,
matches categories and writes the CSV.

```bash
python main.py /path/to/root_folder
python main.py /path/to/root_folder --categories my_rules.json --csv out.csv
```

- `--categories` picks the category rules. The default is the bundled
  `examples/categories.json`, so a plain run works out of the box.
- `--csv` picks the output file. The default is `results.csv` in the folder
  you run the command from.
- `--log-file` picks the log file as before (default `zipsearch.log`).

The folder listing still prints while the search runs, and the last line
names the CSV and how many files matched. A missing or unreadable root
folder, a broken `--categories` file or an unwritable `--csv` path each stop
the run with one clear ERROR line and exit code 1, never a traceback. Bad
items found along the way (corrupt ZIPs, denied folders, odd filenames) are
logged and skipped: the run still finishes with exit code 0 and the CSV
contains everything that worked.
