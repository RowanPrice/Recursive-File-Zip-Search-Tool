"""Walk ordinary folders without opening or extracting any archives."""

import os
from typing import Iterator, List, Tuple, Union

Path = Union[str, os.PathLike]
Directory = Tuple[str, List[str], List[str]]


def walk_directories(root: Path) -> Iterator[Directory]:
    """Yield (folder, subfolder names, file names), just like os.walk.

    Keep the operating system's order, ignore inaccessible folders by default,
    and do not follow directory symlinks. This view preserves the original
    CLI's
    directory headings, including empty folders.
    """
    yield from os.walk(root)


def walk(root: Path) -> Iterator[str]:
    """Yield each file's path lazily, including ZIPs as ordinary files for now.

    A generator produces one item at a time rather than building a big list.
    Paths keep the caller's relative/absolute form; they are not resolved.
    """
    for folder, _directories, files in walk_directories(root):
        for name in files:
            yield os.path.join(folder, name)
