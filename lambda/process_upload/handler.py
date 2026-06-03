"""
Member B: S3 upload processor.

S3 layout (bucket aussie-ecolens-media-storage-2026):
  raw/        — frontend uploads (presigned PUT)
  thumb/      — 400px previews for UI
  ai-ready/   — 1080p-standardized stills / video frames for GCP ML
  rejected/   — duplicate uploads
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.parse
from pathlib import Path

import boto3

from checksum import sha256_file, sha256_stream
from dedup import is_duplicate
from media import (
    create_ai_ready_image,
    create_thumbnail,
    create_video_thumbnail,
    extract_frames_per_second_1080p,
    file_kind,
)

s3 = boto3.client("s3")

RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/")
THUMB_PREFIX = os.environ.get("THUMB_PREFIX", "thumb/")
AI_READY_PREFIX = os.environ.get("AI_READY_PREFIX", "ai-ready/")
REJECTED_PREFIX = os.environ.get("REJECTED_PREFIX", "rejected/")


def _rel_from_raw(object_key: str) -> str:
    if not object_key.startswith(RAW_PREFIX):
        raise ValueError(f"Not under {RAW_PREFIX}: {object_key}")
    return object_key[len(RAW_PREFIX) :]


def _thumb_key(object_key: str) -> str:
    rel = _rel_from_raw(object_key)
    p = Path(rel)
    return f"{THUMB_PREFIX}{p.parent / (p.stem + '_thumb.jpg')}".replace("\\", "/")


def _ai_ready_image_key(object_key: str) -> str:
    rel = _rel_from_raw(object_key)
    p = Path(rel)
    return f"{AI_READY_PREFIX}{p.parent / (p.stem + '.jpg')}".replace("\\", "/")


def _ai_ready_video_prefix(object_key: str) -> str:
    rel = _rel_from_raw(object_key)
    p = Path(rel)
    return f"{AI_READY_PREFIX}{p.parent / p.stem}/".replace("\\", "/")


def _rejected_key(object_key: str) -> str:
    rel = _rel_from_raw(object_key)
    return f"{REJECTED_PREFIX}{rel}".replace("\\", "/")


def _move_to_rejected(bucket: str | None, key: str | None, local_path: str | None) -> str:
    if bucket and key:
        dest = _rejected_key(key)
        s3.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": key},
            Key=dest,
        )
        s3.delete_object(Bucket=bucket, Key=key)
        return f"s3://{bucket}/{dest}"
    if local_path:
        src = Path(local_path)
        dest = Path(__file__).parent / "output" / "rejected" / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return str(dest.resolve())
    return ""


def notify_gcp(payload: dict) -> None:
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
        pseudo_key = f"{RAW_PREFIX}local/{path.name}"
    elif bucket and key:
        digest_obj = s3.get_object(Bucket=bucket, Key=key)
        digest = sha256_stream(digest_obj["Body"])
        s3_uri = f"s3://{bucket}/{key}"
        work_path = f"/tmp/{Path(key).name}"
        s3.download_file(bucket, key, work_path)
        kind = file_kind(key)
        out_root = Path("/tmp/out")
        out_root.mkdir(parents=True, exist_ok=True)
        pseudo_key = key
    else:
        raise ValueError("Provide local_path or (bucket, key)")

    file_key_for_status = key if bucket and key else None

    if is_duplicate(digest, s3_uri):
        rejected_uri = _move_to_rejected(bucket, key, local_path)
        result = {
            "status": "duplicate",
            "sha256": digest,
            "s3_uri": s3_uri,
            "rejected_uri": rejected_uri,
        }
        print(json.dumps(result, indent=2))
        return result

    thumb_uri = None
    ai_ready_uris: list[str] = []

    if kind == "image":
        thumb_dest = out_root / "thumb" / f"{Path(work_path).stem}_thumb.jpg"
        ai_dest = out_root / "ai-ready" / f"{Path(work_path).stem}.jpg"
        create_thumbnail(work_path, thumb_dest)
        create_ai_ready_image(work_path, ai_dest)
        if bucket and key:
            tk = _thumb_key(key)
            ak = _ai_ready_image_key(key)
            s3.upload_file(str(thumb_dest), bucket, tk)
            s3.upload_file(str(ai_dest), bucket, ak)
            thumb_uri = f"s3://{bucket}/{tk}"
            ai_ready_uris = [f"s3://{bucket}/{ak}"]
        else:
            thumb_uri = str(thumb_dest.resolve())
            ai_ready_uris = [str(ai_dest.resolve())]

    elif kind == "video":
        thumb_dest = out_root / "thumb" / f"{Path(work_path).stem}_thumb.jpg"
        create_video_thumbnail(work_path, thumb_dest)
        frames_dir = out_root / "ai-ready" / Path(work_path).stem
        frame_paths = extract_frames_per_second_1080p(work_path, frames_dir)
        if bucket and key:
            tk = _thumb_key(key)
            s3.upload_file(str(thumb_dest), bucket, tk)
            thumb_uri = f"s3://{bucket}/{tk}"
            prefix = _ai_ready_video_prefix(key)
            for fp in frame_paths:
                fname = Path(fp).name
                fk = f"{prefix}{fname}"
                s3.upload_file(fp, bucket, fk)
                ai_ready_uris.append(f"s3://{bucket}/{fk}")
        else:
            thumb_uri = str(thumb_dest.resolve())
            ai_ready_uris = [str(Path(p).resolve()) for p in frame_paths]

    else:
        raise ValueError(f"Unsupported file type: {work_path}")

    result = {
        "status": "processed",
        "sha256": digest,
        "s3_uri": s3_uri,
        "fileKey": file_key_for_status or pseudo_key,
        "media_type": kind,
        "thumbnail_uri": thumb_uri,
        "ai_ready_uris": ai_ready_uris,
    }

    notify_gcp(result)
    print(json.dumps(result, indent=2))
    return result


def lambda_handler(event, context):
    records = event.get("Records", [])
    if not records:
        return {"statusCode": 400, "body": "No S3 records"}

    results = []
    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        if not key.startswith(RAW_PREFIX):
            print(f"Skip non-raw key: {key}")
            continue
        results.append(process_file(bucket=bucket, key=key))

    return {"statusCode": 200, "body": json.dumps(results)}
