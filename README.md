# Recursive File Zip Search Tool

A command-line tool that searches a folder and every folder inside it, looks inside any `.zip` files it finds, sorts the files it finds into categories (like "documents" or "images"), and saves the matches to a spreadsheet-friendly CSV file.

It matches on file **names** only (extension or name pattern). It does not read what is inside the files, and it does not open zip files that are inside other zip files.

## What you need

- Python 3.8 or newer. Check with `python --version` (on some computers it is `python3`).
- This project downloaded or cloned onto your computer.

No extra packages to install.

## Quick start

1. Open a terminal and go to the project folder (the one that contains `main.py`):

   ```bash
   cd path/to/Recursive-File-Zip-Search-Tool
   ```

2. Run the tool and give it the folder you want to search:

   ```bash
   python main.py /path/to/folder_to_search
   ```

   If the path has spaces in it, put it in quotes:

   ```bash
   python main.py "/Users/me/My Documents"
   ```

3. When it finishes, look in the project folder. You now have two new files:
   - `results.csv` - the files it found (open it in Excel, Numbers or Google Sheets)
   - `zipsearch.log` - a diary of what happened, including any problems

To see all the options at any time:

```bash
python main.py --help
```

## The options

| Option | What it does | Default |
| --- | --- | --- |
| `root_folder` (required) | The folder to start searching from | none |
| `--categories FILE` | A JSON file with your category rules | `examples/categories.json` |
| `--csv FILE` | Where to save the results | `results.csv` |
| `--log-file FILE` | Where to write the log | `zipsearch.log` |

Example using all of them:

```bash
python main.py "/Users/me/My Documents" --categories my_categories.json --csv my_results.csv --log-file my_run.log
```

The default `results.csv` and `zipsearch.log` are saved in the folder you ran the command from. Each run replaces the CSV file but adds to the end of the log file, so the log keeps a history of earlier runs.

## Choosing your categories

Categories are rules that decide which files end up in the CSV. A file that matches no category is left out. They live in a JSON file. The one that comes with the project is `examples/categories.json`:

```json
{
  "documents": {"extensions": [".txt", ".pdf", ".docx"]},
  "images": {"extensions": [".png", ".jpg", ".jpeg"]},
  "reports": {"patterns": ["report_*", "*_report.*"]},
  "python": {"extensions": [".py"], "patterns": ["requirements*.txt"]}
}
```

Each category has a name and one or both of:

- `extensions` - file endings. Each must start with a dot, like `".pdf"`.
- `patterns` - name patterns where `*` means "any text" and `?` means "any one character". For example `report_*` matches `report_2026.xlsx`.

A file only needs to match **one** rule to join a category. Matching ignores upper and lower case, and a file can belong to several categories.

To use your own rules, copy `examples/categories.json`, edit it, and run the tool with `--categories your_file.json`.

## What is in results.csv

One row per matched file, with these columns:

| Column | Meaning |
| --- | --- |
| `category` | Matching categories. If there are several they are joined like `documents; reports` |
| `filename` | The file's name |
| `folder_location` | The folder it is in (for a file inside a zip, the folder path inside the zip) |
| `zipfile` | The zip it came from, or empty if it is a normal file |
| `filesizebytes` | Size in bytes |
| `last_modified` | Last changed date and time (UTC) |

## When something goes wrong

**The tool keeps going and notes the problem in the log** when it hits:

- a zip file that is damaged (corrupt) - it is skipped
- a password-protected zip - the files inside are still listed and marked as encrypted in the log, but their contents are not read
- a file or folder it is not allowed to open (permission denied) - it is skipped
- a file name with unusual characters - it is saved with a readable escape code instead of crashing

Open `zipsearch.log` and look for lines starting with `WARNING` or `ERROR` to see what was skipped and why.

**The tool stops with one clear message** (and no scary traceback) when:

- the folder you gave does not exist, is a file instead of a folder, or cannot be opened
- the categories file is missing or has invalid rules
- the CSV file cannot be saved (for example the folder for it does not exist)
