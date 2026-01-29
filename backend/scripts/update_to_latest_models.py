#!/usr/bin/env python3
"""
Update to Latest Models (January 2026)
Updates model configuration to use the latest available models
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


# Latest recommended models (January 2026)
LATEST_MODELS = [
    {
        "model_name": "gpt-4o",
        "model_url": None,
        "provider": "openai",
        "description": "Primary: Latest GPT-4o (gpt-4o-mini deprecates Feb 27, 2026)"
    },
    {
        "model_name": "gpt-5.2",
        "model_url": None,
        "provider": "openai",
        "description": "Flagship: Latest GPT-5 with enhanced reasoning (Jan 2026)"
    },
    {
        "model_name": "deepseek-v3.2",
        "model_url": None,
        "provider": "deepseek",
        "description": "Reasoning: Outperforms GPT-5 on reasoning tasks (Dec 2025)"
    },
    {
        "model_name": "deepseek-r1",
        "model_url": None,
        "provider": "deepseek",
        "description": "Reasoning Specialist: Latest reasoning model (Jan 2026)"
    },
    {
        "model_name": "kimi-k2-thinking",
        "model_url": None,
        "provider": "moonshot",
        "description": "Long Context: Trillion-param K2, 256K context, 75% cheaper (Nov 2025)"
    },
    {
        "model_name": "glm-4.7",
        "model_url": None,
        "provider": "zhipu",
        "description": "Coding: 358B params, 90.1% MMLU, beats GPT-OSS-20B (Jan 2026)"
    },
    {
        "model_name": "glm-4.7-flash",
        "model_url": None,
        "provider": "zhipu",
        "description": "Economy: Speed-optimized MoE, 200K context (Jan 2026)"
    },
]


async def update_models(username: str = "thesis", dry_run: bool = False):
    """Update to latest models"""
    
    # Get MongoDB connection details
    mongo_url = os.getenv("MONGODB_URL", "mongodb:27017")
    mongo_user = os.getenv("MONGODB_ROOT_USERNAME", "thesis")
    mongo_pass = os.getenv("MONGODB_ROOT_PASSWORD")
    mongo_db = os.getenv("MONGODB_DB", "chat_mongodb")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(
        f"mongodb://{mongo_user}:{mongo_pass}@{mongo_url}/{mongo_db}?authSource=admin"
    )
    
    db = client[mongo_db]
    collection = db["model_config"]
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Updating to latest models (January 2026)...\n")
    
    # Check existing configuration
    existing = await collection.find_one({"username": username})
    
    if existing:
        print("📋 Current configuration:")
        print(f"  User: {existing.get('username')}")
        print(f"  Current default: {existing.get('model_id')}")
        print(f"  Current models: {len(existing.get('model_list', []))}\n")
        
        # Check for deprecated models
        deprecated = []
        for model in existing.get('model_list', []):
            name = model.get('model_name', '')
            if 'gpt-4o-mini' in name:
                deprecated.append(f"{name} (deprecates Feb 27, 2026!)")
            elif 'glm-4-' in name and 'glm-4.7' not in name:
                deprecated.append(f"{name} (outdated, GLM-4.7 available)")
            elif 'moonshot-v1' in name:
                deprecated.append(f"{name} (outdated, Kimi K2 available)")
            elif name in ['deepseek-chat', 'deepseek-reasoner']:
                deprecated.append(f"{name} (generic, V3.2 available)")
        
        if deprecated:
            print(f"⚠️  Deprecated/outdated models found:")
            for m in deprecated:
                print(f"  - {m}")
            print()
    
    # Build latest model list
    model_list = []
    print("✨ New configuration with latest models:\n")
    
    for idx, model in enumerate(LATEST_MODELS, 1):
        model_id = f"{username}_{model['model_name'].replace('.', '_').replace('-', '_')}_{idx}"
        
        model_config = {
            "model_id": model_id,
            "model_name": model['model_name'],
            "model_url": model['model_url'],
            "api_key": None,  # Will use env vars
            "provider": model['provider'],
            "description": model['description'],
            "created_at": datetime.utcnow().isoformat(),
            "version": "2.0.1",  # Updated version
        }
        
        model_list.append(model_config)
        
        print(f"  {idx}. {model['model_name']} ({model['provider']})")
        print(f"     {model['description']}")
        print(f"     ID: {model_id}")
        print()
    
    # Prepare document
    doc = {
        "username": username,
        "user_id": username,
        "model_id": model_list[0]['model_id'],  # Default to gpt-4o (not deprecated!)
        "model_list": model_list,
        "updated_at": datetime.utcnow().isoformat(),
        "version": "2.0.1",
    }
    
    if not dry_run:
        # Update or insert
        result = await collection.replace_one(
            {"username": username},
            doc,
            upsert=True
        )
        
        if result.matched_count > 0:
            print(f"✅ Updated configuration for {username}")
        else:
            print(f"✅ Created new configuration for {username}")
        
        print(f"   Default model: {doc['model_id']} (gpt-4o)")
        print(f"   Total models: {len(model_list)}")
        print(f"\n⚠️  IMPORTANT: gpt-4o-mini deprecates February 27, 2026")
        print(f"   Default changed to gpt-4o for safety")
    else:
        print("[DRY RUN] No changes made to database")
        print(f"\n💡 Would set default to: {doc['model_id']} (gpt-4o)")
    
    client.close()
    
    return doc


async def main():
    import sys
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    print("="*70)
    print("UPDATE TO LATEST MODELS - January 2026")
    print("="*70)
    print()
    print("🚨 CRITICAL UPDATES:")
    print("  • gpt-4o-mini → gpt-4o (mini deprecates Feb 27, 2026)")
    print("  • Added GPT-5.2 (Jan 2026 flagship)")
    print("  • glm-4.x → glm-4.7 (358B params, Jan 2026)")
    print("  • moonshot-v1 → kimi-k2-thinking (trillion params, Nov 2025)")
    print("  • deepseek-chat → deepseek-v3.2 (beats GPT-5, Dec 2025)")
    print()
    print("="*70)
    print()
    
    # Setup models
    await update_models(username="thesis", dry_run=dry_run)
    
    print("\n" + "="*70)
    
    if dry_run:
        print("\n💡 To apply changes, run without --dry-run flag")
    else:
        print("\n✅ Configuration updated to latest models!")
        print("   Test in UI: http://localhost:8090")
        print()
        print("📊 Performance improvements:")
        print("  • GLM-4.7: 358B parameters (vs GLM-4)")
        print("  • Kimi K2: Trillion params, 256K context (vs V1 128K)")
        print("  • DeepSeek V3.2: Outperforms GPT-5 on reasoning")
        print("  • GPT-5.2: Latest flagship capabilities")


if __name__ == "__main__":
    asyncio.run(main())
