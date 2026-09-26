"""Storage management with S3 and MinIO support."""

from __future__ import annotations

import logging
from typing import BinaryIO, Dict, List, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_config

logger = logging.getLogger(__name__)


class StorageClient:
    """S3-compatible object storage client."""

    def __init__(self) -> None:
        self._config = get_config()
        self._client = None
        self._connect()

    def _connect(self) -> None:
        try:
            self._client = boto3.client(
                's3',
                endpoint_url=self._config.storage.endpoint,
                aws_access_key_id=self._config.storage.access_key_id,
                aws_secret_access_key=self._config.storage.secret_access_key,
                region_name=self._config.storage.region,
                config=Config(signature_version='s3v4'),
            )
            logger.info("Connected to object storage")
        except Exception as exc:
            logger.error(f"Object storage connection failed: {exc}")
            raise

    def upload_file(self, bucket: str, key: str, data: BinaryIO, content_type: Optional[str] = None) -> str:
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            self._client.upload_fileobj(data, bucket, key, ExtraArgs=extra_args)
            return f"s3://{bucket}/{key}"
        except ClientError as exc:
            logger.error(f"Upload failed: {exc}")
            raise

    def download_file(self, bucket: str, key: str) -> bytes:
        try:
            buffer = BytesIO()
            self._client.download_fileobj(bucket, key, buffer)
            return buffer.getvalue()
        except ClientError as exc:
            logger.error(f"Download failed: {exc}")
            raise

    def get_presigned_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        try:
            return self._client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in,
            )
        except ClientError as exc:
            logger.error(f"Presigned URL generation failed: {exc}")
            raise

    def delete_file(self, bucket: str, key: str) -> None:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            logger.error(f"Delete failed: {exc}")
            raise

    def list_files(self, bucket: str, prefix: str = "") -> list:
        try:
            response = self._client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as exc:
            logger.error(f"List failed: {exc}")
            raise


_storage: Optional[StorageClient] = None


def get_storage() -> StorageClient:
    global _storage
    if _storage is None:
        _storage = StorageClient()
    return _storage
