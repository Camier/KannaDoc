import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
DB_URL = os.getenv("DB_URL")
MONGODB_DB = os.getenv("MONGODB_DB", "chat_mongodb")
MONGODB_URL = os.getenv("MONGODB_URL")

async def main():
    print("="*60)
    print("LAYRA SYSTEM DATA REPORT")
    print("="*60)

    # 1. MySQL: Users
    print("\n[USER ACCOUNTS]")
    print(f"{ 'ID':<5} {'Username':<20} {'Email':<30}")
    print("-" * 70)

    users = []

    try:
        engine = create_async_engine(DB_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT id, username, email FROM users"))
            users = result.fetchall()
            for u in users:
                # Handle None values
                uid = u[0]
                uname = u[1]
                email = u[2] if u[2] else "-"
                print(f"{uid:<5} {uname:<20} {email:<30}")
        await engine.dispose()
    except Exception as e:
        print(f"Error fetching users: {e}")

    # 2. MongoDB: KBs and Workflows
    print("\n[KNOWLEDGE BASES & WORKFLOWS]")

    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[MONGODB_DB]
        
        usernames = [u[1] for u in users]
        mongo_users = await db.knowledge_bases.distinct("username")
        all_usernames = sorted(list(set(usernames + mongo_users)))
        
        for username in all_usernames:
            print(f"\nUser: {username}")
            
            # KBs
            kbs = await db.knowledge_bases.find({"username": username}).to_list(None)
            if kbs:
                print(f"  Knowledge Bases ({len(kbs)}):")
                for kb in kbs:
                    kb_id = kb.get("knowledge_base_id")
                    file_count = await db.files.count_documents({"knowledge_base_id": kb_id})
                    print(f"    - {kb.get('knowledge_base_name')} (Files: {file_count})")
                    print(f"      ID: {kb_id}")
            else:
                print("  Knowledge Bases: None")

            # Workflows
            wfs = await db.workflows.find({"username": username}).to_list(None)
            if wfs:
                print(f"  Workflows ({len(wfs)}):")
                for wf in wfs:
                    print(f"    - {wf.get('workflow_name')}")
                    print(f"      ID: {wf.get('workflow_id')}")
            else:
                print("  Workflows: None")

    except Exception as e:
        print(f"Error fetching MongoDB data: {e}")

    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())