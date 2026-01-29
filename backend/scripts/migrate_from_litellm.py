"""
Migration Script: Remove LiteLLM Dependency
Migrates model_config documents from LiteLLM proxy URLs to direct provider APIs
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.mongo import get_mongo
from app.core.logging import logger


# Provider URL mapping
PROVIDER_MAPPINGS = {
    "gpt": "openai",
    "openai": "openai",
    "deepseek": "deepseek",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gemini": "gemini",
}

PROVIDER_API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def detect_provider(model_name: str) -> str:
    """Detect provider from model name"""
    model_lower = model_name.lower()
    for pattern, provider in PROVIDER_MAPPINGS.items():
        if pattern in model_lower:
            return provider
    return "openai"  # Default


async def migrate_model_configs():
    """Migrate all model_config documents"""
    mongo = await get_mongo()
    
    # Find all configs using LiteLLM proxy
    configs = await mongo.db.model_config.find({
        "model_url": {"$regex": "litellm"}
    }).to_list(None)
    
    if not configs:
        print("✅ No LiteLLM configs found. Nothing to migrate.")
        return
    
    print(f"📋 Found {len(configs)} config(s) using LiteLLM proxy")
    print()
    
    migrated = 0
    errors = 0
    
    for config in configs:
        username = config.get("username", "unknown")
        model_name = config.get("model_name", "")
        old_url = config.get("model_url", "")
        old_key = config.get("api_key", "")
        
        print(f"🔄 Migrating user '{username}':")
        print(f"   Model: {model_name}")
        print(f"   Old URL: {old_url}")
        
        # Detect provider
        provider = detect_provider(model_name)
        print(f"   Detected Provider: {provider}")
        
        # Get API key from environment
        env_key = PROVIDER_API_KEYS.get(provider)
        new_api_key = os.getenv(env_key, "")
        
        if not new_api_key:
            print(f"   ⚠️ Warning: {env_key} not set in environment")
            new_api_key = f"PLEASE_SET_{env_key}"
        
        # Update document
        try:
            result = await mongo.db.model_config.update_one(
                {"_id": config["_id"]},
                {
                    "$set": {
                        "model_url": "",  # Empty = auto-detect
                        "api_key": new_api_key,
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"   ✅ Migrated (model_url cleared, api_key updated)")
                migrated += 1
            else:
                print(f"   ℹ️ No changes needed")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            errors += 1
        
        print()
    
    print("=" * 60)
    print(f"📊 Migration Summary:")
    print(f"   Total configs: {len(configs)}")
    print(f"   Migrated: {migrated}")
    print(f"   Errors: {errors}")
    print()
    
    if errors == 0:
        print("✅ Migration completed successfully!")
        print()
        print("⚠️ IMPORTANT: Make sure to set API keys in .env:")
        for provider, env_key in PROVIDER_API_KEYS.items():
            key_set = "✓" if os.getenv(env_key) else "✗"
            print(f"   [{key_set}] {env_key}")
    else:
        print("⚠️ Migration completed with errors. Check logs above.")


async def verify_migration():
    """Verify migration results"""
    mongo = await get_mongo()
    
    # Count remaining LiteLLM configs
    remaining = await mongo.db.model_config.count_documents({
        "model_url": {"$regex": "litellm"}
    })
    
    # Count direct configs (empty model_url)
    direct = await mongo.db.model_config.count_documents({
        "model_url": ""
    })
    
    print("🔍 Verification:")
    print(f"   Configs still using LiteLLM: {remaining}")
    print(f"   Configs using direct providers: {direct}")
    print()
    
    if remaining == 0:
        print("✅ All configs migrated successfully!")
    else:
        print(f"⚠️ {remaining} config(s) still reference LiteLLM")


async def main():
    """Main migration flow"""
    print("=" * 60)
    print("LiteLLM Removal Migration")
    print("=" * 60)
    print()
    
    # Check environment
    print("📋 Checking environment...")
    all_keys_set = True
    for provider, env_key in PROVIDER_API_KEYS.items():
        if os.getenv(env_key):
            print(f"   ✓ {env_key} is set")
        else:
            print(f"   ✗ {env_key} NOT set (will use placeholder)")
            all_keys_set = False
    print()
    
    if not all_keys_set:
        print("⚠️ Warning: Not all API keys are set. Migration will continue,")
        print("   but you'll need to update .env and re-run change_credentials.py")
        print()
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            return
        print()
    
    # Run migration
    await migrate_model_configs()
    
    # Verify
    await verify_migration()
    
    print()
    print("=" * 60)
    print("Next Steps:")
    print("1. Update .env with provider API keys (if not already set)")
    print("2. Test chat functionality: docker exec layra-backend pytest tests/")
    print("3. Verify litellm_net is removed from docker-compose.yml (and any overrides)")
    print("4. Stop LiteLLM service: cd /LAB/@litellm && docker-compose down")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
