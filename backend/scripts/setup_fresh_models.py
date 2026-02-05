#!/usr/bin/env python3
"""
Setup fresh model configurations with new providers
Removes legacy LiteLLM proxy references and configures direct API models
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


# Recommended model configurations
FRESH_MODELS = [
    {
        "model_name": "gpt-4o-mini",
        "model_url": None,  # Will use direct API
        "provider": "openai",
        "description": "Primary: Fast, capable, vision support"
    },
    {
        "model_name": "deepseek-chat",
        "model_url": None,
        "provider": "deepseek",
        "description": "Fast general purpose, good for coding"
    },
    {
        "model_name": "deepseek-reasoner",
        "model_url": None,
        "provider": "deepseek",
        "description": "Reasoning: Complex logical tasks"
    },
    {
        "model_name": "moonshot-v1-32k",
        "model_url": None,
        "provider": "moonshot",
        "description": "Backup: Long context (32k), Chinese support"
    },
    {
        "model_name": "glm-4-plus",
        "model_url": None,
        "provider": "zai",
        "description": "Coding: Strong code generation"
    },
    {
        "model_name": "glm-4-flash",
        "model_url": None,
        "provider": "zai",
        "description": "Economy: Fast, cost-effective"
    },
]


async def setup_models(username: str = "thesis", dry_run: bool = False):
    """Setup fresh model configurations"""
    
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
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Setting up fresh models for user: {username}\n")
    
    # Check existing configuration
    existing = await collection.find_one({"username": username})
    
    if existing:
        print("📋 Existing configuration found:")
        print(f"  User: {existing.get('username')}")
        print(f"  Current models: {len(existing.get('model_list', []))}")
        print(f"  Selected: {existing.get('model_id')}\n")
        
        # Check for suspicious models
        suspicious = []
        for model in existing.get('model_list', []):
            url = model.get('model_url', '')
            if url and ('172.17.0.1' in url or 'litellm' in url.lower() or ':4000' in url):
                suspicious.append(model)
        
        if suspicious:
            print(f"⚠️  Found {len(suspicious)} suspicious/legacy model(s):")
            for m in suspicious:
                print(f"  - {m.get('model_name')} → {m.get('model_url')}")
            print()
    
    # Build fresh model list
    model_list = []
    print("✨ New model configuration:\n")
    
    for idx, model in enumerate(FRESH_MODELS, 1):
        model_id = f"{username}_{model['model_name'].replace('.', '_')}_{idx}"
        
        model_config = {
            "model_id": model_id,
            "model_name": model['model_name'],
            "model_url": model['model_url'],
            "api_key": None,  # Will use env vars
            "provider": model['provider'],
            "description": model['description'],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        model_list.append(model_config)
        
        print(f"  {idx}. {model['model_name']} ({model['provider']})")
        print(f"     {model['description']}")
        print(f"     ID: {model_id}")
        print()
    
    # Prepare document
    doc = {
        "username": username,
        "user_id": username,  # For consistency
        "model_id": model_list[0]['model_id'],  # Default to first (gpt-4o-mini)
        "model_list": model_list,
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    if not dry_run:
        # Update or insert
        result = await collection.replace_one(
            {"username": username},
            doc,
            upsert=True
        )
        
        if result.matched_count > 0:
            print(f"✅ Updated existing configuration for {username}")
        else:
            print(f"✅ Created new configuration for {username}")
        
        print(f"   Default model: {doc['model_id']}")
        print(f"   Total models: {len(model_list)}")
    else:
        print("[DRY RUN] No changes made to database")
    
    client.close()
    
    return doc


async def verify_api_keys():
    """Verify required API keys are configured"""
    print("\n🔑 Verifying API keys...\n")
    
    required_keys = {
        "OPENAI_API_KEY": "OpenAI",
        "DEEPSEEK_API_KEY": "DeepSeek",
        "MOONSHOT_API_KEY": "Moonshot/Kimi",
        "ZAI_API_KEY": "Z.ai/GLM",
    }
    
    optional_keys = {
        "MINIMAX_API_KEY": "MiniMax",
        "COHERE_API_KEY": "Cohere",
        "OLLAMA_API_KEY": "Ollama",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GEMINI_API_KEY": "Google Gemini",
    }
    
    all_good = True
    
    for key, provider in required_keys.items():
        value = os.getenv(key)
        if value and len(value) > 10:
            print(f"  ✅ {provider}: Configured")
        else:
            print(f"  ❌ {provider}: MISSING (required)")
            all_good = False
    
    print()
    for key, provider in optional_keys.items():
        value = os.getenv(key)
        if value and len(value) > 10:
            print(f"  ✅ {provider}: Configured")
        else:
            print(f"  ⚠️  {provider}: Not configured (optional)")
    
    return all_good


async def main():
    import sys
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv
    
    # Verify API keys
    keys_ok = await verify_api_keys()
    
    if not keys_ok:
        print("\n⚠️  WARNING: Some required API keys are missing!")
        print("Run: bash scripts/update_api_keys.sh")
        if not dry_run:
            print("\nProceeding anyway...")
    
    print("\n" + "="*60 + "\n")
    
    # Setup models
    await setup_models(username="thesis", dry_run=dry_run)
    
    print("\n" + "="*60)
    
    if dry_run:
        print("\n💡 To apply changes, run without --dry-run flag")
    else:
        print("\n✅ Model configuration updated successfully!")
        print("   Test in UI: http://localhost:8090")


if __name__ == "__main__":
    asyncio.run(main())
