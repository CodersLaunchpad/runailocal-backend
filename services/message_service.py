from typing import List, Optional
from repos.message_repo import MessageRepository
from models.message_model import MessageCreate, MessageResponse, Conversation
from fastapi import HTTPException

class MessageService:
    def __init__(self, message_repo: MessageRepository):
        self.message_repo = message_repo

    async def send_message(self, message: MessageCreate) -> MessageResponse:
        """Send a new message"""
        if message.sender_id == message.receiver_id:
            raise HTTPException(status_code=400, detail="Cannot send message to yourself")
        
        return await self.message_repo.create_message(message)

    async def get_conversation(self, user_id: str, other_user_id: str) -> Optional[Conversation]:
        """Get conversation between two users"""
        if user_id == other_user_id:
            raise HTTPException(status_code=400, detail="Cannot get conversation with yourself")
        
        return await self.message_repo.get_conversation(user_id, other_user_id)

    async def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user"""
        return await self.message_repo.get_user_conversations(user_id)

    async def get_messages(self, user_id: str, other_user_id: str, skip: int = 0, limit: int = 50) -> List[MessageResponse]:
        """Get messages between two users"""
        if user_id == other_user_id:
            raise HTTPException(status_code=400, detail="Cannot get messages with yourself")
        
        return await self.message_repo.get_messages(user_id, other_user_id, skip, limit)

    async def mark_messages_as_read(self, user_id: str, other_user_id: str):
        """Mark messages as read"""
        if user_id == other_user_id:
            raise HTTPException(status_code=400, detail="Cannot mark messages as read with yourself")
        
        await self.message_repo.mark_messages_as_read(user_id, other_user_id) 