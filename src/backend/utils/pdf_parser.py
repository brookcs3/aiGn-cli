"""
PDF text extraction using PyMuPDF (fitz)
"""
import sys
from pathlib import Path

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using PyMuPDF.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a string
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "[ERROR] PyMuPDF not installed. Run: pip install PyMuPDF"

    path = Path(file_path)
    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    if path.suffix.lower() != ".pdf":
        return f"[ERROR] Not a PDF file: {file_path}"

    try:
        doc = fitz.open(str(path))
        text_parts = []

        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(text)

        doc.close()
        return "\n".join(text_parts)

    except Exception as e:
        return f"[ERROR] Failed to parse PDF: {e}"


if __name__ == "__main__":
    # CLI usage for testing
    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <file.pdf>")
        sys.exit(1)

    text = extract_text_from_pdf(sys.argv[1])
    print(text)
