from typing import Optional, Dict, List


class ObjectStorage:
    def __init__(self, backend: str = 's3', endpoint: Optional[str] = None, access_key: Optional[str] = None, secret_key: Optional[str] = None, bucket_name: str = 'models'):
        self.backend = backend
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.client = None
        if backend == 's3':
            try:
                import boto3
                self.client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
            except ImportError:
                logger.warning("boto3 not installed, using local cache only for object storage")
        self.local_cache: Dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str = 'application/octet-stream') -> None:
        if self.client:
            self.client.put_object(Bucket=self.bucket_name, Key=key, Body=data, ContentType=content_type)
        self.local_cache[key] = data

    def get(self, key: str) -> Optional[bytes]:
        if key in self.local_cache:
            return self.local_cache[key]
        if self.client:
            try:
                response = self.client.get_object(Bucket=self.bucket_name, Key=key)
                data = response['Body'].read()
                self.local_cache[key] = data
                return data
            except Exception:
                return None
        return None

    def delete(self, key: str) -> None:
        if self.client:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
        self.local_cache.pop(key, None)

    def list_objects(self, prefix: str = '') -> List[str]:
        if self.client:
            try:
                response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                return [obj['Key'] for obj in response.get('Contents', [])]
            except Exception:
                return []
        return list(self.local_cache.keys())
