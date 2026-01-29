import os
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BACKEND_URL = "http://localhost:8090/api"
USERNAME = "miko"
PASSWORD = "lol"
KB_ID = "thesis_34f1ab7f-5fbe-4a7a-bf73-6561f8ce1dd7"
CORPUS_DIR = "literature/corpus"

async def get_token():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/auth/login", data={
            "username": USERNAME,
            "password": PASSWORD
        })
        resp.raise_for_status()
        return resp.json()["access_token"]

async def upload_file(client, token, file_path):
    filename = os.path.basename(file_path)
    logger.info(f"Uploading {filename}...")
    
    with open(file_path, "rb") as f:
        files = {"files": (filename, f, "application/pdf")}
        resp = await client.post(
            f"{BACKEND_URL}/chat/upload/{USERNAME}/{KB_ID}",
            files=files,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0
        )
        if resp.status_code == 200:
            logger.info(f"Successfully queued {filename}")
        elif "文件ID已存在" in resp.text:
            logger.info(f"File already exists: {filename}")
        else:
            logger.error(f"Failed to upload {filename}: {resp.status_code} - {resp.text}")

async def main():
    token = await get_token()
    
    # Get all PDFs
    files = [os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if f.endswith(".pdf")]
    logger.info(f"Found {len(files)} PDFs")
    
    async with httpx.AsyncClient() as client:
        # Upload in batches to avoid overwhelming the system
        batch_size = 5
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            tasks = [upload_file(client, token, f) for f in batch]
            await asyncio.gather(*tasks)
            await asyncio.sleep(1) # Small delay between batches

if __name__ == "__main__":
    asyncio.run(main())
