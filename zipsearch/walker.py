"""Walk ordinary folders without opening or extracting any archives."""

import logging
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

from zipsearch.logging_setup import log_errors

PathLike = Union[str, Path]
Directory = Tuple[str, List[str], List[str]]


def _list_folder(folder: Path) -> Tuple[List[str], List[str]]:
    """Split one folder's entries into subfolder names and file names.

    A symlink to a folder counts as a subfolder name here; the caller decides
    whether to recurse into it. Raises OSError (such as PermissionError) when
    the folder cannot be listed, like os.walk's scandir does.
    """
    subfolders = []
    files = []
    for entry in folder.iterdir():
        if entry.is_dir():
            subfolders.append(entry.name)
        else:
            files.append(entry.name)
    return subfolders, files


@log_errors
def walk_directories(root: PathLike) -> Iterator[Directory]:
    """Yield (folder, subfolder names, file names), just like os.walk.

    Keep the operating system's order, log inaccessible folders and continue,
    and do not follow directory symlinks. This view preserves the original
    CLI's directory headings, including empty folders.
    """
    def report_error(error):
        logging.getLogger(__name__).error(
            "Cannot access folder %s: %s", error.filename, error
        )

    def visit(folder: Path) -> Iterator[Directory]:
        try:
            subfolders, files = _list_folder(folder)
        except OSError as error:
            report_error(error)
            return
        yield str(folder), subfolders, files
        for name in subfolders:
            child = folder / name
            # os.walk's followlinks=False: name a folder symlink but never
            # recurse through it, so loops cannot hang the walk.
            if not child.is_symlink():
                yield from visit(child)

    yield from visit(Path(root))


@log_errors
def walk(root: PathLike) -> Iterator[str]:
    """Yield each file's path lazily, including ZIPs as ordinary files for now.

    A generator produces one item at a time rather than building a big list.
    Paths keep the caller's relative/absolute form; they are not resolved.
    """
    for folder, _directories, files in walk_directories(root):
        for name in files:
            yield str(Path(folder) / name)


def root_problem(root: PathLike) -> Optional[str]:
    """Return a short reason the root folder cannot be searched, else None.

    main.py uses this to stop with a clear, helpful message instead of a
    traceback. A missing path, a plain file and an unreadable folder each
    get their own reason. Readability is checked by really opening the
    folder listing, because permission rules differ between systems.
    """
    path = Path(root)
    if not path.exists():
        return "the folder does not exist"
    if not path.is_dir():
        return "it is a file, not a folder"
    try:
        # Opening the listing is the only reliable permission check.
        for _entry in path.iterdir():
            break
    except PermissionError:
        return "permission denied"
    except OSError as error:
        return str(error)
    return None
