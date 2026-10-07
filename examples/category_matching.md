# Category matching

This step gives each file zero, one or several category names. It checks names,
not file contents, and does not change `main.py` yet.

## Start with a Python dict

```python
from zipsearch.categories import CategoryMatcher

categories = {
    "documents": {"extensions": [".txt", ".pdf"]},
    "reports": {"patterns": ["report_*", "*_report.*"]},
}
matcher = CategoryMatcher(categories)
print(matcher.match("docs/report_sales.txt"))
# ['documents', 'reports']
```

A dict connects each category name to its rules. `extensions` checks the end
of the filename. Include the dot: `.txt`, not `txt`. You can also use a compound
extension such as `.tar.gz`.

`patterns` uses filename globs: `*` means any text, `?` means one character,
and `[ab]` means either `a` or `b`. These are not regular expressions.

Rules use OR: when a category has both extensions and patterns, either kind
can make it match. Matching ignores capitals and only checks the final filename,
not the folders before it. Every matching category is returned in config order;
an unmatched file returns `[]`. Folder entries are skipped.

## Or use JSON

```python
from zipsearch.categories import load_categories

matcher = load_categories("examples/categories.json")
print(matcher.match("report_october.txt"))
# ['documents', 'reports']
```

JSON stores the same dict in a separate text file, so you can edit the category
rules without editing Python code. The example categories are only examples,
not a fixed list. Misspelled rule fields, empty rules and invalid extensions
raise a `ValueError` instead of silently failing to match.

## Use it with ZIP entries

```python
from zipsearch.zip_reader import iter_zip_entries

for entry in iter_zip_entries("my_files.zip"):
    print(entry.inner_path, matcher.match_entry(entry))
```

`match_entry` takes the filename inside the ZIP, not the ZIP's own name.
For an ordinary-file `Entry`, it uses that file's path instead. It never reads
file contents or extracts anything. This example connects the existing modules
in a short script; the main command-line program has not been changed.

## What to read

1. `examples/categories.json`: the category rules.
2. `zipsearch/categories.py`: `match` checks a name; `match_entry` picks the right
   name from an `Entry`; `load_categories` reads JSON.
3. `tests/test_categories.py`: small examples of the expected results.

`PurePosixPath` from `pathlib` takes the last part of a path without opening a
file. The matcher normalizes backslashes first, so Windows file paths and ZIP
member paths can both be checked, even on Linux.
