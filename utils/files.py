"""
File handling utilities for safe upload validation, storage, and retrieval.
"""

import os
import uuid
from pathlib import Path
from typing import Tuple, Set
from fastapi import UploadFile
from .errors import ValidationException

ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".3gp"}

MAX_IMAGE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def get_upload_base_dir() -> Path:
    """Returns the base directory for uploaded media."""
    project_dir = Path(__file__).resolve().parent.parent
    upload_dir = project_dir / os.getenv("UPLOAD_DIR", "uploads")
    return upload_dir


def ensure_upload_dirs() -> Tuple[Path, Path]:
    """Ensures uploads/images and uploads/videos exist."""
    base_dir = get_upload_base_dir()
    img_dir = base_dir / "images"
    vid_dir = base_dir / "videos"
    img_dir.mkdir(parents=True, exist_ok=True)
    vid_dir.mkdir(parents=True, exist_ok=True)
    return img_dir, vid_dir


def validate_file_extension(filename: str, allowed_extensions: Set[str]) -> str:
    """Validates that the file has an acceptable extension."""
    if not filename:
        raise ValidationException("Missing filename in upload.")
    
    ext = Path(filename).suffix.lower()
    if not ext or ext not in allowed_extensions:
        allowed_str = ", ".join(allowed_extensions)
        raise ValidationException(
            f"Unsupported file format '{ext}'. Allowed formats: {allowed_str}"
        )
    return ext


async def save_upload_file(
    upload_file: UploadFile,
    is_video: bool = False,
) -> str:
    """
    Validates, renames safely with UUID, streams to disk, and returns the absolute saved file path.
    Prevents directory traversal and untrusted filename attacks.
    """
    if not upload_file or not upload_file.filename:
        raise ValidationException("No upload file provided.")

    allowed_exts = ALLOWED_VIDEO_EXTENSIONS if is_video else ALLOWED_IMAGE_EXTENSIONS
    max_size = MAX_VIDEO_SIZE_BYTES if is_video else MAX_IMAGE_SIZE_BYTES
    media_type = "video" if is_video else "image"

    ext = validate_file_extension(upload_file.filename, allowed_exts)
    img_dir, vid_dir = ensure_upload_dirs()
    target_dir = vid_dir if is_video else img_dir

    # Generate unique, unguessable filename
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / safe_filename

    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks

    try:
        with open(target_path, "wb") as buffer:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_size:
                    buffer.close()
                    if target_path.exists():
                        target_path.unlink()
                    raise ValidationException(
                        f"{media_type.capitalize()} file exceeds maximum allowed limit of {max_size // (1024*1024)} MB."
                    )
                buffer.write(chunk)
    except Exception as e:
        if target_path.exists():
            target_path.unlink()
        if isinstance(e, ValidationException):
            raise
        raise ValidationException(f"Failed to process upload: {str(e)}")

    if total_bytes == 0:
        if target_path.exists():
            target_path.unlink()
        raise ValidationException("Uploaded file is empty (0 bytes).")

    return str(target_path.resolve())
