# Saving results to a CSV file

A CSV file is a plain-text table: one row per line, columns separated by
commas. Excel and other spreadsheet programs open it.

```python
from zipsearch.categories import load_categories
from zipsearch.csv_export import write_results_csv
from zipsearch.results import build_results, file_entry
from zipsearch.walker import walk

matcher = load_categories("examples/categories.json")
entries = (file_entry(path) for path in walk("my_folder"))
results = build_results(entries, matcher)
write_results_csv(results, "results.csv")
```

The columns come in the same order as the fields of each result:
`category`, `filename`, `folder_location`, `zipfile`, `filesizebytes`,
`last_modified`.

## How the file is written

- **UTF-8 with a BOM (`utf-8-sig`).** A BOM is a few invisible bytes at the
  start of the file. They tell Excel the text is UTF-8, so accents and
  non-English characters show correctly.
- **Quoting.** A filename like `my "best", file.txt` would normally break the
  columns. Python's `csv` module wraps such values in quotes and doubles any
  quote inside, so the file stays correct. Reading it back gives the original
  text.
- **Several categories.** A file has one row. Its categories share one cell,
  joined with `; `, for example `documents; reports`.
- **Missing date.** A `last_modified` of `None` becomes an empty cell.
- **Existing file.** A file already at that path is replaced. The folder must
  already exist, otherwise Python raises `OSError`.

`main.py` is unchanged; this step only adds the function.
