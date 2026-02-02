#!/usr/bin/env python3
"""
DataLab Repair Script
Backfills missing metadata (Year, DOI) in extraction.json files using filename heuristics.
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime

# Configuration
DATA_ROOT = Path('/LAB/@thesis/datalab/data/datextract')
LOG_DIR = Path('/LAB/@thesis/datalab/data/logs')
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'datalab_repair.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataLabRepair")

def infer_year_from_filename(filename: str):
    """
    Extracts year from filenames like '2017 - Khan - Title.pdf'
    Returns integer year or None.
    """
    # Pattern: Start with 4 digits followed by ' - '
    match = re.search(r'^(\d{4})\s*-\s*', filename)
    if match:
        try:
            year = int(match.group(1))
            # Basic sanity check for year range
            if 1800 <= year <= 2030:
                return year
        except ValueError:
            pass
    return None

def repair_corpus():
    """Iterate through all extractions and apply repairs."""
    logger.info(f"Starting repair on {DATA_ROOT}")
    
    repaired_count = 0
    total_count = 0
    
    # Iterate over all document directories
    for doc_dir in sorted(DATA_ROOT.iterdir()):
        if not doc_dir.is_dir():
            continue
            
        extraction_file = doc_dir / 'extracted' / 'extraction.json'
        request_file = doc_dir / 'raw' / 'request.json'
        
        if not extraction_file.exists():
            logger.warning(f"No extraction.json found in {doc_dir.name}")
            continue
            
        total_count += 1
        
        # Load data
        try:
            data = json.loads(extraction_file.read_text(encoding='utf-8'))
            
            # Get filename for inference
            filename = None
            if request_file.exists():
                try:
                    req_data = json.loads(request_file.read_text(encoding='utf-8'))
                    input_path = req_data.get('input', '')
                    # Handle both local paths and datalab:// URLs if possible (though URL won't help much)
                    # Ideally we want the original filename.
                    # The folder name usually contains the safe version of the filename: YYYYMMDD_HHMMSS_Original_Filename
                    # Let's try to parse the folder name first as it might be easier.
                    pass
                except Exception:
                    pass
            
            # Fallback: Extract from folder name
            # Folder format: YYYYMMDD_HHMMSS_filename_stem
            # Example: 20260123_221131_2017_-_Khan_-_Quantification_of_mesembri
            folder_name = doc_dir.name
            # Strip timestamp prefix (15 chars: YYYYMMDD_HHMMSS_)
            if len(folder_name) > 16 and folder_name[8] == '_' and folder_name[15] == '_':
                name_part = folder_name[16:]
                # The folder name might have underscores instead of spaces if it was sanitized
                # But our regex `^(\d{4})\s*-\s*` handles the year part well if it starts with it.
                # Let's try to infer year from the name_part directly.
                inferred_year = infer_year_from_filename(name_part)
                
                # Try replacing underscores with spaces if direct match fails
                if inferred_year is None:
                    inferred_year = infer_year_from_filename(name_part.replace('_', ' '))
            else:
                inferred_year = None
                
            modified = False
            
            # 1. Repair Year
            if not data.get('year'):
                if inferred_year:
                    data['year'] = inferred_year
                    data['year_citations'] = ["(Inferred from filename)"]
                    modified = True
                    logger.info(f"🔧 Repaired YEAR for {doc_dir.name}: {inferred_year}")
            
            # 2. Repair DOI (Placeholder for future logic)
            # Currently we don't have a reliable offline DOI source without regexing the full text.
            # We will skip this for now to keep it low-risk.
            
            # Save if modified
            if modified:
                extraction_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                repaired_count += 1
                
        except Exception as e:
            logger.error(f"Failed to process {doc_dir.name}: {e}")
            
    logger.info("=" * 40)
    logger.info(f"Repair Complete.")
    logger.info(f"Documents processed: {total_count}")
    logger.info(f"Documents repaired:  {repaired_count}")
    logger.info("=" * 40)

if __name__ == "__main__":
    repair_corpus()
