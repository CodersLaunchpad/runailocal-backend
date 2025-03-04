from models.users_model import UserResponse, UserCreate
from db.schemas.users_schema import UserInDB
from typing import Dict, Any

def user_db_to_response(user_db: UserInDB) -> UserResponse:
    """Convert database user schema to API response model"""
    user_dict = user_db.model_dump(by_alias=False)
    
    # Only include fields that are in the UserResponse model
    response_fields = UserResponse.model_fields.keys()
    filtered_user = {k: v for k, v in user_dict.items() if k in response_fields}
    
    return UserResponse(**filtered_user)

def create_user_dict(user_create: UserCreate, password_hash: str) -> Dict[str, Any]:
    """Create a dict for MongoDB user document from UserCreate model"""
    user_dict = user_create.model_dump()
    user_dict.pop("password")  # Remove plain password
    user_dict["password_hash"] = password_hash
    return user_dict

# def apply_user_update(
#     current_user: UserInDB, 
#     update_data: UserUpdate
# ) -> UserInDB:
#     """Apply update data to the current user"""
#     update_dict = update_data.model_dump(exclude_unset=True)
    
#     # Update the user fields that are present in the update_data
#     for field, value in update_dict.items():
#         if value is not None:  # Only update non-None values
#             setattr(current_user, field, value)
    
#     return current_user