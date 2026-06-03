"""
Member B: S3 upload processor (local dev + AWS Lambda entry point).

Local:  python test_local.py [path/to/file]
Lambda: set handler to handler.lambda_handler
"""

from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path

import boto3

from checksum import sha256_file, sha256_stream
from dedup import is_duplicate
from media import create_thumbnail, extract_frames_per_second, file_kind

s3 = boto3.client("s3")

THUMB_PREFIX = os.environ.get("THUMB_PREFIX", "thumb/")
FRAMES_PREFIX = os.environ.get("FRAMES_PREFIX", "frames/")


def _thumb_key(object_key: str) -> str:
    base = Path(object_key).name
    stem = Path(base).stem
    return f"{THUMB_PREFIX}{stem}_thumb.jpg"


def _frames_prefix(object_key: str) -> str:
    stem = Path(object_key).stem
    return f"{FRAMES_PREFIX}{stem}/"


def notify_upload_api_status(file_key: str, status: str = "processing") -> None:
    """Tell request_upload Lambda (API Gateway URL) that processing started."""
    base = os.environ.get("UPLOAD_API_URL", "").strip().rstrip("/")
    if not base or not file_key.startswith(os.environ.get("RAW_PREFIX", "raw/")):
        return
    import requests

    try:
        requests.post(
            f"{base}/internal/uploads/{file_key}/status",
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[notify_upload_api_status] {exc}")


def notify_gcp(payload: dict) -> None:
    """POST processing result to teammate C (optional until URL is ready)."""
    url = os.environ.get("GCP_CALLBACK_URL", "").strip()
    if not url:
        print("[notify_gcp] GCP_CALLBACK_URL not set, skipping:", json.dumps(payload))
        return
    import requests

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    print("[notify_gcp] OK", resp.status_code)


def process_file(
    *,
    local_path: str | None = None,
    bucket: str | None = None,
    key: str | None = None,
    output_dir: str | Path | None = None,
) -> dict:
    """
    Core pipeline: checksum -> dedup -> thumbnail or frames -> notify GCP.

    Local mode: pass local_path + output_dir (writes under output/).
    S3 mode:    pass bucket + key (reads/writes S3).
    """
    if local_path:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(local_path)
        digest = sha256_file(path)
        s3_uri = f"file://{path.resolve()}"
        work_path = str(path)
        kind = file_kind(path)
        out_root = Path(output_dir or Path(__file__).parent / "output")
        out_root.mkdir(parents=True, exist_ok=True)
    elif bucket and key:
        digest_obj = s3.get_object(Bucket=bucket, Key=key)
        digest = sha256_stream(digest_obj["Body"])
        s3_uri = f"s3://{bucket}/{key}"
        work_path = f"/tmp/{Path(key).name}"
        s3.download_file(bucket, key, work_path)
        kind = file_kind(key)
        out_root = Path("/tmp/out")
        out_root.mkdir(parents=True, exist_ok=True)
    else:
        raise ValueError("Provide local_path or (bucket, key)")

    file_key_for_status = key if bucket and key else None

    if is_duplicate(digest, s3_uri):
        result = {
            "status": "duplicate",
            "sha256": digest,
            "s3_uri": s3_uri,
        }
        print(json.dumps(result, indent=2))
        return result

    if file_key_for_status:
        notify_upload_api_status(file_key_for_status, "processing")

    thumb_uri = None
    frame_uris: list[str] = []

    if kind == "image":
        thumb_dest = out_root / "thumb" / f"{Path(work_path).stem}_thumb.jpg"
        create_thumbnail(work_path, thumb_dest)
        if bucket and key:
            thumb_key = _thumb_key(key)
            s3.upload_file(str(thumb_dest), bucket, thumb_key)
            thumb_uri = f"s3://{bucket}/{thumb_key}"
        else:
            thumb_uri = str(thumb_dest.resolve())

    elif kind == "video":
        frames_dir = out_root / "frames" / Path(work_path).stem
        frame_paths = extract_frames_per_second(work_path, frames_dir)
        if bucket and key:
            prefix = _frames_prefix(key)
            for fp in frame_paths:
                fname = Path(fp).name
                fk = f"{prefix}{fname}"
                s3.upload_file(fp, bucket, fk)
                frame_uris.append(f"s3://{bucket}/{fk}")
        else:
            frame_uris = [str(Path(p).resolve()) for p in frame_paths]

    else:
        raise ValueError(f"Unsupported file type: {work_path}")

    result = {
        "status": "processed",
        "sha256": digest,
        "s3_uri": s3_uri,
        "fileKey": file_key_for_status,
        "media_type": kind,
        "thumbnail_uri": thumb_uri,
        "frame_uris": frame_uris,
    }

    notify_gcp(result)
    print(json.dumps(result, indent=2))
    return result


def lambda_handler(event, context):
    """AWS Lambda entry: S3 ObjectCreated notification."""
    records = event.get("Records", [])
    if not records:
        return {"statusCode": 400, "body": "No S3 records"}

    results = []
    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        if not key.startswith(os.environ.get("RAW_PREFIX", "raw/")):
            print(f"Skip non-raw key: {key}")
            continue
        results.append(process_file(bucket=bucket, key=key))

    return {"statusCode": 200, "body": json.dumps(results)}
