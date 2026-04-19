import asyncio
import os
import sys
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend_go_contract"))

# Mock environment variables if needed
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["OPENAI_API_KEY"] = "sk-test-key"

from app.services.ai_service import get_ai_service
from app.services.pdf_service import get_pdf_service
from app.services.storage_service import get_storage_service

async def verify_backend_services():
    print("--- Verificando Servicios Backend ---")
    
    # 1. PDF Service Check (The most likely failure point due to dependencies)
    pdf_service = get_pdf_service()
    print(f"Checking PDF Service...")
    sample_md = "# Test Contract\n\nThis is a test of the PDF generation service."
    pdf_bytes = pdf_service.generate_pdf_from_markdown(sample_md, "test_verify.pdf")
    
    if pdf_bytes:
        print("✅ PDF Service: Generación EXITOSA.")
        print(f"   Tamaño del PDF: {len(pdf_bytes)} bytes")
    else:
        print("❌ PDF Service: FALLÓ. Posiblemente faltan dependencias de WeasyPrint (libgobject, pango, etc.)")

    # 2. Storage Service Check
    storage_service = get_storage_service()
    print(f"\nChecking Storage Service...")
    if pdf_bytes:
        url = await storage_service.upload_pdf(pdf_bytes, "test_verify.pdf")
        if url:
            print(f"✅ Storage Service: Upload EXITOSO.")
            print(f"   URL generada: {url}")
            # Check if file exists
            if os.path.exists(os.path.join(os.getcwd(), "uploads", "test_verify.pdf")):
                print(f"   Archivo verificado en disco: uploads/test_verify.pdf")
        else:
            print("❌ Storage Service: FALLÓ al subir el archivo.")
    else:
        print("⚠️ Storage Service: No se pudo probar (depende de PDF Service).")

    # 3. AI Service (Dry Run - checking initialization)
    print(f"\nChecking AI Service...")
    ai_service = get_ai_service()
    if ai_service.client.api_key and ai_service.client.api_key != "sk-test-key":
        print("✅ AI Service: Cliente inicializado con API Key real.")
    else:
        print("⚠️ AI Service: Usando API Key de prueba o faltante.")

    print("\n--- Verificación Finalizada ---")

if __name__ == "__main__":
    asyncio.run(verify_backend_services())
