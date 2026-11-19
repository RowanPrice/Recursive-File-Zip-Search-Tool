"""Shared records and path types used by the separate feature modules.

Sizes are uncompressed bytes.
"""

import os
from dataclasses import dataclass
from typing import BinaryIO, Optional, Union

Path = Union[str, os.PathLike]
ZipSource = Union[Path, BinaryIO]


@dataclass(frozen=True)
class Entry:
    """Describe one file or directory without loading its contents.

    container_path is the on-disk file/ZIP path. inner_path is empty for a
    plain
    file, otherwise the member path (nested levels use '!/'). is_zip is a hint
    that the entry is an archive; a reader must still validate the bytes.
    Directory and encrypted flags let later readers list but avoid reading
    them. last_modified is ISO8601: UTC for filesystem files, but ZIP
    timestamps have no timezone. None means the timestamp is unavailable.
    """

    container_path: str
    inner_path: str
    size: int
    is_zip: bool
    is_dir: bool = False
    encrypted: bool = False
    last_modified: Optional[str] = None
