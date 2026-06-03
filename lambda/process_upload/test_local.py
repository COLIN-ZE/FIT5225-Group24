#!/usr/bin/env python3
"""
Run the upload pipeline on your machine (no AWS Lambda required).

  cd lambda/process_upload
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python test_local.py
  python test_local.py ../../test_images/Canis_familiaris_1.JPG
  python test_local.py ../../test_images/Canis_familiaris_1.JPG   # run twice -> duplicate
"""

import sys
from pathlib import Path

from handler import process_file

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IMAGE = ROOT / "test_images" / "Canis_familiaris_1.JPG"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def main() -> None:
    if len(sys.argv) > 1:
        target = Path(sys.argv[1]).expanduser().resolve()
    else:
        target = DEFAULT_IMAGE

    if not target.is_file():
        print(f"File not found: {target}")
        print("Usage: python test_local.py [path/to/image-or-video]")
        sys.exit(1)

    print(f"Processing: {target}")
    print(f"Output dir: {OUTPUT_DIR}\n")

    result = process_file(local_path=str(target), output_dir=OUTPUT_DIR)
    print("\nDone.")
    if result["status"] == "processed" and result.get("thumbnail_uri"):
        print(f"Thumbnail: {result['thumbnail_uri']}")
    if result["status"] == "processed" and result.get("ai_ready_uris"):
        print(f"ai-ready: {len(result['ai_ready_uris'])} file(s)")
    if result["status"] == "duplicate":
        print(f"rejected: {result.get('rejected_uri')}")


if __name__ == "__main__":
    main()
