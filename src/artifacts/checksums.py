"""Cross-platform verification helpers for immutable artifact manifests.

The frozen R5-R8 manifests predate Linux deployment and record CRLF text
artifact bytes.  Git may check those same UTF-8 text files out with LF on a
Linux host.  Verification therefore accepts the manifest digest of either the
literal working-tree bytes or the deterministic CRLF rendering of a known text
artifact.  Binary artifacts are always hashed literally.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


_CROSS_PLATFORM_TEXT_SUFFIXES = frozenset({".csv", ".json", ".md"})


def sha256_file(path: Path) -> str:
    """Return the literal SHA-256 digest of a file's current bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest_digest_matches(path: Path, expected_digest: str) -> bool:
    """Match a frozen manifest without treating LF checkout conversion as tampering.

    A literal byte digest always wins.  Only known UTF-8 text artifact types
    receive the legacy CRLF compatibility check; pickle and every other binary
    file must match their literal bytes exactly.
    """
    artifact = Path(path)
    if sha256_file(artifact) == expected_digest:
        return True
    if artifact.suffix.lower() not in _CROSS_PLATFORM_TEXT_SUFFIXES:
        return False
    data = artifact.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    canonical_crlf = data.replace(b"\n", b"\r\n")
    return hashlib.sha256(canonical_crlf).hexdigest() == expected_digest
