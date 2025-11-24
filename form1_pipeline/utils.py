import re
import fitz 
import pytesseract
from PIL import Image
import io

def get_page_rotation(pdf_path, page_number):
    """
    Returns the rotation angle of a PDF page.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    return page.rotation


def normalize_text(text):
    """Uppercases and removes excessive whitespace."""
    if not text:
        return ""
    text = text.upper()
    text = re.sub(r"\s+", " ", text)
    return text.strip()



