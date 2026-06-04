#!/usr/bin/env bash
# Build deployment zip for AWS Lambda (request_upload).
# Mac: uses Docker (Amazon Linux) for pip; zip runs on your Mac.
set -euo pipefail
cd "$(dirname "$0")"

DIST=dist
ZIP="$DIST/request_upload.zip"
rm -rf build "$ZIP"
mkdir -p build "$DIST"

if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  echo "Installing Linux dependencies in Docker (linux/amd64)..."
  docker run --rm --platform linux/amd64 \
    --entrypoint /bin/bash \
    -v "$PWD:/src:ro" \
    -v "$PWD/build:/build" \
    public.ecr.aws/lambda/python:3.12 \
    -c '
      set -e
      rm -rf /build/*
      pip install -r /src/requirements.txt -t /build --quiet
      cp /src/handler.py /src/routes.py /src/auth_cognito.py /src/config.py /src/db.py /src/s3_service.py /build/
    '
else
  echo "WARNING: Docker not running. Using local pip (Mac zip will break on Lambda)."
  python3 -m pip install -r requirements.txt -t build/ --quiet
  cp handler.py routes.py auth_cognito.py config.py db.py s3_service.py build/
fi

echo "Creating zip..."
(cd build && zip -r9 "../$ZIP" . -x "*.pyc" -x "__pycache__/*")

echo "Created $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "Upload in Lambda → Code → Upload from .zip file"
