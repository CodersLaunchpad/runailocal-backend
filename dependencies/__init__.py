"""
Import common dependencies to make them available from the package level.
This allows imports like: from dependencies import get_current_user
"""
from .auth import get_current_user, get_current_active_user, get_optional_user
from .db import get_db, get_object_storage
from .user import get_user_repository, get_user_service
