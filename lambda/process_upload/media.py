import os
from pathlib import Path

import cv2

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

# thumb/: 400px max edge for UI preview
THUMB_MAX_EDGE = int(os.environ.get("THUMB_MAX_EDGE", "400"))
THUMB_JPEG_QUALITY = int(os.environ.get("THUMB_JPEG_QUALITY", "85"))

# ai-ready/: fit inside 1920x1080 (1080p box) for GCP ML
AI_READY_MAX_WIDTH = int(os.environ.get("AI_READY_MAX_WIDTH", "1920"))
AI_READY_MAX_HEIGHT = int(os.environ.get("AI_READY_MAX_HEIGHT", "1080"))
AI_READY_JPEG_QUALITY = int(os.environ.get("AI_READY_JPEG_QUALITY", "90"))


def file_kind(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    return "unknown"


def _resize_keep_aspect(img, max_w: int, max_h: int):
    height, width = img.shape[:2]
    scale = min(max_w / width, max_h / height, 1.0)
    if scale >= 1.0:
        return img
    new_w = max(1, int(width * scale))
    new_h = max(1, int(height * scale))
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _write_jpeg(path: str | Path, img, quality: int) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(dest), img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError(f"Failed to write image: {path}")


def create_thumbnail(
    source_path: str | Path,
    dest_path: str | Path,
    max_edge: int = THUMB_MAX_EDGE,
) -> None:
    """thumb/: ~400px max edge for frontend gallery."""
    img = cv2.imread(str(source_path))
    if img is None:
        raise ValueError(f"Could not read image: {source_path}")
    thumb = _resize_keep_aspect(img, max_edge, max_edge)
    _write_jpeg(dest_path, thumb, THUMB_JPEG_QUALITY)


def create_ai_ready_image(
    source_path: str | Path,
    dest_path: str | Path,
) -> None:
    """ai-ready/: standardize still image to fit 1080p box."""
    img = cv2.imread(str(source_path))
    if img is None:
        raise ValueError(f"Could not read image: {source_path}")
    ready = _resize_keep_aspect(img, AI_READY_MAX_WIDTH, AI_READY_MAX_HEIGHT)
    _write_jpeg(dest_path, ready, AI_READY_JPEG_QUALITY)


def create_video_thumbnail(
    source_path: str | Path,
    dest_path: str | Path,
) -> None:
    """Use first frame as thumb/ preview for video uploads."""
    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {source_path}")
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise ValueError(f"No frame in video: {source_path}")
    thumb = _resize_keep_aspect(frame, THUMB_MAX_EDGE, THUMB_MAX_EDGE)
    _write_jpeg(dest_path, thumb, THUMB_JPEG_QUALITY)


def extract_frames_per_second_1080p(
    source_path: str | Path,
    output_dir: str | Path,
) -> list[str]:
    """
    Video → ai-ready/: one JPEG per second, each resized into 1080p box.
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
        ready = _resize_keep_aspect(frame, AI_READY_MAX_WIDTH, AI_READY_MAX_HEIGHT)
        frame_path = out_dir / f"{stem}_sec{second:04d}.jpg"
        _write_jpeg(frame_path, ready, AI_READY_JPEG_QUALITY)
        written.append(str(frame_path))
        second += 1

    cap.release()
    if not written:
        raise RuntimeError(f"No frames extracted from video: {source_path}")
    return written
