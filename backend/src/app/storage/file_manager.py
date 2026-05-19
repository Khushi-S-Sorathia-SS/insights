"""
CSV upload and dataset metadata extraction (database-integrated).

- display_name is MANDATORY — no fallback to filename
- Preview row count driven by AppConfig.PREVIEW_ROWS_COUNT
- Uses get_settings() for size/type validation limits
"""

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config.app_config import AppConfig
from src.app.config.settings import get_settings
from src.app.db.models import Dataset
from src.app.models.session import DatasetMetadata
from src.app.utils.error_handler import (
    CorruptedDataError,
    FileTooLargeError,
    InvalidFileFormatError,
)

settings = get_settings()


class FileManager:
    """Handles CSV ingestion: validation, parsing, and persistence to PostgreSQL."""

    async def save_uploaded_csv(
        self,
        upload_file: UploadFile,
        session_id: str,
        db: AsyncSession,
        display_name: str,  # Mandatory — no default, no fallback
    ) -> DatasetMetadata:
        """
        Validate, parse, and persist an uploaded CSV file.

        Parameters
        ----------
        upload_file:
            The multipart file upload from the request.
        session_id:
            Temporary session identifier (used for backwards compatibility).
        db:
            Async SQLAlchemy session for persisting the dataset record.
        display_name:
            User-defined workspace name. Must be unique. Mandatory — callers
            are responsible for providing this; no filename fallback exists.

        Returns
        -------
        DatasetMetadata
            Parsed metadata for the successfully saved dataset.

        Raises
        ------
        InvalidFileFormatError: File has no name or wrong extension.
        FileTooLargeError: File exceeds settings.MAX_UPLOAD_SIZE bytes.
        CorruptedDataError: File is empty or pandas cannot parse it as CSV.
        """
        if not upload_file.filename:
            raise InvalidFileFormatError("Unnamed File", AppConfig.ALLOWED_FILE_TYPES)

        filename = Path(upload_file.filename).name
        extension = Path(filename).suffix.lower()

        if extension not in AppConfig.ALLOWED_FILE_TYPES:
            raise InvalidFileFormatError(filename, AppConfig.ALLOWED_FILE_TYPES)

        upload_file.file.seek(0)
        content = upload_file.file.read()
        size_bytes = len(content)

        if size_bytes == 0:
            raise CorruptedDataError("Empty file")

        if size_bytes > settings.MAX_UPLOAD_SIZE:
            raise FileTooLargeError(size_bytes, settings.MAX_UPLOAD_SIZE)

        try:
            df = pd.read_csv(io.BytesIO(content))
            # Drop completely empty rows (e.g. trailing commas in CSV)
            df = df.dropna(how="all")
            # Re-encode cleaned data to store only valid rows in the DB
            content = df.to_csv(index=False).encode("utf-8")
            size_bytes = len(content)
        except Exception as exc:
            raise CorruptedDataError(str(exc)) from exc

        missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns}
        dtypes = {str(col): str(df[col].dtype) for col in df.columns}

        # Use AppConfig.PREVIEW_ROWS_COUNT — no magic number in code
        preview_rows = (
            df.head(AppConfig.PREVIEW_ROWS_COUNT).fillna("").to_dict(orient="records")
        )

        # Persist to PostgreSQL datasets table
        dataset_record = Dataset(
            filename=filename,
            display_name=display_name,  # Mandatory — no fallback
            schema_json={
                "columns": [str(col) for col in df.columns],
                "dtypes": dtypes,
                "missing_values": missing_values,
                "rows": int(df.shape[0]),
            },
            raw_data=content,
        )
        db.add(dataset_record)
        await db.commit()
        await db.refresh(dataset_record)

        return DatasetMetadata(
            filename=filename,
            dataset_id=str(dataset_record.id),
            file_path="",  # No longer saving to disk — data lives in PostgreSQL
            rows=int(df.shape[0]),
            columns=[str(col) for col in df.columns],
            dtypes=dtypes,
            missing_values=missing_values,
            preview_rows=preview_rows,
            size_bytes=size_bytes,
            uploaded_at=datetime.utcnow(),
        )


file_manager = FileManager()
