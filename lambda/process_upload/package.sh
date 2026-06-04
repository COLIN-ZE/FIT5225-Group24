#!/usr/bin/env bash
# Build deployment zip for AWS Lambda (process_upload). OpenCV comes from a Layer, not this zip.
set -euo pipefail
cd "$(dirname "$0")"

DIST=dist
ZIP="$DIST/process_upload.zip"
rm -rf "$DIST" build
mkdir -p build "$DIST"

python3 -m pip install requests -t build/ --quiet

cp handler.py checksum.py media.py dedup.py build/

cd build
zip -r9 "../$ZIP" . -x "*.pyc" -x "__pycache__/*"
cd ..

echo "Created $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "Also attach opencv-python-headless Lambda Layer (see build_opencv_layer.sh)"
