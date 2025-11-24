import os
import fitz
import pytesseract
import re
from PIL import Image
import pandas as pd
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

DEBUG_OCR_FOLDER = "./ocr_debug"
os.makedirs(DEBUG_OCR_FOLDER, exist_ok=True)

def get_visual_rotation(img, logger=None):
    """
    Uses Tesseract OSD to detect visual rotation (0, 90, 180, 270).
    """
    try:
        osd = pytesseract.image_to_osd(img)
        rotate_match = re.search(r'(?<=Rotate: )\d+', osd)
        if rotate_match:
            return int(rotate_match.group(0))
    except Exception as e:
        if logger:
            logger.debug(f"OSD check failed: {e}")
    return 0

def correct_orientation(img, logger):
    """
    Rotates image based on OSD detection.
    """
    rotation = get_visual_rotation(img, logger)
    if rotation != 0:
        logger.info(f"      ⟳ Detected page rotation: {rotation}°. Correcting...")
        img = img.rotate(-rotation, expand=True)
    else:
        logger.info("      ✓ Page orientation looks correct.")
    return img

def preprocess_image_for_ocr(image):
    """
    Standard preprocessing: Grayscale -> Thresholding -> Denoising
    """
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    return Image.fromarray(denoised)

def assign_to_column(x_center, width):
    """
    Maps an X-coordinate (0.0 to 1.0) to a Form 1 Column Index (0-6).
    Based on standard Form 1 layout percentages.
    """
    # Column Boundaries (Percentage of page width)
    # Ref #       | Desc.        | Pet. Val | Est. Net | Aban. | Sale/Fund | Asset Fully
    # 0% - 4%     | 4% - 38%     | 38% - 50%| 50% - 62%| 62-70%| 70% - 86% | 86% - 100%
    
    if x_center < 0.045: return 0  # Ref #
    if x_center < 0.390: return 1  # Asset Description
    if x_center < 0.510: return 2  # Petition Value
    if x_center < 0.630: return 3  # Estimated Net Value
    if x_center < 0.710: return 4  # Property Abandoned
    if x_center < 0.870: return 5  # Sale/Funds
    return 6                       # Asset Fully Administered

def extract_table_via_ocr(pdf_path, page_number, logger):
    """
    Extracts table data using Spatial Binning to fix alignment issues.
    """
    try:
        logger.info(f"🔍 Attempting Spatial OCR extraction on page {page_number+1}")
        
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        
        # 1. Render High DPI Image
        mat = fitz.Matrix(300/72, 300/72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # 2. Correct Orientation
        img = correct_orientation(img, logger)
        img_width, img_height = img.size

        # 3. Preprocess
        processed_img = preprocess_image_for_ocr(img)
        
        # Save debug image
        debug_img_path = os.path.join(DEBUG_OCR_FOLDER, f"{os.path.basename(pdf_path)}_page_{page_number+1}.png")
        processed_img.save(debug_img_path)

        # 4. Get Data with Bounding Boxes
        ocr_data = pytesseract.image_to_data(
            processed_img, 
            output_type=pytesseract.Output.DICT,
            config='--psm 6' # Assume uniform block of text
        )
        
        # 5. Group Text into Rows and Columns
        rows = {}
        
        num_items = len(ocr_data['text'])
        for i in range(num_items):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            if text and conf > 30:
                # Get coordinates
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                # Calculate relative position (0.0 to 1.0)
                x_center = (x + w/2) / img_width
                
                # Determine Column Index
                col_idx = assign_to_column(x_center, img_width)
                
                # Group by Y-coordinate (Row)
                # We bin rows by 15 pixels to handle slight misalignments
                row_key = y // 15 
                
                if row_key not in rows:
                    # Initialize empty row with 7 columns
                    rows[row_key] = {c: [] for c in range(7)}
                
                rows[row_key][col_idx].append(text)

        # 6. Convert to DataFrame
        # Sort rows by vertical position
        sorted_row_keys = sorted(rows.keys())
        
        data = []
        for key in sorted_row_keys:
            row_data = rows[key]
            # Join text lists into strings for each column
            clean_row = [
                " ".join(row_data[col]) if row_data[col] else "" 
                for col in range(7)
            ]
            # Filter out empty rows or noise
            if any(clean_row):
                data.append(clean_row)

        # Define Standard Headers
        headers = [
            "Ref #", 
            "Asset Description", 
            "Petition/Unscheduled Values", 
            "Estimated Net Value", 
            "Property Abandoned", 
            "Sale/Funds", 
            "Asset Fully Administered"
        ]

        if data:
            df = pd.DataFrame(data, columns=headers)
            
            # Optional: Drop rows that look like page headers/footers (noise)
            # e.g., rows containing "Form 1", "Page:", etc.
            df = df[~df["Asset Description"].str.contains("Asset Description|Form 1|Page:", case=False, na=False)]
            
            logger.info(f"✅ Spatial OCR extraction successful: {len(df)} rows")
            return df, "spatial_ocr"
            
        return None, None
        
    except Exception as e:
        logger.error(f"❌ OCR extraction failed: {str(e)}")
        return None, None