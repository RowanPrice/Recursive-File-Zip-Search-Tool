#!/usr/bin/env python3
"""File Audit: recursively search folders and ZIPs, and save matches to a CSV."""
import argparse
import logging
import sys
from pathlib import Path

from zipsearch import walker
from zipsearch.categories import safe_load_categories
from zipsearch.csv_export import safe_write_results_csv
from zipsearch.logging_setup import setup_logging
from zipsearch.results import build_results, safe_file_entry
from zipsearch.zip_reader import iter_zip_entries_safe

# Category rules bundled with the project, so a plain run just works.
# --categories points at any other JSON file with the same shape.
DEFAULT_CATEGORIES = Path(__file__).resolve().parent / "examples" / "categories.json"


def main():
    """Validate inputs, log the run, walk folders and write the matches CSV."""
    parser = argparse.ArgumentParser(
        description="Recursively walk folders, look inside ZIPs and save matches to a CSV"
    )
    parser.add_argument(
        "root_folder", nargs="?",
        help="Root folder to start searching from (same as --root)"
    )
    parser.add_argument(
        "--root", dest="root_option",
        help="Root folder to start searching from, as a named argument "
             "(same as the positional root_folder)"
    )
    parser.add_argument(
        "--log-file", default="zipsearch.log",
        help="Log file path (default: zipsearch.log in the working folder)"
    )
    parser.add_argument(
        "--categories", default=str(DEFAULT_CATEGORIES),
        help="Category rules JSON (default: the bundled examples/categories.json)"
    )
    parser.add_argument(
        "--csv", default="results.csv",
        help="CSV output path (default: results.csv in the working folder)"
    )
    args = parser.parse_args()

    # The root folder can be given either way, but exactly once.
    if args.root_folder and args.root_option:
        parser.error("give the root folder once: either as an argument or with --root")
    root_argument = args.root_option or args.root_folder
    if root_argument is None:
        parser.error("a root folder is required: pass it as an argument or with --root")

    try:
        logger = setup_logging(args.log_file)
    except OSError:
        # setup_logging has already reported why the file cannot be opened.
        sys.exit(1)

    # Resolve the root so the CSV holds full absolute folder paths.
    root_path = Path(root_argument).resolve()
    logger.info("Run started")
    logger.info("Root folder: %s", root_path)
    outcome = "failed"
    try:
        problem = walker.root_problem(root_path)
        if problem is not None:
            # One clear line, no traceback, so the fix is obvious.
            logger.error("Cannot search '%s': %s", root_path, problem)
            sys.exit(1)

        matcher = safe_load_categories(args.categories)
        if matcher is None:
            # safe_load_categories has already logged the clear reason.
            sys.exit(1)

        entries = []
        for root, _dirs, files in walker.walk_directories(root_path):
            for f in files:
                path = str(Path(root) / f)
                if f.lower().endswith(".zip"):
                    # Bad ZIPs are logged and skipped inside the safe reader.
                    entries.extend(iter_zip_entries_safe(path))
                else:
                    # None means the file was unreadable, logged and skipped.
                    entry = safe_file_entry(path)
                    if entry is not None:
                        entries.append(entry)

        results = build_results(entries, matcher)
        if not safe_write_results_csv(results, args.csv):
            # safe_write_results_csv has already logged the clear reason.
            sys.exit(1)
        logger.info("CSV written to '%s': %d matched file(s)", args.csv, len(results))
        outcome = "completed"
    except KeyboardInterrupt:
        outcome = "interrupted"
        logger.warning("Run interrupted by the user")
        raise
    except Exception:
        logger.exception("Run failed")
        raise
    finally:
        logger.info("Run ended (%s)", outcome)
        # Flush messages before the process exits or a caller reads the log.
        for handler in logging.getLogger("zipsearch").handlers:
            handler.flush()


if __name__ == "__main__":
    main()
