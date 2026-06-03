import re
import uuid

import boto3
from botocore.config import Config

from config import AWS_REGION, PRESIGN_EXPIRY_SECONDS, RAW_PREFIX, S3_BUCKET_NAME

_s3 = boto3.client("s3", region_name=AWS_REGION, config=Config(signature_version="s3v4"))


def _sanitize_filename(name: str) -> str:
    base = name.split("/")[-1].split("\\")[-1]
    base = re.sub(r"[^\w.\-]", "_", base)
    return base or "upload.bin"


def build_file_key(user_id: str, filename: str) -> str:
    safe = _sanitize_filename(filename)
    uid = uuid.uuid4().hex[:12]
    user_part = re.sub(r"[^\w\-]", "_", user_id)[:64]
    return f"{RAW_PREFIX}{user_part}/{uid}_{safe}"


def create_presigned_put_url(file_key: str, content_type: str) -> str:
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is not configured")

    return _s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": S3_BUCKET_NAME,
            "Key": file_key,
            "ContentType": content_type or "application/octet-stream",
        },
        ExpiresIn=PRESIGN_EXPIRY_SECONDS,
    )
