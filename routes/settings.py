from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from dependencies.settings import SettingsRepositoryDep
from models.models import AppSettings, AppSettingsUpdate
from repos.settings_repo import SettingsRepository
from dependencies.db import DB
from db.db import get_db
from dependencies.auth import AdminUser, get_current_user

router = APIRouter()

@router.get("/settings", response_model=Dict[str, Any])
async def get_settings(
    db = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current application settings"""
    try:
        settings_repo = SettingsRepository(db)
        settings = await settings_repo.get_settings()
        return settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/settings", response_model=Dict[str, Any])
async def update_settings(
    settings_update: AppSettingsUpdate,
    db = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update application settings"""
    try:
        settings_repo = SettingsRepository(db)
        updated_settings = await settings_repo.update_settings(settings_update)
        return updated_settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/auto-publish", response_model=Dict[str, Any])
async def update_auto_publish_setting(
    auto_publish: bool,
    current_user: AdminUser,
    settings_repo: SettingsRepositoryDep
):
    """Update auto-publish articles setting (admin only)"""
    try:
        updated_settings = await settings_repo.update_settings(
            AppSettingsUpdate(auto_publish_articles=auto_publish),
            str(current_user.id)
        )
        return updated_settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) 