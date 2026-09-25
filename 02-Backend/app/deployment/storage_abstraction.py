from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from ..deployment.base_adapter import BaseCloudAdapter, DeploymentConfig, StorageCredentials


@dataclass
class ObjectStorageConfig:
    bucket_name: str
    region: str = "us-east-1"
    versioning: bool = True
    encryption: str = "AES256"
    public_access: bool = False
    lifecycle_rules: Optional[List[Dict[str, Any]]] = None


class BaseObjectStorage(ABC):
    @abstractmethod
    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    @abstractmethod
    def get_object(self, bucket: str, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, bucket: str, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_objects(self, bucket: str, prefix: str = "") -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        raise NotImplementedError

    @abstractmethod
    def copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_bucket_policy(self, bucket: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def set_bucket_policy(self, bucket: str, policy: Dict[str, Any]) -> bool:
        raise NotImplementedError


class ObjectStorageFactory:
    @staticmethod
    def create(adapter: BaseCloudAdapter, config: ObjectStorageConfig) -> BaseObjectStorage:
        provider = adapter.provider
        if provider.value == "aws":
            return S3ObjectStorage(adapter, config)
        elif provider.value == "azure":
            return BlobObjectStorage(adapter, config)
        elif provider.value == "gcp":
            return GCSObjectStorage(adapter, config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")


class S3ObjectStorage(BaseObjectStorage):
    def __init__(self, adapter: BaseCloudAdapter, config: ObjectStorageConfig):
        self.adapter = adapter
        self.config = config

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        adapter = self.adapter
        adapter.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{bucket}/{key}"

    def get_object(self, bucket: str, key: str) -> bytes:
        adapter = self.adapter
        response = adapter.s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def delete_object(self, bucket: str, key: str) -> bool:
        adapter = self.adapter
        adapter.s3_client.delete_object(Bucket=bucket, Key=key)
        return True

    def list_objects(self, bucket: str, prefix: str = "") -> List[str]:
        adapter = self.adapter
        response = adapter.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]

    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        adapter = self.adapter
        return adapter.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration,
        )

    def copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> str:
        adapter = self.adapter
        adapter.s3_client.copy_object(
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Bucket=dest_bucket,
            Key=dest_key,
        )
        return f"s3://{dest_bucket}/{dest_key}"

    def get_bucket_policy(self, bucket: str) -> Dict[str, Any]:
        adapter = self.adapter
        try:
            response = adapter.s3_client.get_bucket_policy(Bucket=bucket)
            return response.get("Policy", {})
        except Exception:
            return {}

    def set_bucket_policy(self, bucket: str, policy: Dict[str, Any]) -> bool:
        adapter = self.adapter
        adapter.s3_client.put_bucket_policy(Bucket=bucket, Policy=policy)
        return True


class BlobObjectStorage(BaseObjectStorage):
    def __init__(self, adapter: BaseCloudAdapter, config: ObjectStorageConfig):
        self.adapter = adapter
        self.config = config

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        blob_client = self.adapter.blob_service_client.get_blob_client(container=bucket, blob=key)
        blob_client.upload_blob(data, overwrite=True)
        return f"https://{self.adapter.config.storage_credentials.account_name}.blob.core.windows.net/{bucket}/{key}"

    def get_object(self, bucket: str, key: str) -> bytes:
        blob_client = self.adapter.blob_service_client.get_blob_client(container=bucket, blob=key)
        return blob_client.download_blob().readall()

    def delete_object(self, bucket: str, key: str) -> bool:
        blob_client = self.adapter.blob_service_client.get_blob_client(container=bucket, blob=key)
        blob_client.delete_blob()
        return True

    def list_objects(self, bucket: str, prefix: str = "") -> List[str]:
        container_client = self.adapter.blob_service_client.get_container_client(bucket)
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]

    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        blob_client = self.adapter.blob_service_client.get_blob_client(container=bucket, blob=key)
        return blob_client.generate_blob_sas_url("r", expiry=expiration)

    def copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> str:
        source_blob = self.adapter.blob_service_client.get_blob_client(container=source_bucket, blob=source_key)
        dest_blob = self.adapter.blob_service_client.get_blob_client(container=dest_bucket, blob=dest_key)
        dest_blob.start_copy_from_url(source_blob.url)
        return f"https://{self.adapter.config.storage_credentials.account_name}.blob.core.windows.net/{dest_bucket}/{dest_key}"

    def get_bucket_policy(self, bucket: str) -> Dict[str, Any]:
        return {}

    def set_bucket_policy(self, bucket: str, policy: Dict[str, Any]) -> bool:
        return True


class GCSObjectStorage(BaseObjectStorage):
    def __init__(self, adapter: BaseCloudAdapter, config: ObjectStorageConfig):
        self.adapter = adapter
        self.config = config
        self.project_id = adapter.project_id

    def put_object(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        blob = bucket_client.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{bucket}/{key}"

    def get_object(self, bucket: str, key: str) -> bytes:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        blob = bucket_client.blob(key)
        return blob.download_as_bytes()

    def delete_object(self, bucket: str, key: str) -> bool:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        blob = bucket_client.blob(key)
        blob.delete()
        return True

    def list_objects(self, bucket: str, prefix: str = "") -> List[str]:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        blobs = storage_client.list_blobs(bucket_client.name, prefix=prefix)
        return [blob.name for blob in blobs]

    def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        blob = bucket_client.blob(key)
        return blob.generate_signed_url(expiration=expiration)

    def copy_object(self, source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> str:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        source_blob = storage_client.bucket(source_bucket).blob(source_key)
        dest_blob = storage_client.bucket(dest_bucket).blob(dest_key)
        dest_blob.rewrite(source_blob)
        return f"gs://{dest_bucket}/{dest_key}"

    def get_bucket_policy(self, bucket: str) -> Dict[str, Any]:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        try:
            policy = bucket_client.get_iam_policy()
            return dict(policy)
        except Exception:
            return {}

    def set_bucket_policy(self, bucket: str, policy: Dict[str, Any]) -> bool:
        from google.cloud import storage
        storage_client = storage.Client(project=self.project_id)
        bucket_client = storage_client.bucket(bucket)
        bucket_client.set_iam_policy(policy)
        return True
