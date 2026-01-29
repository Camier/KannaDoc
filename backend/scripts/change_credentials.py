import asyncio
import argparse
import os
import uuid
from sqlalchemy import select
from app.db.mysql_session import mysql
from app.models.user import User
from app.core.security import get_password_hash
from app.db.mongo import get_mongo
from app.core.config import settings

async def update_or_create_user(username, password, email=None):
    if not email:
        email = f"{username}@example.com"

    # 1. MySQL Operation
    async with mysql.async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        hashed_pw = get_password_hash(password)

        if user:
            print(f"🔄 User '{username}' found in MySQL. Updating password...")
            user.hashed_password = hashed_pw
            user.password_migration_required = False
        else:
            print(f"🆕 User '{username}' not found in MySQL. Creating new user...")
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_pw,
                password_migration_required=False
            )
            session.add(user)
        
        try:
            await session.commit()
            print(f"✅ MySQL: Successfully {'updated' if user.id else 'created'} user '{username}'.")
        except Exception as e:
            print(f"❌ MySQL Error: {e}")
            await session.rollback()
            return

    # 2. MongoDB Operation (Model Config)
    try:
        mongo = await get_mongo()
        existing_config = await mongo.db.model_config.find_one({"username": username})
        
        if not existing_config:
            print(f"⚙️ MongoDB: Creating default model config for '{username}'...")
            
            # Get default model from environment or use fallback
            default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
            default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
            
            # Get API key from environment (provider-specific)
            api_key_env = {
                "openai": "OPENAI_API_KEY",
                "deepseek": "DEEPSEEK_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY"
            }
            
            api_key = os.getenv(api_key_env.get(default_provider, "OPENAI_API_KEY"), "")
            if not api_key:
                print(f"⚠️ Warning: No API key found for {default_provider}. Set {api_key_env.get(default_provider)} in .env")
                api_key = "PLEASE_SET_API_KEY_IN_ENV"
            
            model_id = username + "_" + str(uuid.uuid4())
            await mongo.create_model_config(
                username=username,
                selected_model=model_id,
                model_id=model_id,
                model_name=default_model,
                model_url="",  # Empty = auto-detect provider from model name
                api_key=api_key,
                base_used=[],
                system_prompt="You are a helpful assistant.",
                temperature=0.6,
                max_length=4096,
                top_P=0.9,
                top_K=5,
                score_threshold=60
            )
            print(f"✅ MongoDB: Config created with model '{default_model}' (provider: {default_provider})")
        else:
            print("ℹ️ MongoDB: Config already exists.")
            
    except Exception as e:
        print(f"⚠️ MongoDB Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Layra users")
    parser.add_argument("username", help="Username")
    parser.add_argument("password", help="Password")
    parser.add_argument("--email", help="Email (optional, default: username@example.com)", default=None)
    
    args = parser.parse_args()
    
    asyncio.run(update_or_create_user(args.username, args.password, args.email))
