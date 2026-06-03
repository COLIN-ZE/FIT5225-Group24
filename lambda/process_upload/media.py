import os
from pathlib import Path

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

THUMB_MAX_EDGE = 256
THUMB_JPEG_QUALITY = 85


def file_kind(path: str | Path) -> str:
    """Return 'image', 'video', or 'unknown'."""
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def create_thumbnail(
    source_path: str | Path,
    dest_path: str | Path,
    max_edge: int = THUMB_MAX_EDGE,
) -> None:
    """Resize image keeping aspect ratio; write JPEG to dest_path."""
    img = cv2.imread(str(source_path))
    if img is None:
        raise ValueError(f"Could not read image: {source_path}")

    height, width = img.shape[:2]
    scale = max_edge / max(height, width)
    if scale >= 1.0:
        thumb = img
    else:
        new_w = max(1, int(width * scale))
        new_h = max(1, int(height * scale))
        thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(
        str(dest),
        thumb,
        [int(cv2.IMWRITE_JPEG_QUALITY), THUMB_JPEG_QUALITY],
    )
    if not ok:
        raise RuntimeError(f"Failed to write thumbnail: {dest_path}")


def extract_frames_per_second(
    source_path: str | Path,
    output_dir: str | Path,
) -> list[str]:
    """
    Extract one JPEG per second from a video.
    Returns list of written file paths.
    """
    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {source_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(source_path).stem
    written: list[str] = []

    second = 0
    while True:
        cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        frame_path = out_dir / f"{stem}_sec{second:04d}.jpg"
        if cv2.imwrite(str(frame_path), frame):
            written.append(str(frame_path))
        second += 1

    cap.release()
    if not written:
        raise RuntimeError(f"No frames extracted from video: {source_path}")
    return written
