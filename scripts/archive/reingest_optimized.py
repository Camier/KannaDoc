import os
import asyncio
import httpx
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
BACKEND_URL = "http://127.0.0.1:8090/api"
USERNAME = "miko"
# Try known passwords
PASSWORDS = ["lol", "miko_password_change_this"]
KB_NAME = "Thesis Corpus Optimized"
CORPUS_DIR = "literature/corpus"

async def get_token():
    async with httpx.AsyncClient() as client:
        for pwd in PASSWORDS:
            try:
                logger.info(f"Attempting login for '{USERNAME}'...")
                # Note: OAuth2PasswordRequestForm expects data, not json
                resp = await client.post(f"{BACKEND_URL}/auth/login", data={
                    "username": USERNAME,
                    "password": pwd
                })
                if resp.status_code == 200:
                    logger.info("✅ Login successful")
                    return resp.json()["access_token"]
                else:
                    logger.warning(f"Login failed with {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.debug(f"Login attempt failed: {e}")
        
        logger.error("❌ All login attempts failed. Please check credentials.")
        sys.exit(1)

async def get_or_create_kb(token):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Get existing KBs
        resp = await client.get(f"{BACKEND_URL}/base/users/{USERNAME}/knowledge_bases", headers=headers)
        resp.raise_for_status()
        kbs = resp.json()
        
        for kb in kbs:
            if kb["knowledge_base_name"] == KB_NAME:
                logger.info(f"✅ Found existing KB: {KB_NAME} ({kb['knowledge_base_id']})")
                return kb["knowledge_base_id"]
        
        # 2. Create new KB if not found
        logger.info(f"Creating new KB: {KB_NAME}...")
        resp = await client.post(f"{BACKEND_URL}/base/knowledge_base", json={
            "username": USERNAME,
            "knowledge_base_name": KB_NAME
        }, headers=headers)
        resp.raise_for_status()
        
        # Get the ID again
        resp = await client.get(f"{BACKEND_URL}/base/users/{USERNAME}/knowledge_bases", headers=headers)
        kbs = resp.json()
        for kb in kbs:
            if kb["knowledge_base_name"] == KB_NAME:
                return kb["knowledge_base_id"]
        
        raise RuntimeError("Failed to retrieve created KB ID")

async def upload_file(client, token, kb_id, file_path):
    filename = os.path.basename(file_path)
    
    with open(file_path, "rb") as f:
        files = {"files": (filename, f, "application/pdf")}
        try:
            resp = await client.post(
                f"{BACKEND_URL}/base/upload/{kb_id}",
                files=files,
                headers={"Authorization": f"Bearer {token}"},
                timeout=120.0
            )
            if resp.status_code == 200:
                logger.info(f"✅ Queued: {filename}")
                return True
            else:
                logger.error(f"❌ Failed {filename}: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Error uploading {filename}: {e}")
            return False

async def main():
    if not os.path.exists(CORPUS_DIR):
        logger.error(f"Directory not found: {CORPUS_DIR}")
        return

    token = await get_token()
    kb_id = await get_or_create_kb(token)
    
    files = [os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if f.endswith(".pdf")]
    logger.info(f"Found {len(files)} PDFs to process")
    
    async with httpx.AsyncClient() as client:
        # Batch size 3 to avoid overloading the model server / kafka
        batch_size = 3
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(files)+batch_size-1)//batch_size}")
            tasks = [upload_file(client, token, kb_id, f) for f in batch]
            await asyncio.gather(*tasks)
            await asyncio.sleep(2)

    logger.info("=== Ingestion tasks submitted to Kafka ===")
    logger.info(f"You can check progress in the UI or by running 'docker exec layra-redis redis-cli -a <password> KEYS \"task:*\"'")

if __name__ == "__main__":
    asyncio.run(main())
