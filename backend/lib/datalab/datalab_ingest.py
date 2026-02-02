import os
import json
import requests
import logging
import shutil
import time
from pathlib import Path
from datetime import datetime
from .datalab_utils import validate_file_size, calculate_sha256_file, validate_api_key_format, sanitize_path_component

# Configuration
ROOT_DIR = Path('/LAB/@thesis/datalab')
DATA_DIR = ROOT_DIR / 'data'
PDF_DIR = ROOT_DIR / 'ALL_FLAT'
CATALOG_FILE = DATA_DIR / 'catalog.json'
CATALOG_BACKUP_DIR = DATA_DIR / '.catalog_backups'
API_KEY_FILE = DATA_DIR / '.datalab_api_key'
LOG_DIR = DATA_DIR / 'logs'

# Setup logging
LOG_DIR.mkdir(exist_ok=True, parents=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / 'datalab_ingest.log')
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# =============================
# Configuration & Catalog Management
# =============================

def get_api_key():
    """Load and validate API key from env var or file."""
    # 1. Try Environment Variable (Preferred)
    env_key = os.environ.get("DATALAB_API_KEY")
    if env_key:
        validate_api_key_format(env_key, raise_on_invalid=True)
        return env_key.strip()

    # 2. Fallback to File (Deprecated)
    if not API_KEY_FILE.exists():
        logger.error(f"API key file not found: {API_KEY_FILE}")
        raise FileNotFoundError(f"API key file missing: {API_KEY_FILE}")

    logger.warning(f"Loading API key from file {API_KEY_FILE}. This method is deprecated. Please use DATALAB_API_KEY env var.")
    api_key = API_KEY_FILE.read_text().strip()
    if not api_key:
        logger.error("API key file is empty")
        raise ValueError("API key is empty")

    validate_api_key_format(api_key, raise_on_invalid=True)

    return api_key

def calculate_sha256_file_hash(file_path, chunk_size: int = 1024 * 1024) -> str:
    """
    Calculate SHA-256 hash of file for deduplication.
    Wrapper function for consistency with module naming.
    """
    return calculate_sha256_file(file_path, chunk_size)

