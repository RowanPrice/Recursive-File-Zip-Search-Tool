#!/usr/bin/env python3
"""Recursive File Zip Search Tool"""
import argparse
import logging
import sys
from pathlib import Path

from zipsearch import walker
from zipsearch.logging_setup import setup_logging


def main():
    """Validate the root folder, log the run and print the directory listing."""
    parser = argparse.ArgumentParser(
        description="Recursively walk through folders and search files/zips"
    )
    parser.add_argument(
        "root_folder",
        help="Root folder path to start searching from"
    )
    parser.add_argument(
        "--log-file", default="zipsearch.log",
        help="Log file path (default: zipsearch.log in the working folder)"
    )
    args = parser.parse_args()

    try:
        logger = setup_logging(args.log_file)
    except OSError:
        # setup_logging has already reported why the file cannot be opened.
        sys.exit(1)

    root_path = Path(args.root_folder)
    logger.info("Run started")
    logger.info("Root folder: %s", root_path)
    outcome = "failed"
    try:
        if not root_path.is_dir():
            logger.error("'%s' is not a valid directory", root_path)
            sys.exit(1)

        print(f"Walking: {root_path}")
        for root, dirs, files in walker.walk_directories(root_path):
            print(f"\nDirectory: {root}")
            for d in dirs:
                print(f"  [DIR] {d}")
            for f in files:
                print(f"  [FILE] {f}")
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
