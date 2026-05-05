"""
CSV upload and dataset metadata extraction.
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from fastapi import UploadFile

from ..config import ALLOWED_FILE_TYPES, get_settings
from ..models.session import DatasetMetadata
from ..utils.error_handler import CorruptedDataError, FileTooLargeError, InvalidFileFormatError

settings = get_settings()


class FileManager:
    """File manager for handling CSV uploads."""

    def __init__(self) -> None:
        self.root_dir = Path(settings.UPLOAD_DIR)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_uploaded_csv(self, upload_file: UploadFile, session_id: str) -> DatasetMetadata:
        filename = Path(upload_file.filename or "dataset.csv").name
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_FILE_TYPES:
            raise InvalidFileFormatError(filename, ALLOWED_FILE_TYPES)

        upload_file.file.seek(0)
        content = upload_file.file.read()
        size_bytes = len(content)

        if size_bytes == 0:
            raise CorruptedDataError("Empty file")

        if size_bytes > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(size_bytes, settings.MAX_UPLOAD_SIZE)

        session_dir = self.root_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        csv_path = session_dir / filename
        csv_path.write_bytes(content)

        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise CorruptedDataError(str(exc)) from exc

        missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns}
        dtypes = {str(col): str(df[col].dtype) for col in df.columns}
        preview_rows = df.head(5).fillna("").to_dict(orient="records")

        metadata = DatasetMetadata(
            filename=filename,
            file_path=str(csv_path),
            rows=int(df.shape[0]),
            columns=[str(col) for col in df.columns],
            dtypes=dtypes,
            missing_values=missing_values,
            preview_rows=preview_rows,
            size_bytes=size_bytes,
            uploaded_at=datetime.utcnow(),
        )

        return metadata


file_manager = FileManager()
