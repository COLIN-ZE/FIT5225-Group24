import json
import os
from pathlib import Path

import requests


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


def is_duplicate_local(sha256: str) -> bool:
    """Check/register SHA-256 using a local JSON file (for test_local.py)."""
    seen = _load_local_cache()
    if sha256 in seen:
        return True
    seen.add(sha256)
    _save_local_cache(seen)
    return False


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


def is_duplicate(sha256: str, s3_uri: str = "") -> bool:
    """
    Use GCP API when GCP_DEDUP_URL is set; otherwise local JSON cache.
    """
    if os.environ.get("GCP_DEDUP_URL", "").strip():
        return check_duplicate_remote(sha256, s3_uri)
    return is_duplicate_local(sha256)
