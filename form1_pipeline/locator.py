import os
import fitz
import pytesseract
import re
from PIL import Image
from .utils import normalize_text

# Tesseract configuration
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Define the keywords to look for
FORM1_MARKERS = [
    "FORM 1",
    "ASSET CASES",
    "INDIVIDUAL ESTATE PROPERTY RECORD AND REPORT",
    "ASSET DESCRIPTION",
    "EXHIBIT A"
]

def find_form1_pages(pdf_path, logger):
    """
    Scans PDF and returns ONLY pages that contain at least 2 Form 1 keywords.
    """
    logger.info(f"Scanning PDF for keywords: {pdf_path}")
    matched_pages = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = normalize_text(page.get_text())
        found_markers = [m for m in FORM1_MARKERS if m in text]

        if len(found_markers) > 3:
            logger.info(f"âœ… Page {i+1} confirmed (Found: {found_markers})")
            matched_pages.append(i)
        else:
            # Optional: Log rejected pages for debugging
            pass

    if not matched_pages:
        logger.warning("âš ï¸ No valid Form 1 pages detected based on keywords.")
    
    return matched_pages

def find_form1_pages_with_ocr(pdf_path, logger, debug_folder):
    """
    Scans PDF pages using OCR (for scanned docs).
    Only returns pages that contain Form 1 keywords.
    """
    logger.info(f"🔍 Starting OCR Keyword Scan for: {pdf_path}")
    matched_pages = []
    doc = fitz.open(pdf_path)

    for i, page in enumerate(doc):
        # Optimization: Check if page has images. If not, skip (it's empty or pure text)
        images = page.get_images()
        if not images:
            continue

        # Perform OCR on this page just to check for keywords
        ocr_text = ocr_scan_page(page, i, logger, debug_folder)
        found_markers = [m for m in FORM1_MARKERS if m in ocr_text]

        # Threshold: at least 2 markers for OCR (slightly lower threshold due to OCR noise)
        if len(found_markers) >= 2:
            logger.info(f"✅ Page {i+1} confirmed via OCR (Found: {found_markers})")
            matched_pages.append(i)
        
        # Optional: If we found markers, we don't need to save a debug txt for every single page 
        # unless you want to debug. The ocr_scan_page function currently saves it.

    if not matched_pages:
        logger.warning("⚠️ OCR scan completed - no Form 1 pages detected")

    return matched_pages

def ocr_scan_page(page, page_num, logger, debug_folder):
    """
    Performs OCR on a page to find text.
    """
    try:
        # Low-ish DPI for locator scan (150) to be faster, 
        # use 300 only for final extraction
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)) 
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Apply Orientation Correction
        img = correct_orientation(img, logger)

        # Run OCR
        # --psm 6 assumes a block of text, good for forms
        ocr_text = pytesseract.image_to_string(img, config='--psm 6')
        
        return normalize_text(ocr_text)

    except Exception as e:
        logger.debug(f"OCR locator failed on page {page_num+1}: {e}")
        return ""