import os
import pandas as pd
from pathlib import Path

# Adjust imports based on your folder structure
from form1_pipeline.logger import setup_logger
from form1_pipeline.locator import find_form1_pages
from form1_pipeline.tables import extract_form1_table

# Configuration
PDF_FOLDER = "./data"
OUTPUT_FOLDER = "./output"  
OUTPUT_LOG = "extraction_log.csv"

# Ensure output exists
Path(OUTPUT_FOLDER).mkdir(exist_ok=True)
logger = setup_logger()
log_entries = []

logger.info("Starting Batch Extraction Process...")

# Process every PDF in the folder
for file in os.listdir(PDF_FOLDER):
    if not file.endswith(".pdf"):
        continue

    pdf_path = os.path.join(PDF_FOLDER, file)
    filename_clean = file.replace(".pdf", "")
    
    logger.info(f"Processing: {file}")

    try:
        # STEP 1: Classify pages (Must have 2+ keywords)
        target_pages = find_form1_pages(pdf_path, logger)

        if not target_pages:
            log_entries.append({"filename": file, "status": "SKIPPED (No Keywords)"})
            continue

        # STEP 2: Extract Data from identified pages
        all_dfs = []
        for page_num in target_pages:
            df, method = extract_form1_table(pdf_path, page_num, logger)
            if df is not None and not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            logger.warning(f"❌ Pages found, but no table data extracted for {file}")
            log_entries.append({"filename": file, "status": "FAILED (Extraction)"})
            continue

        # STEP 3: Combine and Write to Excel
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df = final_df.dropna(how='all').reset_index(drop=True)

        output_path = os.path.join(OUTPUT_FOLDER, f"{filename_clean}.xlsx")
        final_df.to_excel(output_path, index=False, sheet_name="Form 1 Data")
        
        logger.info(f"✅ Saved to: {output_path}")

        # STEP 4: Log Success
        log_entries.append({
            "filename": file,
            "status": "SUCCESS",
            "pages": target_pages,
            "rows": len(final_df),
            "output": output_path
        })

    except Exception as e:
        logger.error(f"Error on {file}: {str(e)}")
        log_entries.append({"filename": file, "status": "ERROR", "error": str(e)})

# Save final log summary
pd.DataFrame(log_entries).to_csv(OUTPUT_LOG, index=False)
logger.info("Process Completed.")