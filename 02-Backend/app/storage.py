import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from .database import get_db

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "local")
        self.local_storage_path = os.getenv("LOCAL_STORAGE_PATH", "storage/uploads")
        self.s3_bucket = os.getenv("S3_BUCKET", "")
        self.s3_endpoint = os.getenv("S3_ENDPOINT", "")
        self.s3_access_key = os.getenv("S3_ACCESS_KEY", "")
        self.s3_secret_key = os.getenv("S3_SECRET_KEY", "")
        self.r2_account_id = os.getenv("R2_ACCOUNT_ID", "")
        self.r2_bucket = os.getenv("R2_BUCKET", "")

        if self.storage_type == "local":
            os.makedirs(self.local_storage_path, exist_ok=True)

    def upload_file(self, file_bytes: bytes, filename: str, user_id: str, content_type: str) -> str:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1]
        stored_filename = f"{file_id}{ext}"

        if self.storage_type == "local":
            file_path = os.path.join(self.local_storage_path, stored_filename)
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            url = f"/files/{file_id}"
        elif self.storage_type == "s3":
            url = self._upload_s3(file_bytes, stored_filename, content_type)
        elif self.storage_type == "r2":
            url = self._upload_r2(file_bytes, stored_filename, content_type)
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

        with get_db() as conn:
            conn.execute(
                """INSERT INTO files (id, user_id, filename, content_type, size, storage_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (file_id, user_id, filename, content_type, len(file_bytes), self.storage_type, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

        return url

    def delete_file(self, file_id: str, user_id: str) -> bool:
        with get_db() as conn:
            row = conn.execute(
                "SELECT storage_type, filename FROM files WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()
            if not row:
                return False

            if row["storage_type"] == "local":
                file_path = os.path.join(self.local_storage_path, row["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)

            conn.execute("DELETE FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
            conn.commit()
        return True

    def get_file_url(self, file_id: str, user_id: str) -> str:
        with get_db() as conn:
            row = conn.execute(
                "SELECT filename, storage_type FROM files WHERE id = ? AND user_id = ?",
                (file_id, user_id),
            ).fetchone()
            if not row:
                raise ValueError("File not found")

            if row["storage_type"] == "local":
                return f"/files/{file_id}"
            elif row["storage_type"] == "s3":
                return f"https://{self.s3_bucket}.s3.amazonaws.com/{row['filename']}"
            elif row["storage_type"] == "r2":
                return f"https://{self.r2_account_id}.r2.cloudflarestorage.com/{self.r2_bucket}/{row['filename']}"
            else:
                return f"/files/{file_id}"

    def list_user_files(self, user_id: str) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, filename, content_type, size, created_at FROM files WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "content_type": r["content_type"],
                    "size": r["size"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def _upload_s3(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                endpoint_url=self.s3_endpoint or None,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
            )
            s3.put_object(Bucket=self.s3_bucket, Key=filename, Body=file_bytes, ContentType=content_type)
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{filename}"
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def _upload_r2(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{self.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
            )
            s3.put_object(Bucket=self.r2_bucket, Key=filename, Body=file_bytes, ContentType=content_type)
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com/{self.r2_bucket}/{filename}"
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            raise


storage_service = StorageService()
