from datetime import timedelta

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.config import get_settings

settings = get_settings()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)


def get_presigned_upload_url(object_key: str, content_type: str = "video/mp4", expires_in: int = 900) -> str:
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.aws_s3_bucket,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return url
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(f"Failed to create upload URL: {error}")


def get_presigned_download_url(object_key: str, expires_in: int = 900) -> str:
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.aws_s3_bucket,
                "Key": object_key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except (BotoCoreError, ClientError) as error:
        raise RuntimeError(f"Failed to create download URL: {error}")
