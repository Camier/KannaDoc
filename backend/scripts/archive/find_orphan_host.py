import asyncio
import urllib.parse
import subprocess
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def find_orphan():
    # 1. Get Mongo Paths
    # Note: Connecting to container IP since port not exposed
    encoded_pass = urllib.parse.quote_plus("thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac")
    MONGO_URL = f"mongodb://thesis:{encoded_pass}@172.18.0.2:27017/chat_mongodb?authSource=admin"
    client = AsyncIOMotorClient(MONGO_URL)
    db = client['chat_mongodb']
    
    print('🔍 Querying MongoDB...')
    cursor = db.files.find({'username': 'miko'}, {'minio_url': 1, 'filename': 1})
    db_files = await cursor.to_list(None)
    
    db_paths = set()
    for f in db_files:
        path = f.get('minio_url', '')
        if path.startswith('thesis/'):
            path = path.replace('thesis/', 'miko/', 1).replace('thesis_', 'miko_', 1)
        db_paths.add(path)
        
    print(f'📉 MongoDB Records: {len(db_paths)}')

    # 2. Get MinIO Paths via Docker Exec
    print('🔍 Querying MinIO...')
    # Use ls -R because find might be missing
    cmd = ["docker", "exec", "layra-minio", "ls", "-R", "/data/minio-file/miko"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    minio_paths = set()
    raw_lines = result.stdout.splitlines()
    
    current_dir = ""
    for line in raw_lines:
        line = line.strip()
        if not line: continue
        
        if line.endswith(':'):
            # It's a directory header: /data/minio-file/miko/subdir:
            current_dir = line[:-1]
        else:
            # It's a file or subdir name
            # Check if it looks like a file (ends with .pdf or .PDF)
            if line.lower().endswith('.pdf'):
                # Construct full path
                full_path = os.path.join(current_dir, line)
                # Clean to 'miko/uuid/filename'
                # full_path is /data/minio-file/miko/uuid/file.pdf
                # remove /data/minio-file/
                clean = full_path.replace('/data/minio-file/', '')
                minio_paths.add(clean)
        
    print(f'🗄️  MinIO Files: {len(minio_paths)}')
    
    # 3. Find Orphan
    orphans = minio_paths - db_paths
    
    if orphans:
        print(f'\n👻 Found {len(orphans)} ORPHAN file(s) in MinIO (missing from DB):')
        for o in orphans:
            print(f' - {o}')
            
        # 4. Generate Repair Script
        print("\n🛠️  Generating repair script for orphans...")
        # (This part would be where we generate the restore call)
    else:
        print('\n✅ No orphan files found. MinIO and MongoDB are synced.')

    client.close()

if __name__ == "__main__":
    asyncio.run(find_orphan())
