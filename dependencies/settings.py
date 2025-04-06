from fastapi import Depends
from typing import Annotated

from repos.settings_repo import SettingsRepository
from .db import get_db

def get_settings_repository(db = Depends(get_db)):
    """
    Dependency to get a settings repository instance.
    """
    return SettingsRepository(db)

# Create annotated type for cleaner dependency injection
SettingsRepositoryDep = Annotated[SettingsRepository, Depends(get_settings_repository)] 