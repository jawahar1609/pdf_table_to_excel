import fitz  # PyMuPDF

def classify_page(pdf_path, page_number, logger):
    doc = fitz.open(pdf_path)
    page = doc[page_number]

    blocks = page.get_text("blocks")
    images = page.get_images()

    text_area = sum([b[2] * b[3] for b in blocks]) if blocks else 0
    image_area = len(images) * 50000  # rough proxy area per image

    total_area = text_area + image_area + 1
    ratio = text_area / total_area

    logger.info(
        f"Page {page_number+1} → Text/Image Ratio: {ratio:.2f}"
    )

    if ratio > 0.6:
        logger.info("✅ Likely machine-readable")
        return "text"
    else:
        logger.warning("⚠️ Likely scanned/image heavy")
        return "image"
