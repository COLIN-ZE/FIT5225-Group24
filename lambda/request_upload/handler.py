"""
Member B — Upload API Lambda (API Gateway → Lambda).

Routes (match frontend upload.js):
  POST /requestUploadFile
  GET  /health

Handler: handler.lambda_handler
"""

from __future__ import annotations

import json
from typing import Any

from auth_cognito import AuthError
from config import CORS_ORIGIN, S3_BUCKET_NAME
from routes import handle_request_upload


def _http_method(event: dict[str, Any]) -> str:
    if "httpMethod" in event:
        return event["httpMethod"].upper()
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "GET")
        .upper()
    )


def _path(event: dict[str, Any]) -> str:
    path = event.get("rawPath") or event.get("path") or "/"
    stage = event.get("requestContext", {}).get("stage")
    if stage and path.startswith(f"/{stage}"):
        path = path[len(stage) + 1 :] or "/"
    return path


def _headers(event: dict[str, Any]) -> dict[str, str]:
    raw = event.get("headers") or {}
    return {k.lower(): v for k, v in raw.items()}


def _body_json(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8")
    if not body:
        return {}
    return json.loads(body)


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": CORS_ORIGIN,
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(payload),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = _http_method(event)
    path = _path(event)
    headers = _headers(event)

    if method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        if method == "GET" and path == "/health":
            return _response(
                200, {"status": "ok", "s3_configured": bool(S3_BUCKET_NAME)}
            )

        if method == "POST" and path == "/requestUploadFile":
            payload = handle_request_upload(
                _body_json(event), headers.get("authorization")
            )
            return _response(200, payload)

        return _response(404, {"code": 404, "message": "Not found", "data": None})

    except AuthError as exc:
        return _response(
            exc.status_code,
            {"code": exc.status_code, "message": str(exc), "data": None},
        )
    except ValueError as exc:
        return _response(400, {"code": 400, "message": str(exc), "data": None})
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}")
        return _response(
            500, {"code": 500, "message": "Internal server error", "data": None}
        )
