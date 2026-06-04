"""Business logic for upload API (shared by Lambda handler and local tests)."""

from __future__ import annotations

import re
from typing import Any

from auth_cognito import user_id_from_claims, verify_bearer_token
from db import get_database
from s3_service import build_file_key, create_presigned_put_url

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
db = get_database()


def _ok(data: dict[str, Any] | None = None, message: str = "OK") -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


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

    db.put_hash_record(
        file_hash,
        {
            "fileKey": file_key,
            "userId": user_id,
            "filename": filename,
            "contentType": content_type,
        },
    )

    return _ok(
        {"exists": False, "fileKey": file_key, "uploadUrl": upload_url}
    )
