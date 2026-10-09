"""Cloud storage integration for AstrovoxAI backend.

Supports S3, Cloudflare R2, and Supabase Storage backends with unified interface.
"""

from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from typing import Any, BinaryIO, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class StorageObject:
    key: str
    bucket: str
    size: int
    content_type: str
    last_modified: str
    url: Optional[str] = None


class CloudStorageService:
    """Unified cloud storage service supporting multiple backends."""

    def __init__(self):
        self.backend = self._detect_backend()
        self._client = self._init_client()

    def _detect_backend(self) -> str:
        if os.getenv("R2_ACCOUNT_ID") and os.getenv("R2_ACCESS_KEY_ID"):
            return "cloudflare_r2"
        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            return "s3"
        if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            return "supabase"
        return "local"

    def _init_client(self) -> Any:
        try:
            if self.backend == "cloudflare_r2":
                import boto3

                return boto3.client(
                    "s3",
                    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
                    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID", ""),
                    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY", ""),
                    region_name="auto",
                )
            if self.backend == "s3":
                import boto3

                return boto3.client(
                    "s3",
                    region_name=os.getenv("AWS_REGION", "us-east-1"),
                )
            if self.backend == "supabase":
                from supabase import create_client

                return create_client(
                    os.getenv("SUPABASE_URL", ""),
                    os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cloud storage init failed: %s", exc)
        return None

    @property
    def is_cloud(self) -> bool:
        return self.backend in ("s3", "cloudflare_r2", "supabase")

    def upload(
        self,
        bucket: str,
        key: str,
        data: Union[bytes, BinaryIO, str],
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageObject:
        if isinstance(data, str):
            data = data.encode("utf-8")
        if self.backend in ("s3", "cloudflare_r2"):
            extra = {"ContentType": content_type}
            if metadata:
                extra["Metadata"] = metadata
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                **extra,
            )
            return StorageObject(
                key=key,
                bucket=bucket,
                size=len(data) if isinstance(data, bytes) else 0,
                content_type=content_type,
                last_modified="",
            )
        if self.backend == "supabase":
            self._client.storage.from_(bucket).upload(
                path=key,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return StorageObject(key=key, bucket=bucket, size=0, content_type=content_type, last_modified="")
        raise RuntimeError(f"Unsupported storage backend: {self.backend}")

    def download(self, bucket: str, key: str) -> bytes:
        if self.backend in ("s3", "cloudflare_r2"):
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        if self.backend == "supabase":
            response = self._client.storage.from_(bucket).download(key)
            return response
        raise RuntimeError(f"Unsupported storage backend: {self.backend}")

    def delete(self, bucket: str, key: str) -> bool:
        if self.backend in ("s3", "cloudflare_r2"):
            self._client.delete_object(Bucket=bucket, Key=key)
            return True
        if self.backend == "supabase":
            self._client.storage.from_(bucket).remove([key])
            return True
        return False

    def list_objects(self, bucket: str, prefix: str = "") -> List[StorageObject]:
        if self.backend in ("s3", "cloudflare_r2"):
            paginator = self._client.get_paginator("list_objects_v2")
            objects = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    objects.append(
                        StorageObject(
                            key=obj["Key"],
                            bucket=bucket,
                            size=obj["Size"],
                            content_type="application/octet-stream",
                            last_modified=obj["LastModified"].isoformat(),
                        )
                    )
            return objects
        if self.backend == "supabase":
            response = self._client.storage.from_(bucket).list(prefix)
            return [
                StorageObject(
                    key=item["name"],
                    bucket=bucket,
                    size=item.get("metadata", {}).get("size", 0),
                    content_type=item.get("metadata", {}).get("mimetype", "application/octet-stream"),
                    last_modified=item.get("updated_at", ""),
                )
                for item in response
            ]
        return []

    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
    ) -> str:
        if self.backend in ("s3", "cloudflare_r2"):
            return self._client.generate_presigned_url(
                ClientMethod="get_object" if method == "GET" else "put_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        if self.backend == "supabase":
            return self._client.storage.from_(bucket).create_signed_url(
                key, expires_in
            )["signedURL"]
        return ""

    def get_public_url(self, bucket: str, key: str, cdn_base: Optional[str] = None) -> str:
        if cdn_base:
            return f"{cdn_base.rstrip('/')}/{key}"
        if self.backend == "cloudflare_r2":
            account = os.getenv("R2_ACCOUNT_ID", "")
            bucket_custom = os.getenv("R2_BUCKET_NAME", bucket)
            return f"https://{bucket_custom}.{account}.r2.dev/{key}"
        if self.backend == "s3":
            region = os.getenv("AWS_REGION", "us-east-1")
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        if self.backend == "supabase":
            project = os.getenv("SUPABASE_URL", "").replace("https://", "").split(".")[0]
            return f"https://{project}.supabase.co/storage/v1/object/public/{bucket}/{key}"
        return f"/storage/{bucket}/{key}"


cloud_storage = CloudStorageService()
