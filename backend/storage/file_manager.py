"""
CSV upload and dataset metadata extraction (Database integrated).
"""

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ALLOWED_FILE_TYPES, get_settings
from ..models.session import DatasetMetadata
from ..db.models import Dataset
from ..utils.error_handler import CorruptedDataError, FileTooLargeError, InvalidFileFormatError

settings = get_settings()

class FileManager:
    """File manager for handling CSV uploads."""

    def __init__(self) -> None:
        pass

    async def save_uploaded_csv(self, upload_file: UploadFile, session_id: str, db: AsyncSession, display_name: str = None) -> DatasetMetadata:
        if not upload_file.filename:
            raise InvalidFileFormatError("Unnamed File", ALLOWED_FILE_TYPES)
            
        filename = Path(upload_file.filename).name
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

        try:
            df = pd.read_csv(io.BytesIO(content))
            # Clean completely empty rows that might inflate row counts (e.g. trailing commas)
            df = df.dropna(how='all')
            # Re-encode the cleaned dataframe to bytes to store clean data in the DB
            content = df.to_csv(index=False).encode('utf-8')
            size_bytes = len(content)
        except Exception as exc:
            raise CorruptedDataError(str(exc)) from exc

        missing_values = {str(col): int(df[col].isna().sum()) for col in df.columns}
        dtypes = {str(col): str(df[col].dtype) for col in df.columns}
        preview_rows = df.head(5).fillna("").to_dict(orient="records")

        # Save to PostgreSQL datasets table
        dataset_record = Dataset(
            filename=filename,
            display_name=display_name or filename,
            schema_json={
                "columns": [str(col) for col in df.columns],
                "dtypes": dtypes,
                "missing_values": missing_values,
                "rows": int(df.shape[0])
            },
            raw_data=content
        )
        db.add(dataset_record)
        await db.commit()
        await db.refresh(dataset_record)

        metadata = DatasetMetadata(
            filename=filename,
            dataset_id=str(dataset_record.id),
            file_path="",  # No longer saving to disk
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
