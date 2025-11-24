import camelot
import pdfplumber
import pandas as pd
from .utils import get_page_rotation

def extract_form1_table(pdf_path, page_number, logger):
    """
    Extracts table from a single page using multiple methods.
    
    Args:
        pdf_path: Path to PDF file
        page_number: Page index (0-indexed)
        logger: Logger instance
        
    Returns:
        (DataFrame, method_name) or (None, None) if extraction fails
    """
    rotation = get_page_rotation(pdf_path, page_number)
    if rotation != 0:
        logger.info(f"Page {page_number+1} rotated: {rotation} degrees")

    logger.info(f"Attempting extraction: page {page_number+1}")

    page_str = str(page_number + 1)  # Camelot uses 1-indexed pages

    # # Method 1: Camelot Stream (best for borderless tables)
    try:
        logger.info("Trying Camelot (stream)...")
        tables = camelot.read_pdf(
            pdf_path, 
            pages=page_str, 
            flavor="stream",
            edge_tol=100,
            row_tol=10
        )

        if tables.n > 0 and not tables[0].df.empty:
            df = tables[0].df
            logger.info(f"âœ… Camelot stream: {df.shape[0]} rows, {df.shape[1]} cols")
            return df, "camelot_stream"
    except Exception as e:
        logger.debug(f"Camelot stream failed: {e}")

    # Method 2: Camelot Lattice (best for bordered tables)
    # try:
    #     logger.info("Trying Camelot (lattice)...")
    #     tables = camelot.read_pdf(
    #         pdf_path, 
    #         pages=page_str, 
    #         flavor="lattice"
    #     )

    #     if tables.n > 0 and not tables[0].df.empty:
    #         df = tables[0].df
    #         logger.info(f"Camelot lattice: {df.shape[0]} rows, {df.shape[1]} cols")
    #         return df, "camelot_lattice"
    # except Exception as e:
    #     logger.debug(f"Camelot lattice failed: {e}")

    # Method 3: pdfplumber (fallback)
    # try:
    #     logger.info("Trying pdfplumber...")
    #     with pdfplumber.open(pdf_path) as pdf:
    #         page = pdf.pages[page_number]
    #         table = page.extract_table()

    #         if table and len(table) > 0:
    #             df = pd.DataFrame(table)
    #             logger.info(f"pdfplumber: {df.shape[0]} rows, {df.shape[1]} cols")
    #             return df, "pdfplumber"
    # except Exception as e:
    #     logger.debug(f"pdfplumber failed: {e}")

    logger.error(f"All extraction methods failed for page {page_number + 1}")
    return None, None