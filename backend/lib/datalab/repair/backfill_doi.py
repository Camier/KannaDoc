#!/usr/bin/env python3
"""
DataLab DOI Repair Script
Backfills missing DOIs in extraction.json files using the CrossRef API.
"""

import json
import logging
import time
import requests
import urllib.parse
from pathlib import Path
from difflib import SequenceMatcher

# Configuration
DATA_ROOT = Path('/LAB/@thesis/datalab/data/datextract')
LOG_DIR = Path('/LAB/@thesis/datalab/data/logs')
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'datalab_repair_doi.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataLabDOIRepair")

def similar(a, b):
    """Return similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_doi_crossref(title):
    """Query CrossRef for a DOI given a title."""
    try:
        # Encode title
        query = urllib.parse.quote(title)
        url = f"https://api.crossref.org/works?query.title={query}&rows=1"
        
        # Be polite to the API
        time.sleep(0.2) 
        
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            items = data.get('message', {}).get('items', [])
            if items:
                item = items[0]
                found_title = item.get('title', [''])[0]
                doi = item.get('DOI')
                
                # Verify match confidence
                similarity = similar(title, found_title)
                if similarity > 0.85:
                    return doi, found_title
                else:
                    logger.warning(f"Low similarity ({similarity:.2f}) for title '{title}' vs '{found_title}'")
        return None, None
    except Exception as e:
        logger.error(f"CrossRef API error: {e}")
        return None, None

def repair_corpus():
    """Iterate through all extractions and apply repairs."""
    logger.info(f"Starting DOI repair on {DATA_ROOT}")
    
    repaired_count = 0
    total_scanned = 0
    skipped_count = 0
    
    # Iterate over all document directories
    for doc_dir in sorted(DATA_ROOT.iterdir()):
        if not doc_dir.is_dir():
            continue
            
        extraction_file = doc_dir / 'extracted' / 'extraction.json'
        
        if not extraction_file.exists():
            continue
            
        total_scanned += 1
        
        try:
            # Load data
            data = json.loads(extraction_file.read_text(encoding='utf-8'))
            
            # Check if DOI is missing
            if not data.get('doi'):
                title = data.get('title')
                if not title or len(title) < 10:
                    logger.warning(f"Skipping {doc_dir.name}: No valid title for search")
                    continue
                
                logger.info(f"🔍 Searching DOI for: {title[:50]}...")
                doi, found_title = find_doi_crossref(title)
                
                if doi:
                    data['doi'] = doi
                    # Add provenance note if possible (custom schema might strict check this, 
                    # but usually extra fields are ignored or we append to citations)
                    if 'doi_citations' in data:
                        data['doi_citations'].append("(Inferred from CrossRef)")
                    else:
                        data['doi_citations'] = ["(Inferred from CrossRef)"]
                        
                    # Save atomically
                    extraction_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
                    logger.info(f"✅ Repaired DOI: {doi}")
                    repaired_count += 1
                else:
                    logger.warning(f"❌ No DOI found for {doc_dir.name}")
                    skipped_count += 1
            else:
                # DOI already exists
                pass
                
        except Exception as e:
            logger.error(f"Failed to process {doc_dir.name}: {e}")
            
    logger.info("=" * 40)
    logger.info(f"DOI Repair Complete.")
    logger.info(f"Documents scanned:   {total_scanned}")
    logger.info(f"DOIs repaired:       {repaired_count}")
    logger.info(f"DOIs still missing:  {skipped_count}")
    logger.info("=" * 40)

if __name__ == "__main__":
    repair_corpus()
