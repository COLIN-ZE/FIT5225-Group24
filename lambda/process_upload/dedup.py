import json
import os
from pathlib import Path

import requests

from botocore.exceptions import ClientError


def _local_dedup_path() -> Path:
    """Writable path: /tmp on Lambda; output/ for local test_local.py."""
    override = os.environ.get("DEDUP_CACHE_PATH", "").strip()
    if override:
        return Path(override)
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/.dedup_cache.json")
    return Path(__file__).resolve().parent / "output" / ".dedup_cache.json"


def _load_local_cache() -> set[str]:
    path = _local_dedup_path()
    if not path.exists():
        return set()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("hashes", []))


def _save_local_cache(hashes: set[str]) -> None:
    path = _local_dedup_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"hashes": sorted(hashes)}, f, indent=2)


def has_seen_hash(sha256: str) -> bool:
    """True if this content hash was successfully processed before."""
    return sha256 in _load_local_cache()


def register_hash(sha256: str) -> None:
    """Call only after thumb/ai-ready upload succeeds."""
    seen = _load_local_cache()
    seen.add(sha256)
    _save_local_cache(seen)


def check_duplicate_remote(sha256: str, s3_uri: str) -> bool:
    """
    Ask teammate C's GCP API whether this checksum already exists in Firestore.
    Expects JSON: {"duplicate": true|false}.
    Set env GCP_DEDUP_URL (e.g. https://xxx.run.app/dedup).
    """
    url = os.environ.get("GCP_DEDUP_URL", "").strip()
    if not url:
        raise ValueError("GCP_DEDUP_URL is not set")

    resp = requests.post(
        url,
        json={"sha256": sha256, "s3_uri": s3_uri},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return bool(data.get("duplicate"))


def is_content_duplicate(sha256: str, s3_uri: str = "") -> bool:
    """
    True when this file content was already processed (local cache or GCP dedup API).
    Does not register the hash — call register_hash() after a successful run.
    """
    if os.environ.get("GCP_DEDUP_URL", "").strip():
        return check_duplicate_remote(sha256, s3_uri)
    return has_seen_hash(sha256)


def s3_object_exists(s3_client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise
