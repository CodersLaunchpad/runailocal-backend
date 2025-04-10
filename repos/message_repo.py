from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from models.message_model import MessageCreate, MessageResponse, Conversation

class MessageRepository:
    def __init__(self, db):
        self.db = db
        self.messages = db.messages
        self.conversations = db.conversations

    async def create_message(self, message: MessageCreate) -> MessageResponse:
        """Create a new message and update conversation"""
        message_dict = message.model_dump()
        message_dict["created_at"] = datetime.utcnow()
        message_dict["is_read"] = False
        
        # Insert message
        result = await self.messages.insert_one(message_dict)
        message_dict["id"] = str(result.inserted_id)
        
        # Update or create conversation
        participants = sorted([message.sender_id, message.receiver_id])
        conversation = await self.conversations.find_one({
            "participants": participants
        })
        
        if conversation:
            await self.conversations.update_one(
                {"_id": conversation["_id"]},
                {
                    "$set": {
                        "last_message": message_dict,
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"unread_count": 1}
                }
            )
        else:
            await self.conversations.insert_one({
                "participants": participants,
                "last_message": message_dict,
                "unread_count": 1,
                "updated_at": datetime.utcnow()
            })
        
        return MessageResponse(**message_dict)

    async def get_conversation(self, user_id: str, other_user_id: str) -> Optional[Conversation]:
        """Get conversation between two users"""
        participants = sorted([user_id, other_user_id])
        conversation = await self.conversations.find_one({"participants": participants})
        
        if conversation:
            conversation["id"] = str(conversation["_id"])
            return Conversation(**conversation)
        return None

    async def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user"""
        conversations = await self.conversations.find({
            "participants": user_id
        }).sort("updated_at", -1).to_list(length=None)
        
        return [Conversation(**{**conv, "id": str(conv["_id"])}) for conv in conversations]

    async def get_messages(self, user_id: str, other_user_id: str, skip: int = 0, limit: int = 50) -> List[MessageResponse]:
        """Get messages between two users"""
        messages = await self.messages.find({
            "$or": [
                {"sender_id": user_id, "receiver_id": other_user_id},
                {"sender_id": other_user_id, "receiver_id": user_id}
            ]
        }).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
        
        return [MessageResponse(**{**msg, "id": str(msg["_id"])}) for msg in messages]

    async def mark_messages_as_read(self, user_id: str, other_user_id: str):
        """Mark all messages from other_user_id to user_id as read"""
        await self.messages.update_many(
            {
                "sender_id": other_user_id,
                "receiver_id": user_id,
                "is_read": False
            },
            {
                "$set": {
                    "is_read": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        # Update conversation unread count
        participants = sorted([user_id, other_user_id])
        await self.conversations.update_one(
            {"participants": participants},
            {"$set": {"unread_count": 0}}
        ) 