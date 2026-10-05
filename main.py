#!/usr/bin/env python3
"""Recursive File Zip Search Tool"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Recursively walk through folders and search files/zips"
    )
    parser.add_argument(
        "root_folder",
        help="Root folder path to start searching from"
    )
    args = parser.parse_args()

    root_path = args.root_folder

    if not os.path.isdir(root_path):
        print(f"Error: '{root_path}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    print(f"Walking: {root_path}")
    for root, dirs, files in os.walk(root_path):
        print(f"\nDirectory: {root}")
        for d in dirs:
            print(f"  [DIR] {d}")
        for f in files:
            print(f"  [FILE] {f}")


if __name__ == "__main__":
    main()
