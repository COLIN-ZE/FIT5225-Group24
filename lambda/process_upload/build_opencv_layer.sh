#!/usr/bin/env bash
# Build OpenCV Lambda Layer using Amazon Linux (Docker required).
set -euo pipefail
cd "$(dirname "$0")"

DIST=dist
ZIP="$DIST/opencv-layer.zip"
rm -rf "$DIST/layer" "$ZIP"
mkdir -p "$DIST"

echo "Building OpenCV layer in Docker (may take a few minutes)..."

docker run --rm --platform linux/amd64 \
  --entrypoint /bin/bash \
  -v "$PWD/$DIST/layer:/out" \
  public.ecr.aws/lambda/python:3.12 \
  -c "pip install opencv-python-headless -t /out/python/lib/python3.12/site-packages && chmod -R a+rX /out"

cd "$DIST/layer"
zip -r9 "../opencv-layer.zip" python
cd ../..

echo "Created $ZIP"
echo "Lambda console → Layers → Create layer → upload this zip → Python 3.12, x86_64"
