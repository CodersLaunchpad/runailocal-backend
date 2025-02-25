# Message routes
@app.post("/messages/", response_model=MessageInDB)
async def send_message(
    message: MessageCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    try:
        recipient_id = PyObjectId(message.recipient_id)
        
        # Check if recipient exists
        recipient = await db.users.find_one({"_id": recipient_id})
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")
        
        # Create message object
        message_obj = {
            "sender_id": current_user.id,
            "recipient_id": recipient_id,
            "text": message.text,
            "read": False,
            "created_at": datetime.utcnow()
        }
        
        # Insert message
        result = await db.messages.insert_one(message_obj)
        
        # Get the created message
        created_message = await db.messages.find_one({"_id": result.inserted_id})
        return created_message
    except:
        raise HTTPException(status_code=400, detail="Invalid recipient ID")

@app.get("/messages/", response_model=List[MessageInDB])
async def get_messages(
    sent: bool = False,
    current_user: UserInDB = Depends(get_current_active_user)
):
    if sent:
        query = {"sender_id": current_user.id}
    else:
        query = {"recipient_id": current_user.id}
    
    messages = []
    cursor = db.messages.find(query).sort("created_at", -1)
    
    async for document in cursor:
        messages.append(document)
    
    return messages

@app.get("/messages/{message_id}", response_model=MessageInDB)
async def get_message(
    message_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    try:
        object_id = PyObjectId(message_id)
        
        # Get the message
        message = await db.messages.find_one({"_id": object_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user is sender or recipient
        if str(message["sender_id"]) != str(current_user.id) and str(message["recipient_id"]) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Mark as read if user is recipient
        if str(message["recipient_id"]) == str(current_user.id) and not message.get("read"):
            updated_message = await db.messages.find_one_and_update(
                {"_id": object_id},
                {"$set": {"read": True}},
                return_document=ReturnDocument.AFTER
            )
            return updated_message
        
        return message
    except:
        raise HTTPException(status_code=400, detail="Invalid message ID")

@app.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: str,
    current_user: UserInDB = Depends(get_current_active_user)
):
    try:
        object_id = PyObjectId(message_id)
        
        # Get the message
        message = await db.messages.find_one({"_id": object_id})
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check if user is sender or recipient
        if str(message["sender_id"]) != str(current_user.id) and str(message["recipient_id"]) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Delete the message
        delete_result = await db.messages.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Message not found")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise HTTPException(status_code=400, detail="Invalid message ID")
