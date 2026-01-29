from app.db.repositories.repository_manager import get_repository_manager


async def find_parent_mesage(conversation_id, message_id, chatflow=False):
    repo_manager = await get_repository_manager()
    if chatflow:
        conversation = await repo_manager.chatflow.get_chatflow(conversation_id)
    else:
        conversation = await repo_manager.conversation.get_conversation(conversation_id)
    if not conversation:
        return {}

    messages = {}
    for turn in conversation["turns"]:
        if message_id == turn["message_id"]:
            messages = {
                "message_id": turn["message_id"],
                "parent_message_id": turn["parent_message_id"],
                "user_message": turn["user_message"],
                "temp_db": turn["temp_db"],
                "ai_message": turn["ai_message"],
                "file_used": turn["file_used"],
                "status": turn["status"],
                "timestamp": turn["timestamp"].isoformat(),
            }
            break
    return messages


async def find_depth_parent_mesage(
    conversation_id, message_id, MAX_PARENT_DEPTH=5, chatflow=False
):
    parent_stack = []

    while message_id and len(parent_stack) < MAX_PARENT_DEPTH:
        parent_messages = await find_parent_mesage(
            conversation_id, message_id, chatflow=chatflow
        )
        message_id = parent_messages.get("parent_message_id", "")
        ai_msg = parent_messages.get("ai_message")
        user_msg = parent_messages.get("user_message")
        if ai_msg is not None:
            parent_stack.append(ai_msg)
        if user_msg is not None:
            parent_stack.append(user_msg)

    return parent_stack