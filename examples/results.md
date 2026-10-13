# Matched-file results

A Python list is our results array. Each item is a dict: named fields attached
to one matched file. `category` is a list, so a file that matches two categories
still has just one result.

## Ordinary files

```python
from zipsearch.categories import load_categories
from zipsearch.results import build_results, file_entry
from zipsearch.walker import walk

matcher = load_categories("examples/categories.json")
entries = (file_entry(path) for path in walk("my_folder"))
results = build_results(entries, matcher)
print(results)
```

`walk` supplies file paths. `file_entry` uses pathlib to get each file's size
and last-modified time. `build_results` checks its categories and appends a dict
only if it matches. The bracket expression above creates a generator: it
hands over one entry at a time. The final `results` is a list kept in memory.

## Files inside one ZIP

```python
from zipsearch.categories import load_categories
from zipsearch.results import build_results
from zipsearch.zip_reader import iter_zip_entries

matcher = load_categories("examples/categories.json")
results = build_results(iter_zip_entries("my_files.zip"), matcher)
print(results)
```

This reads the ZIP's table of contents, not file contents, and extracts nothing.
It does not open ZIPs inside that ZIP.

For a matching member `docs/report.txt` inside `my_files.zip`, a result looks
like this (illustrative metadata):

```python
{
    "category": ["documents", "reports"],
    "filename": "report.txt",
    "folder_location": "docs",
    "zipfile": "my_files.zip",
    "filesizebytes": 120,
    "last_modified": "2020-02-03T04:05:06",
}
```

## Field meanings

- `category`: every matching category, in config order.
- `filename`: the file's name without its folders.
- `folder_location`: the containing filesystem folder for an ordinary file,
  or the internal containing folder for a ZIP member. `.` means the current
  folder or the root of the ZIP. Paths stay relative or absolute as supplied;
  pathlib tidies repeated separators and `./`.
- `zipfile`: the ZIP's path for a member; an empty string for an ordinary file.
- `filesizebytes`: byte size, uncompressed for ZIP members.
- `last_modified`: ISO8601 date/time. Ordinary-file times use UTC (`+00:00`).
  ZIP member dates have no timezone, so we keep the stored wall time without
  adding a guessed offset. An invalid or unavailable date is `None`, which
  becomes `null` if the result is later converted to JSON.

Folders and unmatched files do not produce results. Input order is kept.
An unreadable/missing ordinary file raises `OSError`; a corrupt ZIP raises
`BadZipFile`, as the existing ZIP reader does. This step adds no skip/reporting
policy. Encrypted ZIP members can be listed and matched without a password
because no file contents are read.

`Result` is a `TypedDict`: it documents the expected fields for code editors.
At runtime, each result is still a normal dict. `Entry.last_modified` defaults
to `None`, so older code that creates `Entry` records still works.

`main.py` is unchanged. These examples call the building blocks directly;
the normal run command still prints its folder/file listing.
