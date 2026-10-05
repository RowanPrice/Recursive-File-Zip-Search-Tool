"""List what is inside a ZIP file without extracting anything to disk."""

import os
from typing import Iterator
from zipfile import ZipFile, is_zipfile

from zipsearch.models import Entry, ZipSource


def is_zip(path: str) -> bool:
    """Return True if path looks like a real ZIP file.

    Two checks must both pass: the name ends in .zip (any capitalisation),
    and zipfile.is_zipfile confirms the bytes really are a ZIP archive.
    """
    # lower() makes the extension check case-insensitive (.ZIP, .Zip ...).
    if not str(path).lower().endswith(".zip"):
        return False
    # is_zipfile only peeks at the file, so it is cheap and never raises
    # for a missing or unreadable file (it just returns False).
    return is_zipfile(path)


def iter_zip_entries(path: ZipSource) -> Iterator[Entry]:
    """Yield one Entry for every member (file or folder) inside a ZIP.

    path may be a file path or an open binary file object. Nothing is
    extracted or read: only the ZIP's table of contents is used.
    A bad ZIP raises zipfile.BadZipFile; later steps decide how to skip it.
    """
    if isinstance(path, (str, os.PathLike)):
        container = os.fspath(path)
    else:
        # A file object may or may not have a name. Use "" when it does not.
        name = getattr(path, "name", "")
        container = name if isinstance(name, str) else ""

    # "with" closes the ZIP for us, even if something goes wrong.
    with ZipFile(path) as archive:
        for info in archive.infolist():
            is_dir = info.is_dir()
            yield Entry(
                container_path=container,
                inner_path=info.filename,
                size=info.file_size,  # uncompressed size in bytes
                # Hint only: a nested archive is a non-folder ending in .zip.
                is_zip=(not is_dir) and info.filename.lower().endswith(".zip"),
                is_dir=is_dir,
                # Bit 0 of flag_bits is set when the member is password-protected.
                encrypted=bool(info.flag_bits & 0x1),
            )
