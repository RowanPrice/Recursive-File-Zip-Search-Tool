# Shared logging

Logging is a record of what the program did. Unlike the folder listing, the
record stays in a file so you can read it after the program finishes.

```bash
python main.py /path/to/root_folder
python main.py /path/to/root_folder --log-file /existing/folder/search.log
```

The default is `zipsearch.log` in the folder you run the command from, not
inside the searched root. Each run appends to the file. The log's parent folder
must already exist. A log file that cannot be opened produces a console ERROR
and stops the CLI with exit code 1, because that run could not meet the promise
to write to both destinations.

Messages go to the console's stderr stream and to a UTF-8 file. The directory
listing still goes to stdout. Each log line starts with the local date/time,
severity and module, for example:

```text
2026-10-13 09:00:00 INFO zipsearch: Run started
2026-10-13 09:00:00 INFO zipsearch: Root folder: documents
2026-10-13 09:00:00 INFO zipsearch: Run ended (completed)
```

- INFO: ordinary progress, including start, root, end and category counts.
- WARNING: something unusual, such as an invalid ZIP timestamp or an interrupted run.
- ERROR: a failure. Exceptions include a traceback showing where it happened.

## Use it with the separate building blocks

```python
from zipsearch.categories import CategoryMatcher
from zipsearch.logging_setup import setup_logging
from zipsearch.results import build_results, file_entry

logger = setup_logging("search.log")
logger.info("Run started")
logger.info("Root folder: documents")
try:
    matcher = CategoryMatcher({
        "text": {"extensions": [".txt"]},
        "images": {"extensions": [".png"]},
    })
    results = build_results([file_entry("documents/report.txt")], matcher)
finally:
    logger.info("Run ended")
```

`build_results` logs one count for each configured category, including zero.
A file in two categories adds one to each category. Directories and unmatched
files do not add anything. Counts are per call, not a running total. Failed
calls log their exception and do not print a misleading final count.

Call `setup_logging` once before using the helpers. Python's `logging` module
uses names like `zipsearch.results` to pass their messages to the shared
`zipsearch` logger. Two handlers send each message to its two destinations;
a formatter adds the time and level. Reconfiguring replaces handlers instead
of doubling the output. Other libraries' logging is left alone.

Helper failures still raise the same exceptions, so calling code can decide
whether to stop or continue. Folder traversal errors that `os.walk` previously
ignored are now logged and traversal still continues through accessible folders.
An invalid ZIP timestamp logs a WARNING and keeps the existing `None` date.

This is a logging-only step. `main.py` still lists folders; it does not call
category matching, ZIP reading, the results builder or CSV export. Category
counts appear when `build_results` is called, as in the example above. CLI
argument mistakes are still handled by argparse before a run starts. There is
no log rotation or automatic creation of parent folders in this step.
