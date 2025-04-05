from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from dependencies.auth import AdminUser
from repos.settings_repo import SettingsRepository

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_settings(
    current_user: AdminUser,
    settings_repo: SettingsRepository = Depends()
):
    """Get current application settings (admin only)"""
    try:
        settings = await settings_repo.get_settings()
        return settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.put("/", response_model=Dict[str, Any])
async def update_settings(
    settings_data: Dict[str, Any],
    current_user: AdminUser,
    settings_repo: SettingsRepository = Depends()
):
    """Update application settings (admin only)"""
    try:
        updated_settings = await settings_repo.update_settings(
            settings_data,
            str(current_user.id)
        )
        return updated_settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@router.put("/auto-publish", response_model=Dict[str, Any])
async def update_auto_publish_setting(
    auto_publish: bool,
    current_user: AdminUser,
    settings_repo: SettingsRepository = Depends()
):
    """Update auto-publish articles setting (admin only)"""
    try:
        updated_settings = await settings_repo.update_settings(
            {"auto_publish_articles": auto_publish},
            str(current_user.id)
        )
        return updated_settings
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) 