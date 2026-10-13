"""Walk ordinary folders without opening or extracting any archives."""

import logging
import os
from typing import Iterator, List, Optional, Tuple, Union

from zipsearch.logging_setup import log_errors

Path = Union[str, os.PathLike]
Directory = Tuple[str, List[str], List[str]]


@log_errors
def walk_directories(root: Path) -> Iterator[Directory]:
    """Yield (folder, subfolder names, file names), just like os.walk.

    Keep the operating system's order, log inaccessible folders and continue,
    and do not follow directory symlinks. This view preserves the original
    CLI's
    directory headings, including empty folders.
    """
    def report_error(error):
        logging.getLogger(__name__).error(
            "Cannot access folder %s: %s", error.filename, error
        )

    yield from os.walk(root, onerror=report_error)


@log_errors
def walk(root: Path) -> Iterator[str]:
    """Yield each file's path lazily, including ZIPs as ordinary files for now.

    A generator produces one item at a time rather than building a big list.
    Paths keep the caller's relative/absolute form; they are not resolved.
    """
    for folder, _directories, files in walk_directories(root):
        for name in files:
            yield os.path.join(folder, name)


def root_problem(root: Path) -> Optional[str]:
    """Return a short reason the root folder cannot be searched, else None.

    main.py uses this to stop with a clear, helpful message instead of a
    traceback. A missing path, a plain file and an unreadable folder each
    get their own reason. Readability is checked by really opening the
    folder listing, because permission rules differ between systems.
    """
    path = os.fspath(root)
    if not os.path.exists(path):
        return "the folder does not exist"
    if not os.path.isdir(path):
        return "it is a file, not a folder"
    try:
        # Opening the listing is the only reliable permission check.
        with os.scandir(path) as entries:
            for _entry in entries:
                break
    except PermissionError:
        return "permission denied"
    except OSError as error:
        return str(error)
    return None
