from typing import Optional

from pydantic import BaseModel


class FileInDB(BaseModel):
    """File information for any stored file"""
    file_id: Optional[str] = None
    file_type: Optional[str] = None
    file_extension: Optional[str] = None
    size: Optional[int] = None
    object_name: Optional[str] = None
    slug: Optional[str] = None
    unique_string: Optional[str] = None