from fastapi import APIRouter, Depends, HTTPException, status, Form
from datetime import timedelta, datetime, timezone
import random
import string

from db.db import get_db
from models.auth_model import Token, PasswordResetRequest, PasswordReset
from dependencies.auth import AuthServiceDep
from dependencies.db import DB
from utils.security import get_password_hash
from utils.time import get_current_utc_time
from services.email_service import EmailService

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    auth_service: AuthServiceDep = None
):
    """
    Authenticate user and return JWT access token
    """
    try:
        token = await auth_service.generate_user_token(username, password)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )

@router.post("/forgot-password")
async def request_password_reset(
    request: PasswordResetRequest,
    db = Depends(get_db)
):
    """
    Request a password reset code to be sent to the user's email
    """
    try:
        # Check if user exists
        user = await db.users.find_one({"email": request.email})
        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If your email is registered, you will receive a password reset code."}

        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Store the code in the database
        reset_code = {
            "email": request.email,
            "code": code,
            "created_at": get_current_utc_time(),
            "is_active": True
        }
        
        # Deactivate any existing codes for this email
        await db.password_reset_codes.update_many(
            {"email": request.email},
            {"$set": {"is_active": False}}
        )
        
        # Insert the new code
        await db.password_reset_codes.insert_one(reset_code)
        
        # Send email with reset code
        email_sent = await EmailService.send_password_reset_email(request.email, code)
        
        if not email_sent:
            # If email fails, deactivate the code and raise an error
            await db.password_reset_codes.update_one(
                {"_id": reset_code["_id"]},
                {"$set": {"is_active": False}}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email"
            )
        
        return {"message": "Password reset code sent to your email."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error requesting password reset: {str(e)}"
        )

@router.post("/reset-password")
async def reset_password(
    request: PasswordReset,
    db= Depends(get_db)
):
    """
    Reset password using the code sent to user's email
    """
    try:
        # Find the most recent active code for this email
        reset_code = await db.password_reset_codes.find_one({
            "email": request.email,
            "code": request.code,
            "is_active": True
        })
        
        if not reset_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset code"
            )
            
        # Check if code is less than 15 minutes old
        current_time = datetime.now(timezone.utc)
        code_created_at = reset_code["created_at"]
        
        # Ensure code_created_at is timezone-aware
        if code_created_at.tzinfo is None:
            code_created_at = code_created_at.replace(tzinfo=timezone.utc)
            
        code_age = current_time - code_created_at
        if code_age > timedelta(minutes=15):
            # Deactivate expired code
            await db.password_reset_codes.update_one(
                {"_id": reset_code["_id"]},
                {"$set": {"is_active": False}}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset code has expired"
            )
            
        # Hash the new password
        hashed_password = get_password_hash(request.new_password)
        
        # Update user's password
        result = await db.users.update_one(
            {"email": request.email},
            {"$set": {"password_hash": hashed_password}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Deactivate the used code
        await db.password_reset_codes.update_one(
            {"_id": reset_code["_id"]},
            {"$set": {"is_active": False}}
        )
        
        return {"message": "Password has been reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )

@router.get("/check-availability")
async def check_availability(
    collection: str, 
    field: str, 
    value: str,
    case_sensitive: bool = False,
    db = Depends(get_db)
):
    """
    Check if a given value for a specified field is available in a collection.

    Query Parameters:
      - collection: The collection name (e.g., "users", "categories").
      - field: The field to check (e.g., "username", "email", "name").
      - value: The value to verify.
      - case_sensitive: Whether the search should be case sensitive (default is False).
    
    Returns:
      - available (bool): True if the value is not taken; False otherwise.
      - message (str): A message indicating the status.
    """
    try:
        coll = db[collection]
        if not case_sensitive:
            # Case-insensitive: use a regex that matches the entire string (ignoring case)
            query = {field: {"$regex": f"^{value}$", "$options": "i"}}
        else:
            query = {field: value}
        
        document = await coll.find_one(query)
        if document:
            return {"available": False, "message": f"{field} is already taken."}
        return {"available": True, "message": f"{field} is available."}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"available": False, "message": "Unable to check availability currently."}