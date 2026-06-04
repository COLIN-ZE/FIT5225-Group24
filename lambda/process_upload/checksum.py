import hashlib
from typing import BinaryIO


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 hex digest for a file on disk."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(body: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 from a readable stream (e.g. S3 GetObject Body)."""
    digest = hashlib.sha256()
    while True:
        chunk = body.read(chunk_size)
        if not chunk:
            break
        digest.update(chunk)
    return digest.hexdigest()
