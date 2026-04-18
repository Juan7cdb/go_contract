import markdown
import logging
from typing import Optional
import os
import time
import sys

# macOS Homebrew Path Helper
if sys.platform == "darwin":
    # Common Homebrew paths for Apple Silicon and Intel
    brew_paths = ["/opt/homebrew/lib", "/usr/local/lib"]
    for path in brew_paths:
        if os.path.exists(path) and path not in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", ""):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                path + ":" + os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            ).strip(":")

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception as e:
    # Diagnostic logging for missing dependencies
    logging.error(f"WeasyPrint initialization failed: {e}")
    WEASYPRINT_AVAILABLE = False

class PDFService:
    @staticmethod
    def generate_pdf_from_markdown(md_content: str, filename: str) -> Optional[bytes]:
        """
        Converts Markdown content to a PDF byte string.
        """
        if not WEASYPRINT_AVAILABLE:
            logger.error("PDF generation skipped: WeasyPrint dependencies are not installed on this system.")
            return None
            
        try:
            # Convert Markdown to HTML
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
            
            # Wrap in basic HTML structure with premium styling
            full_html = f"""
            <html>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
                <style>
                    @page {{
                        margin: 2.5cm;
                        @bottom-right {{
                            content: "Página " counter(page) " de " counter(pages);
                            font-size: 9pt;
                            color: #6b7280;
                        }}
                    }}
                    body {{
                        font-family: 'Inter', 'Helvetica', sans-serif;
                        line-height: 1.6;
                        color: #111827;
                        font-size: 11pt;
                    }}
                    .header {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-bottom: 2px solid #2563eb;
                        padding-bottom: 10px;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-weight: 700;
                        font-size: 18pt;
                        color: #2563eb;
                    }}
                    .doc-info {{
                        text-align: right;
                        font-size: 9pt;
                        color: #6b7280;
                    }}
                    h1 {{ 
                        color: #111827; 
                        text-align: center; 
                        margin-bottom: 30px; 
                        font-size: 20pt;
                        text-transform: uppercase;
                    }}
                    h2 {{ 
                        color: #1e3a8a; 
                        border-bottom: 1px solid #e5e7eb; 
                        padding-bottom: 5px; 
                        margin-top: 20px;
                        font-size: 14pt;
                    }}
                    h3 {{ color: #374151; font-size: 12pt; margin-top: 15px; }}
                    p {{ margin-bottom: 10px; text-align: justify; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ border: 1px solid #d1d5db; padding: 10px; text-align: left; font-size: 10pt; }}
                    th {{ background-color: #f9fafb; font-weight: 700; }}
                    .footer {{ 
                        text-align: center; 
                        font-size: 8pt; 
                        color: #9ca3af; 
                        margin-top: 50px;
                        border-top: 1px solid #e5e7eb;
                        padding-top: 10px;
                    }}
                    .signature-box {{
                        margin-top: 50px;
                        display: table;
                        width: 100%;
                    }}
                    .signature-line {{
                        display: table-cell;
                        width: 45%;
                        border-top: 1px solid #000;
                        padding-top: 5px;
                        text-align: center;
                    }}
                    .spacer {{ display: table-cell; width: 10%; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="logo">GoContract</div>
                    <div class="doc-info">
                        Documento ID: {filename.split('.')[0]}<br>
                        Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
                {html_content}
                <div class="footer">
                    &copy; {time.strftime('%Y')} Go Contracto Inc. - Este documento ha sido generado mediante inteligencia artificial y tiene validez legal entre las partes firmantes.
                </div>
            </body>
            </html>
            """
            
            # Convert HTML to PDF (bytes)
            pdf_bytes = HTML(string=full_html).write_pdf()
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None

def get_pdf_service() -> PDFService:
    return PDFService()
