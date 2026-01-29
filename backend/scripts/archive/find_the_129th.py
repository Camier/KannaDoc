import asyncio
import urllib.parse
from motor.motor_asyncio import AsyncIOMotorClient

async def find_all():
    MONGO_PASS = urllib.parse.quote_plus("thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac")
    MONGO_URL = f"mongodb://thesis:{MONGO_PASS}@mongodb:27017/chat_mongodb?authSource=admin"
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["chat_mongodb"]
    
    print("🚀 Scanning ENTIRE files collection...")
    
    # Get everything
    cursor = db.files.find({}, {"filename": 1, "original_filename": 1, "username": 1, "file_id": 1})
    all_files = await cursor.to_list(None)
    
    print(f"📊 Total Records found: {len(all_files)}")
    
    unique_filenames = set()
    file_map = {} # filename -> list of records
    
    for f in all_files:
        name = f.get("filename") or f.get("original_filename")
        if not name: continue
        
        unique_filenames.add(name)
        if name not in file_map:
            file_map[name] = []
        file_map[name].append(f)
        
    print(f"🧩 Total UNIQUE filenames: {len(unique_filenames)}")
    
    # We know the miko user has 128. Let's get that set specificially.
    miko_set = set()
    for f in all_files:
        if f.get("username") == "miko":
            name = f.get("filename") or f.get("original_filename")
            miko_set.add(name)
            
    print(f"👤 Miko UNIQUE filenames: {len(miko_set)}")
    
    # Find the difference
    diff = unique_filenames - miko_set
    
    if diff:
        print(f"\n🔥 FOUND {len(diff)} FILES NOT IN MIKO'S LIST:")
        for name in diff:
            print(f" - {name}")
            # details
            recs = file_map[name]
            for r in recs:
                print(f"   ↳ ID: {r['file_id']} | User: {r['username']}")
    else:
        print("\n✅ No additional unique files found in the entire database.")
        if len(miko_set) == 129:
             print("🎉 Miko actually has 129!")
        elif len(miko_set) == 128:
             print("⚠️  Miko has exactly 128. The 129th file is NOT in MongoDB.")

    client.close()

if __name__ == "__main__":
    asyncio.run(find_all())
