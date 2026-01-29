import json
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def restore():
    # Configuration from environment
    mongo_user = os.environ.get("MONGODB_ROOT_USERNAME", "root")
    mongo_pass = os.environ.get("MONGODB_ROOT_PASSWORD", "root_password")
    mongo_host = os.environ.get("MONGODB_HOST", "mongodb")
    mongo_url = f"mongodb://{mongo_user}:{mongo_pass}@{mongo_host}:27017"
    
    db_name = os.environ.get("MONGODB_DB", "chat_mongodb")
    json_path = "workflows/workflow_v5_pretty.json"
    target_kb_id = "miko_e6643365-8b03_4bea-a69b_7a1df00ec653"
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Update KB IDs in all VLM/LLM nodes
    for node in data.get('nodes', []):
        if 'modelConfig' in node.get('data', {}):
            base_used = node['data']['modelConfig'].get('base_used', [])
            for base in base_used:
                if base.get('name') == "Thesis Corpus":
                    print(f"Updating KB ID in node {node['id']}")
                    base['baseId'] = target_kb_id

    # Update username to match our current user
    data['username'] = "thesis"
    
    # Connect and Insert
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check if exists
    existing = await db.workflows.find_one({"workflow_id": data['workflow_id']})
    if existing:
        print(f"Workflow {data['workflow_id']} already exists. Updating...")
        await db.workflows.replace_one({"workflow_id": data['workflow_id']}, data)
    else:
        print(f"Inserting new workflow {data['workflow_id']}...")
        await db.workflows.insert_one(data)
    
    print("Done!")

if __name__ == "__main__":
    asyncio.run(restore())
