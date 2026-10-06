"""Shared records and planned interfaces for the separate feature modules.

The functions below are documentation stubs, not working ZIP search functions.
Each names the module that will implement it. Import the real implementation
from that module when it lands, not from here. Sizes are uncompressed bytes.
"""

import os
from dataclasses import dataclass
from typing import BinaryIO, Iterator, Optional, Tuple, Union
from zipfile import ZipFile, ZipInfo

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
    them.
    """

    container_path: str
    inner_path: str
    size: int
    is_zip: bool
    is_dir: bool = False
    encrypted: bool = False


@dataclass(frozen=True)
class SearchHit:
    """Pair a matching Entry with optional content-search line details.

    Name-only hits leave line_number and line_text unset. Content line numbers
    start at 1. Keeping the Entry avoids copying its path and size fields.
    """

    entry: Entry
    line_number: Optional[int] = None
    line_text: Optional[str] = None


def iter_zip_entries(path: ZipSource) -> Iterator[Entry]:
    """Z3, zip_reader: list members, marking directories and encryption.

    When given a file object, use its name if available for container_path;
    otherwise use an empty string. The nested reader supplies the outer path.
    """
    raise NotImplementedError("Implemented by zipsearch.zip_reader in Z3")


def iter_nested(
    zip_file_obj: ZipFile,
    prefix: str,
    depth: int = 0,
    *,
    max_depth: int = 5,
    max_inner_zip_size: int = 100 * 1024 * 1024,
) -> Iterator[Entry]:
    """Z4, nested: list nested members with '!/' paths; depth 0 is outer ZIP.

    prefix is the display path of the current archive. Read inner ZIPs in
    memory
    and report a skip rather than recursing beyond either limit.
    """
    raise NotImplementedError("Implemented by zipsearch.nested in Z4")


def safe_open_zip(path_or_fileobj: ZipSource):
    """Z5, safe_open: return ZipFile or errors.Skipped(reason), never extract.

    The caller closes a successful ZipFile. Skipped is defined by Z5;
    encryption
    on individual entries is represented by Entry.encrypted, not a whole-file
    failure. The return annotation waits for that module to avoid a dependency.
    """
    raise NotImplementedError("Implemented by zipsearch.safe_open in Z5")


def is_safe_entry_name(name: str) -> bool:
    """Z6, safety: reject traversal, absolute, drive, backslash and NUL
    paths."""
    raise NotImplementedError("Implemented by zipsearch.safety in Z6")


def check_limits(
    info: ZipInfo,
    *,
    max_size: int = 100 * 1024 * 1024,
    max_ratio: float = 1000.0,
) -> Optional[str]:
    """Z6, safety: return a skip reason for unsafe sizes/ratios, else None."""
    raise NotImplementedError("Implemented by zipsearch.safety in Z6")


def search_stream(fileobj: BinaryIO, text: str) -> Iterator[Tuple[int, str]]:
    """Z8, content_search: yield (1-based line number, text) from a byte
    stream.

    Probe the first 8 KiB for NUL bytes, skip binary streams, then decode UTF-8
    with replacement for invalid bytes. The caller owns and closes the stream.
    """
    raise NotImplementedError("Implemented by zipsearch.content_search in Z8")


class NameMatcher:
    """Z7, matcher: planned interface; no filesystem or ZIP knowledge
    needed."""

    def __init__(
        self,
        pattern: str,
        mode: str = "substring",
        *,
        case_sensitive: bool = True,
        full_path: bool = False,
    ) -> None:
        """Choose substring/glob/regex, case rules and basename/full-path
        use."""
        raise NotImplementedError("Implemented by zipsearch.matcher in Z7")

    def matches(self, name: str) -> bool:
        """Return whether a file or member path matches the chosen pattern."""
        raise NotImplementedError("Implemented by zipsearch.matcher in Z7")
