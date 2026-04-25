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
            
            # Wrap in professional legal document HTML structure
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: letter;
            margin: 2.54cm 2.54cm 2.54cm 2.54cm;
            @bottom-center {{
                content: counter(page) " of " counter(pages);
                font-family: "Times New Roman", Times, serif;
                font-size: 9pt;
                color: #666;
            }}
        }}
        body {{
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #000000;
            margin: 0;
            padding: 0;
        }}
        h1 {{
            font-family: "Times New Roman", Times, serif;
            font-size: 16pt;
            font-weight: bold;
            text-align: center;
            text-transform: uppercase;
            margin-top: 0;
            margin-bottom: 20pt;
            letter-spacing: 1px;
        }}
        h2 {{
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            font-weight: bold;
            text-transform: uppercase;
            border-top: 1px solid #000;
            margin-top: 20pt;
            margin-bottom: 6pt;
            padding-top: 10pt;
        }}
        h3 {{
            font-family: "Times New Roman", Times, serif;
            font-size: 11pt;
            font-weight: bold;
            margin-top: 12pt;
            margin-bottom: 4pt;
        }}
        p {{
            margin-top: 0;
            margin-bottom: 8pt;
            text-align: justify;
        }}
        ul {{
            list-style: none;
            margin-top: 4pt;
            margin-bottom: 8pt;
            padding-left: 20pt;
        }}
        ul li::before {{
            content: "· ";
            font-weight: bold;
        }}
        ol {{
            margin-top: 4pt;
            margin-bottom: 8pt;
            padding-left: 20pt;
        }}
        li {{
            margin-bottom: 4pt;
        }}
        strong {{
            font-weight: bold;
        }}
        em {{
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1px solid #000;
            margin: 16pt 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
            font-size: 11pt;
        }}
        th, td {{
            border: 1px solid #000;
            padding: 6pt 8pt;
            text-align: left;
        }}
        th {{
            font-weight: bold;
            background-color: #f0f0f0;
        }}
        .header-block {{
            border-bottom: 2px solid #000;
            margin-bottom: 8pt;
            padding-bottom: 10pt;
            text-align: center;
        }}
        .company-name {{
            font-family: "Times New Roman", Times, serif;
            font-weight: bold;
            font-size: 20pt;
            letter-spacing: 2px;
        }}
        .footer-bar {{
            border-top: 1px solid #999;
            margin-top: 24pt;
            padding-top: 6pt;
            font-size: 8pt;
            color: #666;
            text-align: center;
        }}
        blockquote {{
            margin-left: 24pt;
            margin-right: 0;
            border-left: 3px solid #ccc;
            padding-left: 12pt;
            color: #333;
        }}
        .signature-block {{
            margin-top: 40pt;
            border-top: 1px dashed #999;
            padding-top: 20pt;
        }}
        .sig-row {{
            display: flex;
            justify-content: space-between;
            gap: 40pt;
        }}
        .sig-col {{
            flex: 1;
        }}
        .sig-line {{
            border-bottom: 1px solid #000;
            height: 30pt;
            margin-bottom: 4pt;
        }}
        .sig-date-line {{
            border-bottom: 1px solid #000;
            height: 20pt;
            margin-top: 12pt;
            margin-bottom: 4pt;
        }}
        .sig-label {{
            font-size: 9pt;
            color: #444;
        }}
    </style>
</head>
<body>
    <div class="header-block">
        <div class="company-name">GoContract</div>
    </div>
    {html_content}
    <div class="signature-block">
        <div class="sig-row">
            <div class="sig-col">
                <div class="sig-line"></div>
                <div class="sig-label">Client Signature</div>
                <div class="sig-date-line"></div>
                <div class="sig-label">Date</div>
            </div>
            <div class="sig-col">
                <div class="sig-line"></div>
                <div class="sig-label">Service Provider Signature</div>
                <div class="sig-date-line"></div>
                <div class="sig-label">Date</div>
            </div>
        </div>
    </div>
    <div class="footer-bar">
        &copy; {time.strftime('%Y')} GoContract Inc. &nbsp;|&nbsp; This document was generated by AI and is legally binding between the signing parties. &nbsp;|&nbsp; Confidential &mdash; For authorized parties only
    </div>
</body>
</html>"""
            
            # Convert HTML to PDF (bytes)
            pdf_bytes = HTML(string=full_html).write_pdf()
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None

def get_pdf_service() -> PDFService:
    return PDFService()
