"""Reusable ZIP fixtures; every generated file lives in pytest's tmp_path."""

import base64
import io
from typing import Mapping, Union
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

Content = Union[str, bytes]


def zip_bytes(entries: Mapping[str, Content]) -> bytes:
    """Build an in-memory ZIP from member-name to text/bytes pairs.

    A name ending with '/' creates a directory entry. Bytes also allow an
    archive to contain another archive, without extracting anything to disk.
    """
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture
def make_zip(tmp_path):
    """Return a factory: make_zip(entries, name='plain.zip') -> Path."""
    def build(entries, name="plain.zip"):
        """Write a ZIP beneath this test's temporary directory."""
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(zip_bytes(entries))
        return path
    return build


@pytest.fixture
def make_nested_zip(make_zip):
    """Return a factory nesting entries inside ZIPs, levels including outer.

    levels=2 produces outer.zip!/inner1.zip!/file.txt. levels=3 adds
    inner2.zip.
    Names are predictable so tests can assert exact paths.
    """
    def build(entries=None, levels=2, name="outer.zip"):
        """Write a nested ZIP with at least two archive levels."""
        if levels < 2:
            raise ValueError("levels must be at least 2")
        members = {"file.txt": "hello\n"} if entries is None else entries
        data = zip_bytes(members)
        for level in range(levels - 1, 0, -1):
            if level == 1:
                return make_zip({"inner1.zip": data}, name=name)
            data = zip_bytes({"inner{}.zip".format(level): data})
    return build


@pytest.fixture
def make_corrupt_zip(tmp_path):
    """Return a factory for invalid bytes or a ZIP missing its end record."""
    def build(name="corrupt.zip", truncated=False):
        """Write a corrupt ZIP; truncated=True cuts off a real ZIP's tail."""
        data = zip_bytes({"file.txt": "hello"}) if truncated else b"not a zip"
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data[:-22] if truncated else data)
        return path
    return build


# zipfile can READ encrypted ZIPs but cannot WRITE them. This tiny, genuine
# ZipCrypto fixture was generated once using `zip -P scaffold-password`.
# Tests do not need that program installed. Member: secret.txt, bytes:
# secret\n.
_ENCRYPTED_ZIP = (
    "UEsDBAoACQAAABpQRV2MsuviEwAAAAcAAAAKABwAc2VjcmV0LnR4dFVUCQADRGfDakRn"
    "w2p1eAsAAQTpAwAABOkDAACH9MXrWKwJN1woa6UGVStdhjaAUEsHCIyy6+ITAAAABwAA"
    "AFBLAQIeAwoACQAAABpQRV2MsuviEwAAAAcAAAAKABgAAAAAAAEAAACkgQAAAABzZWNy"
    "ZXQudHh0VVQFAANEZ8NqdXgLAAEE6QMAAATpAwAAUEsFBgAAAAABAAEAUAAAAGcAAAAA"
    "AA=="
)


@pytest.fixture
def make_encrypted_zip(tmp_path):
    """Return a factory for a real password-protected ZIP with secret.txt.

    Its known test-only password is 'scaffold-password'. Reads without that
    password must fail, not silently return unencrypted contents.
    """
    def build(name="encrypted.zip"):
        """Write the embedded archive beneath this test's temporary folder."""
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(_ENCRYPTED_ZIP))
        return path
    return build


@pytest.fixture
def make_password_protected_zip(make_encrypted_zip):
    """Provide a descriptive alias for the encrypted ZIP factory."""
    return make_encrypted_zip
