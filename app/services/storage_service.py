import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            logger.info(f"Created local upload directory: {self.upload_dir}")

    async def upload_pdf(self, pdf_bytes: bytes, filename: str) -> Optional[str]:
        """
        Uploads PDF to storage. Currently implements local storage as default.
        In production, this should use Boto3 to upload to S3.
        """
        try:
            # Check for AWS configuration in settings
            if hasattr(settings, "AWS_ACCESS_KEY_ID") and settings.AWS_ACCESS_KEY_ID != "change_me":
                # Implementation for S3 would go here
                # return await self._upload_to_s3(pdf_bytes, filename)
                pass

            # Fallback to local storage for now
            file_path = os.path.join(self.upload_dir, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            
            # Return a relative URL or full URL if domain is known
            # For local dev, we might serve this via FastAPI static files
            return f"/uploads/{filename}"
            
        except Exception as e:
            logger.error(f"Error uploading to storage: {str(e)}")
            return None

_storage_service = StorageService()

def get_storage_service() -> StorageService:
    return _storage_service
