import os
import uuid
import logging
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_AVATAR_MIME = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB


class StorageError(Exception):
    """Raised when an object storage operation fails."""


class StorageService:
    def __init__(self):
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            logger.info(f"Created local upload directory: {self.upload_dir}")

    # ------------------------------------------------------------------ #
    # Legacy: local PDF storage (kept until S3 PDFs are wired up)
    # ------------------------------------------------------------------ #
    async def upload_pdf(self, pdf_bytes: bytes, filename: str) -> Optional[str]:
        try:
            file_path = os.path.join(self.upload_dir, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            return f"/uploads/{filename}"
        except Exception as e:
            logger.error(f"Error uploading to local storage: {str(e)}")
            return None

    # ------------------------------------------------------------------ #
    # S3-compatible client (Railway portable-trunk)
    # ------------------------------------------------------------------ #
    def _is_s3_configured(self) -> bool:
        return bool(
            settings.AWS_ENDPOINT_URL
            and settings.AWS_S3_BUCKET_NAME
            and settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
        )

    def _get_s3_client(self):
        if not self._is_s3_configured():
            raise StorageError("Object storage is not configured")
        return boto3.client(
            "s3",
            endpoint_url=settings.AWS_ENDPOINT_URL,
            region_name=settings.AWS_DEFAULT_REGION or "auto",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
        )

    # ------------------------------------------------------------------ #
    # Avatars
    # ------------------------------------------------------------------ #
    async def upload_avatar(self, user_id: int, file: UploadFile) -> str:
        """Upload an avatar image. Returns the S3 key."""
        if file.content_type not in ALLOWED_AVATAR_MIME:
            raise StorageError(
                f"Unsupported file type: {file.content_type}. Allowed: jpg, png, webp"
            )

        contents = await file.read()
        if len(contents) > MAX_AVATAR_BYTES:
            raise StorageError("File too large. Maximum size is 5 MB.")
        if len(contents) == 0:
            raise StorageError("Empty file.")

        ext = ALLOWED_AVATAR_MIME[file.content_type]
        key = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"

        client = self._get_s3_client()
        try:
            client.put_object(
                Bucket=settings.AWS_S3_BUCKET_NAME,
                Key=key,
                Body=contents,
                ContentType=file.content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        except (BotoCoreError, ClientError) as e:
            logger.error(f"S3 put_object failed for user {user_id}: {e}")
            raise StorageError("Failed to upload avatar to storage") from e

        logger.info(f"Avatar uploaded for user {user_id}: {key}")
        return key

    def delete_avatar(self, key: str) -> None:
        """Delete an avatar object from S3. Errors are logged but not raised."""
        if not key:
            return
        try:
            client = self._get_s3_client()
            client.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=key)
            logger.info(f"Avatar deleted: {key}")
        except (BotoCoreError, ClientError, StorageError) as e:
            logger.warning(f"Failed to delete avatar {key}: {e}")

    def generate_avatar_url(self, key: Optional[str]) -> Optional[str]:
        """Generate a presigned GET URL for an avatar key. None if no key."""
        if not key:
            return None
        if not self._is_s3_configured():
            return None
        try:
            client = self._get_s3_client()
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": key},
                ExpiresIn=settings.AVATAR_URL_TTL_SECONDS,
            )
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to presign URL for {key}: {e}")
            return None


_storage_service = StorageService()


def get_storage_service() -> StorageService:
    return _storage_service
