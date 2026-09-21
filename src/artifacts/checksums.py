"""Cross-platform verification helpers for immutable artifact manifests.

The frozen R5-R8 manifests predate Linux deployment and record Windows text
bytes, including a small number of mixed-line-ending artifacts. Git may check
those same tracked UTF-8 files out with LF on Linux. Verification therefore
accepts only the explicitly pinned normalized content digests corresponding to
those pre-existing manifest entries. Binary artifacts are always hashed
literally.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


_CROSS_PLATFORM_TEXT_SUFFIXES = frozenset({".csv", ".json", ".md"})

# Expected manifest digest -> pinned LF-normalized content digest. This is a
# deliberately finite compatibility bridge for the frozen Windows-generated
# R5-R7 artifacts; it is not a general EOL bypass.
_LEGACY_TEXT_MANIFEST_DIGESTS = {
    "17ae8da4936dd11aa1bbd1a189d4409791d53d7c4d3c098b127bd5fe617a0b6e": "37ab8f66c09206fb94aeacb27d72f421f7023ef6a82fce64cdc51d329bab8df6",
    "fee11313bd86982f86f9d836adb4420758e8516b71d0f2be99b90c4e69a72887": "4bf902e6c30076038322faa53bddb5af7481e3e10d5d4a7b01bb92826fe5b647",
    "096e91e83b30902ba01da043262b8647b18610d42b58b806cb13cdcaa0ee47eb": "dd504d26205345d191b2c6f366dfdbddd6d8fb16c72c31f5c49d0ed86e7516af",
    "c86a0ce1b21919b0a4f4fed5e4b8d0cc0560e4846d8f2bfa6e44f3b1395a7fe0": "13d7ef238d799c997f47b21b5097a32160cc81e4207fbcbf949953ea30bf3abf",
    "6d40b841fe681d19e1c23efda0744b0e1523589bfccef035654e663715939d77": "0b7002ccc440634cd8c9444adc359feb300892f90b44152fc07f02f481da5b00",
    "97888b7cbb655d542a4a3cafc42bdfe1d65e267d95cc8e84f125d2a4003fff27": "4934e2ec8b5938ffb1c02c7b01d7d379b662fa3c6d968bcc4e2c997e9279a3bc",
    "3ea53c0a65286069d762602d88d14aed02f77e446f1d4302a08c6b4c2fcd4be7": "6fc37f16870e0301c89cbb624a4b9bb0b289e5664bf34c0f0ff75fcb662b515f",
    "2dcae202f2c763b9cfd04957e9bb3832bf2d827b6f97f869838f632353248dd1": "3dd94e4e936ffe432c82eed8e6bfad5cfdfc8be1d0eb6da3197ed18137bf3438",
    "693dccbc1a3d42699a1c07f97ffbddec5e9b0d571b2e7c302b84512f13590d59": "5f171130854d2dc026deff09078a7e3df0247ec9b4bab3557027f50c0e5ad58a",
    "07fce6e8f0feb2e095de94a7db3890f6e720ad4d73204058e620099e485bed9b": "e48a37a05a4aca378a891107b78fd84b70ecc6b584b043b725ddea64556cdd24",
    "91f3bb98cf0b3efb6f85ae982e196cb89e3a6b1a6f542a9d0e95911dc7aa7f41": "1d300e23949f3fca39103cd5b862e6d2675c2b586d001ad513649ee87a709eba",
    "4d90ced2a3650a05e42873946bb19034f59207cdf2825780ad6b3a05b2f9178e": "7ff17de6a4eed9cfbe5e4920d2962f800cb59ff0b4570de108b0fc6ed21e3146",
    "ae2989dfa1d48da634c253190f4bbbc827ab40218f1201471e641f2081f4e195": "f6b349dce904825be4d12bb5a8fa0b3c3adad29be7d8e1b6f592def315c9991f",
    "83d04e2ca5f9da14eb4d46ffd301375d26c6b4ab91d91745f082c6f94a64908b": "38b938afe0f7cf80e9f52cc67f14ac832aa0506405d78d300f9937cf4a8d09de",
    "be902049508c9c2822f6b590acbb1b3acac2124e71815380c25c7ecf3cbcd259": "6e33ef1c81245488c8ef7d67517acade5d0c2501623514698557a8b3ab5e6463",
    "d5bebd82c4849654fa24d5df02fe161419f6be9a5d33fc76097931a6693832c4": "38339d971d3ff69b23d3ec07c6a876b35bc3467e0e1a8aa924d5a6ae817aa023",
    "b9bd30e465b5dd5493474e5f26718c6851b7280f17d3dff4f48ebe8dce239fa6": "b1050cff4f1a94b5d081f999ed350fe4fa86e0f510f5df71e80a5448cbbc2c5f",
    "4bb7ae9eedc61bae81c02138605a4ebea627862e3b11cc6656e2aab19ba9aaf9": "45f18ed3405c3fd7dda76996ce36413789eae827e3821a8bc6489e7a3e9ce8e9",
}


def sha256_file(path: Path) -> str:
    """Return the literal SHA-256 digest of a file's current bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest_digest_matches(path: Path, expected_digest: str) -> bool:
    """Match a frozen manifest without treating LF checkout conversion as tampering.

    A literal byte digest always wins. Known UTF-8 text artifact types may use
    only their pinned legacy normalized digest; pickle and every other binary
    file must match literally.
    """
    artifact = Path(path)
    if sha256_file(artifact) == expected_digest:
        return True
    if artifact.suffix.lower() not in _CROSS_PLATFORM_TEXT_SUFFIXES:
        return False
    normalized = artifact.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(normalized).hexdigest() == _LEGACY_TEXT_MANIFEST_DIGESTS.get(expected_digest)
