"""File storage service -- local filesystem for dev, S3-compatible for prod."""

import os
import uuid
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "./storage"))


def save_file(lead_id: uuid.UUID, category: str, filename: str, data: bytes) -> str:
    """Save a file and return the relative path."""
    dir_path = STORAGE_ROOT / str(lead_id) / category
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    file_path.write_bytes(data)
    rel_path = str(file_path.relative_to(STORAGE_ROOT))
    logger.info(
        "file_saved",
        lead_id=str(lead_id),
        category=category,
        path=rel_path,
        size=len(data),
    )
    return rel_path


def get_file(rel_path: str) -> bytes:
    """Read a file by relative path."""
    return (STORAGE_ROOT / rel_path).read_bytes()


def delete_file(rel_path: str) -> bool:
    """Delete a file. Returns True if deleted."""
    full = STORAGE_ROOT / rel_path
    if full.exists():
        full.unlink()
        return True
    return False


def get_absolute_path(rel_path: str) -> Path:
    """Get absolute path for a relative storage path."""
    return STORAGE_ROOT / rel_path
