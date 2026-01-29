"""
Migrate existing LiteLLM-based configurations to direct provider API.
This script updates conversation configurations to use the new provider_client architecture.
"""
import asyncio
import os
import sys

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.mongo import get_mongo
from app.rag.provider_client import get_provider_for_model
from app.core.logging import logger


async def migrate_conversation_configs():
    """Migrate existing conversation configurations to use provider detection."""
    db = await get_mongo()
    
    # Query all conversations that have model_config
    query = {"model_config": {"$exists": True}}
    conversations = await db.db["conversations"].find(query).to_list(None)
    
    migrated = 0
    skipped = 0
    errors = 0
    
    logger.info(f"Found {len(conversations)} conversations with model_config")
    
    for conv in conversations:
        try:
            model_config = conv.get("model_config", {})
            old_model = model_config.get("model_name", "gpt-4o-mini")
            
            # Detect provider for new architecture
            provider = get_provider_for_model(old_model)
            
            # Check if provider is already set
            if model_config.get("provider") == provider:
                skipped += 1
                continue
            
            # Update configuration
            model_config["provider"] = provider
            
            # Ensure base_used is set (default to empty list)
            if "base_used" not in model_config:
                model_config["base_used"] = []
            
            # Save updated configuration
            await db.db["conversations"].update_one(
                {"_id": conv["_id"]},
                {"$set": {"model_config": model_config}}
            )
            
            logger.info(f"Migrated: {conv['_id']} ({old_model} -> provider: {provider})")
            migrated += 1
            
        except Exception as e:
            logger.error(f"Error migrating conversation {conv.get('_id')}: {str(e)}")
            errors += 1
    
    logger.info(f"\nMigration Summary:")
    logger.info(f"  Migrated: {migrated}")
    logger.info(f"  Skipped: {skipped} (already configured)")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Total: {len(conversations)}")


async def verify_migration():
    """Verify that conversations have valid provider configurations."""
    db = await get_mongo()
    
    # Count conversations with and without provider
    total = await db.db["conversations"].count_documents({})
    with_provider = await db.db["conversations"].count_documents({"model_config.provider": {"$exists": True}})
    without_provider = total - with_provider
    
    logger.info(f"\nVerification:")
    logger.info(f"  Total conversations: {total}")
    logger.info(f"  With provider: {with_provider}")
    logger.info(f"  Without provider: {without_provider}")
    
    # Check for invalid models (models without corresponding provider)
    all_convs = await db.db["conversations"].find({}).to_list(None)
    invalid_count = 0
    
    for conv in all_convs:
        model_config = conv.get("model_config", {})
        model_name = model_config.get("model_name", "")
        provider = model_config.get("provider", "")
        
        if model_name:
            detected = get_provider_for_model(model_name)
            if provider != detected:
                logger.warning(f"  Mismatch detected: {conv['_id']} - model: {model_name}, configured: {provider}, detected: {detected}")
                invalid_count += 1
    
    if invalid_count == 0:
        logger.info("  All configurations are valid!")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("LAYRA v2.0.0 - Model Configuration Migration")
    print("=" * 60)
    
    # Run migration
    await migrate_conversation_configs()
    
    # Verify migration
    await verify_migration()
    
    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
