"""Business logic for upload API (shared by Lambda handler and local tests)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote

from auth_cognito import AuthError, user_id_from_claims, verify_bearer_token
from db import get_database
from s3_service import build_file_key, create_presigned_put_url

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
db = get_database()


def _ok(data: dict[str, Any] | None = None, message: str = "OK") -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


def _accepted(message: str = "Processing") -> dict[str, Any]:
    return {"code": 202, "message": message, "data": None}


def handle_request_upload(body: dict[str, Any], authorization: str | None) -> dict[str, Any]:
    claims = verify_bearer_token(authorization)
    user_id = user_id_from_claims(claims)

    filename = (body.get("filename") or "").strip()
    content_type = body.get("contentType") or ""
    file_hash = (body.get("fileHash") or "").lower()

    if not filename:
        raise ValueError("filename is required")
    if not SHA256_RE.match(file_hash):
        raise ValueError("fileHash must be SHA-256 hex")

    existing = db.get_hash_record(file_hash)
    if existing and existing.get("fileKey"):
        return _ok(
            {
                "exists": True,
                "fileKey": existing["fileKey"],
                "uploadUrl": None,
            },
            message="Duplicate file",
        )

    file_key = build_file_key(user_id, filename)
    upload_url = create_presigned_put_url(file_key, content_type)

    if not db.get_upload(file_key):
        db.put_upload(
            file_key,
            {
                "sha256": file_hash,
                "userId": user_id,
                "filename": filename,
                "contentType": content_type,
                "status": "awaiting_upload",
                "results": None,
                "videoResults": None,
            },
        )

    db.put_hash_record(
        file_hash,
        {"fileKey": file_key, "userId": user_id, "filename": filename},
    )

    return _ok(
        {"exists": False, "fileKey": file_key, "uploadUrl": upload_url}
    )


def handle_get_results(file_key: str, authorization: str | None) -> dict[str, Any]:
    verify_bearer_token(authorization)
    file_key = unquote(file_key)

    record = db.get_upload(file_key)
    if not record:
        raise LookupError("Unknown fileKey")

    status = record.get("status", "processing")
    if status in ("awaiting_upload", "processing", "pending"):
        return _accepted("Still processing")

    if record.get("results") is not None:
        return _ok({"results": record["results"]})
    if record.get("videoResults") is not None:
        return _ok({"results": record["videoResults"]})

    return _accepted("Still processing")


def handle_mark_processing(file_key: str) -> dict[str, Any]:
    file_key = unquote(file_key)
    if not db.get_upload(file_key):
        raise LookupError("Unknown fileKey")
    db.update_upload(file_key, {"status": "processing"})
    return _ok({"fileKey": file_key, "status": "processing"})


def handle_store_results(file_key: str, body: dict[str, Any]) -> dict[str, Any]:
    file_key = unquote(file_key)
    if not db.get_upload(file_key):
        raise LookupError("Unknown fileKey")

    patch: dict[str, Any] = {"status": body.get("status", "done")}
    if body.get("results") is not None:
        patch["results"] = body["results"]
    if body.get("videoResults") is not None:
        patch["videoResults"] = body["videoResults"]

    db.update_upload(file_key, patch)
    return _ok({"fileKey": file_key, "status": patch["status"]})
