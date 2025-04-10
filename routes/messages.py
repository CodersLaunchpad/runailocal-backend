from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from models.message_model import MessageCreate, MessageResponse, Conversation
from services.message_service import MessageService
from repos.message_repo import MessageRepository
from dependencies.db import get_db
from dependencies.auth import get_current_user
from models.users_model import UserResponse

# router = APIRouter(prefix="/messages", tags=["messages"])
router = APIRouter()

def get_message_repo(db = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)

def get_message_service(message_repo: MessageRepository = Depends(get_message_repo)) -> MessageService:
    return MessageService(message_repo)

@router.post("/", response_model=MessageResponse)
async def send_message(
    message: MessageCreate,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Send a new message"""
    message.sender_id = current_user.id
    return await message_service.send_message(message)

@router.get("/conversations/", response_model=List[Conversation])
async def get_conversations(
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get all conversations for the current user"""
    return await message_service.get_user_conversations(current_user.id)

@router.get("/conversations/{other_user_id}", response_model=Optional[Conversation])
async def get_conversation(
    other_user_id: str,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get conversation with a specific user"""
    return await message_service.get_conversation(current_user.id, other_user_id)

@router.get("/conversations/{other_user_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    other_user_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Get messages with a specific user"""
    return await message_service.get_messages(current_user.id, other_user_id, skip, limit)

@router.post("/conversations/{other_user_id}/read")
async def mark_messages_as_read(
    other_user_id: str,
    current_user: UserResponse = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """Mark messages as read"""
    await message_service.mark_messages_as_read(current_user.id, other_user_id)
    return {"status": "success"} 