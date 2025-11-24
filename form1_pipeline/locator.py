import pdfplumber
from .utils import normalize_text

# Define the keywords to look for
FORM1_MARKERS = [
    "FORM 1",
    "ASSET CASES",
    "INDIVIDUAL ESTATE PROPERTY RECORD AND REPORT",
    "ASSET DESCRIPTION",
]

def find_form1_pages(pdf_path, logger):
    """
    Scans PDF and returns ONLY pages that contain at least 2 Form 1 keywords.
    """
    logger.info(f"Scanning PDF for keywords: {pdf_path}")
    matched_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Extract and clean text
            text = page.extract_text() or ""
            text_upper = normalize_text(text)

            # Check how many markers appear on this specific page
            found_markers = [m for m in FORM1_MARKERS if m in text_upper]
            
            # STRICT RULE: Must have at least 2 keywords to be classified as Form 1
            if len(found_markers) > 3:
                logger.info(f"✅ Page {i+1} confirmed (Found: {found_markers})")
                matched_pages.append(i)
            else:
                # Optional: Log rejected pages for debugging
                pass

    if not matched_pages:
        logger.warning("⚠️ No valid Form 1 pages detected based on keywords.")
    
    return matched_pages