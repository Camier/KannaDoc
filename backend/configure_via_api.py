import sys
sys.path.insert(0, '/app')
from app.db.repositories.repository_manager import get_repository_manager
import asyncio

async def configure():
    rm = await get_repository_manager()
    db = rm.db.client.chat_mongodb
    
    # Clear existing
    await db.model_config.delete_many({})
    
    # Configure just ONE model per user (due to unique constraint on username)
    model = {
        'username': 'miko',
        'chat_model': 'miko_deepseek_chat',
        'model_name': 'deepseek-chat',  # Working model from API tests
        'llm_provider': 'deepseek',
        'embedding_model': 'local_colqwen',
        'is_selected': True,
        'api_key': '',  # Will use env var
    }
    
    result = await db.model_config.insert_one(model)
    print('Inserted model config for miko')
    print('Model: deepseek-chat (deepseek)')
    print('Selected: Yes')
    
    await rm.db.close()

asyncio.run(configure())
