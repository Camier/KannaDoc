import asyncio
import os
import sys
sys.path.insert(0, '/app')

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def configure_models():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client.chat_mongodb
    
    await db.model_config.delete_many({})
    
    models = [
        {
            'username': 'miko',
            'chat_model': 'miko_deepseek_chat',
            'model_name': 'deepseek-chat',
            'llm_provider': 'deepseek',
            'embedding_model': 'local_colqwen',
            'is_selected': True,
            'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
        },
        {
            'username': 'miko',
            'chat_model': 'miko_deepseek_reasoner',
            'model_name': 'deepseek-reasoner',
            'llm_provider': 'deepseek',
            'embedding_model': 'local_colqwen',
            'is_selected': False,
            'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
        },
        {
            'username': 'miko',
            'chat_model': 'miko_glm4',
            'model_name': 'glm-4',
            'llm_provider': 'zhipu',
            'embedding_model': 'local_colqwen',
            'is_selected': False,
            'api_key': os.getenv('ZHIPUAI_API_KEY', ''),
        },
        {
            'username': 'miko',
            'chat_model': 'miko_glm4_plus',
            'model_name': 'glm-4-plus',
            'llm_provider': 'zhipu',
            'embedding_model': 'local_colqwen',
            'is_selected': False,
            'api_key': os.getenv('ZHIPUAI_API_KEY', ''),
        },
        {
            'username': 'miko',
            'chat_model': 'miko_glm4_flash',
            'model_name': 'glm-4-flash',
            'llm_provider': 'zhipu',
            'embedding_model': 'local_colqwen',
            'is_selected': False,
            'api_key': os.getenv('ZHIPUAI_API_KEY', ''),
        },
    ]
    
    result = await db.model_config.insert_many(models)
    print(f'Inserted {len(result.inserted_ids)} model configurations for miko')
    
    for m in models:
        sel = ' [SELECTED]' if m.get('is_selected') else ''
        chat_model = m['chat_model']
        model_name = m['model_name']
        provider = m['llm_provider']
        print(f'  {chat_model}: {model_name} ({provider}){sel}')
    
    await client.close()

asyncio.run(configure_models())
