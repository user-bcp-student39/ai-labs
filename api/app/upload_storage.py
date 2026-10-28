from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from tempfile import NamedTemporaryFile

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
UPLOAD_READ_CHUNK_BYTES = 64 * 1024
ALLOWED_UPLOAD_EXTENSIONS = frozenset({".txt", ".md", ".json"})


@dataclass(frozen=True)
class StoredUpload:
    file_name: str
    stored_at: str
    size: int


class InvalidUploadError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


class UploadAlreadyExistsError(ValueError):
    pass


def _normalize_filename(filename: str | None) -> str:
    if not filename or "\x00" in filename:
        raise InvalidUploadError("Invalid upload filename")

    normalized_name = PureWindowsPath(filename).name
    if not normalized_name or normalized_name in {".", ".."} or ":" in normalized_name:
        raise InvalidUploadError("Invalid upload filename")

    if Path(normalized_name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
        raise InvalidUploadError("Unsupported upload extension")

    return normalized_name


async def store_upload(upload: UploadFile, upload_dir: Path) -> StoredUpload:
    file_name = _normalize_filename(upload.filename)
    destination = upload_dir / file_name
    temporary_path: Path | None = None
    size = 0

    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=".upload-",
            suffix=".tmp",
            dir=upload_dir,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            while content := await upload.read(UPLOAD_READ_CHUNK_BYTES):
                size += len(content)
                if size > MAX_UPLOAD_BYTES:
                    raise UploadTooLargeError("Upload exceeds the maximum size")
                temporary_file.write(content)

        try:
            os.link(temporary_path, destination)
        except FileExistsError as error:
            raise UploadAlreadyExistsError(file_name) from error

        return StoredUpload(file_name=file_name, stored_at=file_name, size=size)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
