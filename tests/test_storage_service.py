import pytest
import os
import shutil
from app.services.storage_service import get_storage_service

@pytest.mark.asyncio
async def test_upload_pdf_local():
    """
    Verifies that the storage service saves a file to the uploads directory.
    """
    storage_service = get_storage_service()
    test_content = b"PDF dummy content"
    test_filename = "test_contract_storage.pdf"
    
    # Save current uploads if it exists to restore later, or just use a test filename
    res_url = await storage_service.upload_pdf(test_content, test_filename)
    
    assert res_url is not None
    assert "/uploads/" in res_url
    assert test_filename in res_url
    
    # Verify file exists on disk
    upload_dir = os.path.join(os.getcwd(), "uploads")
    expected_path = os.path.join(upload_dir, test_filename)
    assert os.path.exists(expected_path)
    
    with open(expected_path, "rb") as f:
        assert f.read() == test_content
        
    # Cleanup
    if os.path.exists(expected_path):
        os.remove(expected_path)
