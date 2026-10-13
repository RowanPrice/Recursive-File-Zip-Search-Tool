"""Walk ordinary folders without opening or extracting any archives."""

import logging
import os
from typing import Iterator, List, Tuple, Union

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
