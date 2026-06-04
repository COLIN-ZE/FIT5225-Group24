#!/usr/bin/env python3
"""
Simulate API Gateway events locally.

  export USE_LOCAL_DB=true
  export S3_BUCKET_NAME=your-bucket
  export COGNITO_USER_POOL_ID=...
  export COGNITO_CLIENT_ID=...
  python test_local.py request   # needs a real Bearer token in TOKEN env
"""

import json
import os
import sys

from handler import lambda_handler


def _event(method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "headers": headers,
        "body": json.dumps(body) if body else None,
    }


def main():
    token = os.environ.get("TOKEN", "")
    if not token:
        print("Set TOKEN=<Cognito id_token> to test /requestUploadFile")
        print("Or run: python test_local.py health")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "health"

    if cmd == "health":
        ev = _event("GET", "/health")
    elif cmd == "request":
        ev = _event(
            "POST",
            "/requestUploadFile",
            {
                "filename": "test.jpg",
                "contentType": "image/jpeg",
                "fileHash": "e0c529de81cd0963b78ff1c1fb895acbbde5231212bc49173606c85cda3d2d4b",
            },
            token=token,
        )
    else:
        print("Usage: python test_local.py [health|request]")
        sys.exit(1)

    resp = lambda_handler(ev, None)
    print(json.dumps(resp, indent=2))
    if resp.get("body"):
        print(json.dumps(json.loads(resp["body"]), indent=2))


if __name__ == "__main__":
    main()
