"""Upload de mídia pro DigitalOcean Spaces (S3-compatível)."""
from __future__ import annotations

import boto3

from app.config import settings


def _client():
    return boto3.client(
        "s3",
        region_name=settings.spaces_region,
        endpoint_url=settings.spaces_endpoint,
        aws_access_key_id=settings.spaces_key,
        aws_secret_access_key=settings.spaces_secret,
    )


def upload(local_path: str, key: str, public: bool = True) -> str:
    extra = {"ACL": "public-read"} if public else {}
    _client().upload_file(local_path, settings.spaces_bucket, key, ExtraArgs=extra)
    return f"{settings.spaces_endpoint}/{settings.spaces_bucket}/{key}"
