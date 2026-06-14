import logging
from pathlib import Path

from app.core.config import StorageType, settings

logger = logging.getLogger(__name__)


def storage_type() -> str:
    return settings.STORAGE_TYPE.value


def build_object_key(node_name: str, filename: str) -> str:
    prefix = settings.S3_BACKUP_PREFIX.strip("/")
    if prefix:
        return f"{prefix}/{node_name}/{filename}"
    return f"{node_name}/{filename}"


def save_bytes(data: bytes, node_name: str, filename: str) -> tuple[str, str]:
    if settings.STORAGE_TYPE == StorageType.S3:
        return _save_s3(data, node_name, filename)
    return _save_local(data, node_name, filename)


def read_bytes(storage_path: str, storage_type_value: str) -> bytes:
    if storage_type_value == StorageType.S3.value:
        return _read_s3(storage_path)
    return _read_local(storage_path)


def delete_object(storage_path: str, storage_type_value: str) -> None:
    if storage_type_value == StorageType.S3.value:
        _delete_s3(storage_path)
    else:
        _delete_local(storage_path)


def _local_path(node_name: str, filename: str) -> Path:
    return Path(settings.BACKUP_LOCAL_DIR) / node_name / filename


def _save_local(data: bytes, node_name: str, filename: str) -> tuple[str, str]:
    path = _local_path(node_name, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return StorageType.LOCAL.value, str(path)


def _read_local(storage_path: str) -> bytes:
    return Path(storage_path).read_bytes()


def _delete_local(storage_path: str) -> None:
    path = Path(storage_path)
    if path.exists():
        path.unlink()


def _s3_client():
    import boto3

    if not settings.S3_BUCKET:
        raise ValueError("S3_BUCKET is not configured")
    region = settings.S3_REGION or "us-east-1"
    return boto3.client("s3", region_name=region)


def _save_s3(data: bytes, node_name: str, filename: str) -> tuple[str, str]:
    key = build_object_key(node_name, filename)
    client = _s3_client()
    client.put_object(Bucket=settings.S3_BUCKET, Key=key, Body=data)
    logger.info("Uploaded backup to s3://%s/%s", settings.S3_BUCKET, key)
    return StorageType.S3.value, key


def _read_s3(storage_path: str) -> bytes:
    client = _s3_client()
    response = client.get_object(Bucket=settings.S3_BUCKET, Key=storage_path)
    return response["Body"].read()


def _delete_s3(storage_path: str) -> None:
    client = _s3_client()
    client.delete_object(Bucket=settings.S3_BUCKET, Key=storage_path)
