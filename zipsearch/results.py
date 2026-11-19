"""Build metadata records for matched ordinary files and ZIP members."""

import logging
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from stat import S_ISDIR
from typing import Iterable, List, Optional, TypedDict

from zipsearch.logging_setup import log_errors
from zipsearch.categories import CategoryMatcher
from zipsearch.models import Entry, Path as FilePath


class Result(TypedDict):
    """One matched file, with every category kept in the same list.

    Field names double as the CSV column headers. Zipfile is an empty string
    for a normal file. LastModified is None when the source has no usable
    timestamp; otherwise it is an ISO8601 date/time string. FolderLocation
    is the containing folder for a normal file, or the folder path inside
    the ZIP for a member ('/' for a file at the ZIP's top level).
    """

    Category: List[str]
    Filename: str
    FolderLocation: str
    Zipfile: str
    FileSizeBytes: int
    LastModified: Optional[str]


def _file_entry(path: FilePath) -> Entry:
    """Worker shared by file_entry and safe_file_entry; see file_entry."""
    file = Path(path)
    metadata = file.stat()
    return Entry(
        container_path=str(file),
        inner_path="",
        size=metadata.st_size,
        is_zip=file.suffix.lower() == ".zip",
        is_dir=S_ISDIR(metadata.st_mode),
        last_modified=datetime.fromtimestamp(
            metadata.st_mtime, timezone.utc
        ).isoformat(),
    )


@log_errors
def file_entry(path: FilePath) -> Entry:
    """Read an ordinary file's size and modification time, without its contents.

    Paths stay relative or absolute as supplied, except pathlib normalizes
    redundant separators and './'. Missing/unreadable files raise OSError.
    The timestamp uses UTC (+00:00), not the machine's local timezone.
    Use safe_file_entry to log and skip unreadable files instead of raising.
    """
    return _file_entry(path)


def safe_file_entry(path: FilePath) -> Optional[Entry]:
    """Like file_entry, but an unreadable file is logged and skipped.

    A missing file, a permission problem or any other OS error produces one
    ERROR line with the file's path and the exact reason, and None is
    returned, so one bad file never stops the whole run.
    """
    try:
        return _file_entry(path)
    except OSError as error:
        logging.getLogger(__name__).error(
            "Skipping file '%s': %s: %s", path, type(error).__name__, error
        )
        return None


@log_errors
def build_results(entries: Iterable[Entry], matcher: CategoryMatcher) -> List[Result]:
    """Return one dict per matching file, containing all its category names.

    The caller supplies entries from file_entry or iter_zip_entries. This
    function does not walk folders, open ZIPs or read file contents. Unmatched
    files and directories are left out. Input order is kept.
    """
    results: List[Result] = []
    counts = dict.fromkeys(matcher.category_names, 0)
    for entry in entries:
        categories = matcher.match_entry(entry)
        if not categories:
            continue
        for category in categories:
            counts[category] += 1
        if entry.inner_path:
            # Member paths belong to the ZIP, not the operating system.
            path = PurePosixPath(entry.inner_path.replace("\\", "/"))
            archive = entry.container_path
            # A member at the ZIP's top level has no inner folder; show the
            # ZIP's root as '/' instead of pathlib's '.'.
            folder = str(path.parent) if str(path.parent) != "." else "/"
        else:
            path = Path(entry.container_path)
            archive = ""
            folder = str(path.parent)
        results.append({
            "Category": categories,
            "Filename": path.name,
            "FolderLocation": folder,
            "Zipfile": archive,
            "FileSizeBytes": entry.size,
            "LastModified": entry.last_modified,
        })
    logger = logging.getLogger(__name__)
    for category, count in counts.items():
        logger.info("Files matched in category %s: %d", category, count)
    return results