def load_catalog():
    """Load catalog with recovery from corruption."""
    if not CATALOG_FILE.exists():
        logger.info("Catalog does not exist, creating new one")
        return {}

    # Create backup before parsing attempt
    try:
        CATALOG_BACKUP_DIR.mkdir(exist_ok=True, parents=True)
        backup_path = CATALOG_BACKUP_DIR / f"catalog.pre_parse.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(CATALOG_FILE, backup_path)
        logger.debug(f"Created pre-parse backup: {backup_path}")
    except Exception as backup_err:
        logger.warning(f"Failed to create pre-parse backup: {backup_err}")

    try:
        with open(CATALOG_FILE, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        logger.info(f"Loaded catalog with {len(catalog)} entries")
        return catalog
    except json.JSONDecodeError as e:
        logger.error(f"Catalog file corrupted: {e}")
        
        # Attempt recovery: backup corrupt file
        CATALOG_BACKUP_DIR.mkdir(exist_ok=True, parents=True)
        backup_path = CATALOG_BACKUP_DIR / f"catalog.corrupt.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            shutil.copy(CATALOG_FILE, backup_path)
            logger.info(f"Backed up corrupt catalog to {backup_path}")
        except Exception as copy_err:
            logger.error(f"Failed to backup corrupt catalog: {copy_err}")
        
        logger.warning("Starting with empty catalog. Manual recovery may be needed.")
        return {}

def save_catalog(catalog, incremental=False):
    """Save catalog to disk safely."""
    try:
        # Write to temporary file first (atomic write)
        temp_file = CATALOG_FILE.with_suffix('.json.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        
        # Atomic rename
        temp_file.replace(CATALOG_FILE)
        
        action = "incremental save" if incremental else "full save"
        logger.info(f"Catalog {action}: {len(catalog)} entries")
    except Exception as e:
        logger.error(f"Failed to save catalog: {e}")
        raise

def create_catalog_backup():
    """Create timestamped backup of current catalog."""
    if not CATALOG_FILE.exists():
        return None
    
    try:
        CATALOG_BACKUP_DIR.mkdir(exist_ok=True, parents=True)
        backup_path = CATALOG_BACKUP_DIR / f"catalog.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(CATALOG_FILE, backup_path)
        logger.info(f"Created catalog backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

# =============================
# Upload Functions
# =============================

def upload_file(file_path, api_key, max_retries=3):
    """
    Upload file to Datalab with retry logic and verification.

    Returns:
        (reference, file_id) tuple on success
        (None, None) on failure
    """
    file_path = Path(file_path)

    # Validate file size before processing
    validate_file_size(file_path)

    file_size = file_path.stat().st_size
    filename = file_path.name

    logger.info(f"Uploading {filename} ({file_size / 1024:.1f} KB)")
    
    for attempt in range(max_retries):
        try:
            # Step 1: Request upload URL
            headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
            init_payload = {"filename": filename, "content_type": "application/pdf"}
            
            logger.debug(f"Step 1: Requesting upload URL (attempt {attempt + 1})")
            r_init = requests.post(
                "https://www.datalab.to/api/v1/files/upload",
                headers=headers,
                json=init_payload,
                timeout=30
            )
            
            if r_init.status_code == 409:
                # File already exists
                logger.info(f"File already uploaded (409): {filename}")
                data = r_init.json()
                return data.get("reference"), data.get("file_id")
            
            r_init.raise_for_status()
            data = r_init.json()
            
            upload_url = data.get("upload_url")
            file_id = data.get("file_id")
            reference = data.get("reference")
            
            if not all([upload_url, file_id, reference]):
                logger.error(f"Incomplete response from upload init: {data}")
                continue
            
            # Step 2: Upload binary file
            logger.debug(f"Step 2: Uploading binary ({file_size / 1024:.1f} KB)")
            with open(file_path, "rb") as f:
                put_headers = {"Content-Type": "application/pdf"}
                r_put = requests.put(
                    upload_url,
                    data=f,
                    headers=put_headers,
                    timeout=300  # Allow long uploads
                )
            
            if r_put.status_code not in [200, 204]:
                logger.warning(f"Upload returned {r_put.status_code}, retrying...")
                continue
            
            logger.debug(f"Step 3: Confirming upload")
            r_conf = requests.get(
                f"https://www.datalab.to/api/v1/files/{file_id}/confirm",
                headers={"X-API-Key": api_key},
                timeout=30
            )
            
            if r_conf.status_code != 200:
                logger.warning(f"Confirmation returned {r_conf.status_code}, retrying...")
                continue
            
            logger.info(f"✅ Upload successful: {reference}")
            return reference, file_id
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout during upload (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            error_text = e.response.text[:200]
            
            if status_code == 413:  # Payload too large
                logger.error(f"File too large: {file_size / (1024*1024):.1f} MB")
                return None, None
            elif status_code == 429:  # Rate limit
                wait_time = int(e.response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"HTTP {status_code}: {error_text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
        
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue
    
    logger.error(f"Failed to upload {filename} after {max_retries} attempts")
    return None, None

# =============================
# Main Ingestion
# =============================

def ingest_pdfs():
    """
    Scan PDF directory and upload new files.
    """
    logger.info("=" * 60)
    logger.info("Starting PDF ingestion")
    logger.info("=" * 60)
    
    # Validation
    if not PDF_DIR.exists():
        logger.error(f"PDF directory not found: {PDF_DIR}")
        print(f"❌ Error: PDF directory not found: {PDF_DIR}")
        return
    
    # Load API key
    try:
        api_key = get_api_key()
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load API key: {e}")
        print(f"❌ Error: {e}")
        return
    
    # Load catalog with backup
    create_catalog_backup()
    catalog = load_catalog()
    
    # Scan PDFs
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdfs)} PDF files")
    print(f"🔍 Scanning {len(pdfs)} PDFs in {PDF_DIR}")
    
    if not pdfs:
        logger.warning("No PDFs found in directory")
        print("⚠️  No PDFs found")
        return
    
    # Process files
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0
    failed_files = []
    
    for pdf_idx, pdf in enumerate(pdfs, 1):
        try:
            # Skip hidden files
            if pdf.name.startswith('.'):
                logger.debug(f"Skipping hidden file: {pdf.name}")
                skipped_count += 1
                continue
            
            # Calculate hash
            file_hash = calculate_sha256_file_hash(pdf)
            
            # Check if already uploaded
            if file_hash in catalog:
                entry = catalog[file_hash]
                if entry.get("status") == "uploaded":
                    logger.debug(f"Already uploaded: {pdf.name}")
                    skipped_count += 1
                    continue
            
            print(f"[{pdf_idx}/{len(pdfs)}] 📦 {pdf.name}")
            logger.info(f"Processing [{pdf_idx}/{len(pdfs)}]: {pdf.name}")
            
            # Upload
            reference, file_id = upload_file(pdf, api_key)
            
            if reference is None:
                logger.error(f"Upload failed: {pdf.name}")
                failed_files.append(pdf.name)
                failed_count += 1
                continue
            
            # Update catalog
            catalog[file_hash] = {
                "filename": pdf.name,
                "path": str(pdf),
                "file_reference": reference,
                "file_id": file_id,
                "status": "uploaded",
                "file_size": pdf.stat().st_size,
                "ingested_at": datetime.utcnow().isoformat() + "Z",
                "sha256_hash": file_hash
            }
            
            uploaded_count += 1
            logger.info(f"✅ Uploaded: {pdf.name} → {reference}")
            
            # Save catalog every 10 files (or at end)
            if uploaded_count % 10 == 0 or pdf_idx == len(pdfs):
                try:
                    save_catalog(catalog, incremental=True)
                except Exception as e:
                    logger.error(f"Failed to save catalog: {e}")
                    print(f"⚠️  Warning: Could not save catalog: {e}")
        
        except KeyboardInterrupt:
            logger.info("Ingestion interrupted by user")
            print("\n⚠️  Ingestion interrupted")
            # Save catalog before exiting
            try:
                save_catalog(catalog, incremental=False)
                logger.info("Catalog saved after interrupt")
            except Exception as e:
                logger.error(f"Failed to save catalog on interrupt: {e}")
            break
        
        except Exception as e:
            logger.error(f"Error processing {pdf.name}: {e}", exc_info=True)
            failed_files.append(pdf.name)
            failed_count += 1
            continue
    
    # Final save
    try:
        save_catalog(catalog, incremental=False)
    except Exception as e:
        logger.error(f"Failed to save catalog at end: {e}")
        print(f"⚠️  Could not save final catalog: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INGESTION SUMMARY")
    print("=" * 60)
    print(f"Total PDFs:    {len(pdfs)}")
    print(f"Uploaded:      {uploaded_count}")
    print(f"Skipped:       {skipped_count}")
    print(f"Failed:        {failed_count}")
    print(f"Catalog size:  {len(catalog)}")
    
    if failed_files:
        print(f"\n❌ Failed files:")
        for filename in failed_files[:10]:  # Show first 10
            print(f"   - {filename}")
        if len(failed_files) > 10:
            print(f"   ... and {len(failed_files) - 10} more")
    
    logger.info(f"Ingestion complete: {uploaded_count} uploaded, {skipped_count} skipped, {failed_count} failed")
    print("=" * 60)

if __name__ == "__main__":
    ingest_pdfs()
