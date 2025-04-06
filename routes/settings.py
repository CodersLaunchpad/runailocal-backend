from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from dependencies.auth import AdminUser
from models.models import AppSettingsUpdate
from dependencies.settings import SettingsRepositoryDep

router = APIRouter()

@router.get("/", response_model=Dict[str, Any])
async def get_settings(
    current_user: AdminUser,
    settings_repo: SettingsRepositoryDep
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
    settings_data: AppSettingsUpdate,
    current_user: AdminUser,
    settings_repo: SettingsRepositoryDep
):
    """Update application settings (admin only)"""
    try:
        updated_settings = await settings_repo.update_settings(
            settings_data,
            str(current_user.id)
        )
        return updated_settings
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
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