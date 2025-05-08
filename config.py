import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any, Tuple, Union, Type, cast

# Load environment variables
load_dotenv()

class ConfigError(Exception):
    """Exception raised for missing configuration values"""
    pass

class Settings:
    # Define required environment variables
    REQUIRED_CONFIGS = [
        "DATABASE_URL",
        "DATABASE_NAME",
        "JWT_SECRET_KEY",
        "MINIO_USERNAME",
        "MINIO_PASSWORD",
        "MINIO_SERVER",
        "MINIO_BUCKET",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL"
    ]
    
    # Define config with default values and types (None means required with no default)
    # Format: (default_value, type)
    CONFIG_DEFAULTS: Dict[str, Tuple[Any, Type]] = {
        "DATABASE_URL": (None, str),
        "DATABASE_NAME": (None, str),
        "JWT_SECRET_KEY": (None, str),
        "JWT_ALGORITHM": ("HS256", str),
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": (30, int),
        # Database pool settings
        "DB_MAX_POOL_SIZE": (10, int),
        "DB_MAX_RECONNECT_ATTEMPTS": (5, int),
        "DB_RECONNECT_DELAY": (5, int),  # seconds
        "DB_SERVER_SELECTION_TIMEOUT_MS": (5000, int),
        "DB_CONNECT_TIMEOUT_MS": (5000, int),
        # MinIO settings
        "MINIO_USERNAME": (None, str),
        "MINIO_PASSWORD": (None, str),
        "MINIO_SERVER": (None, str),
        "MINIO_BUCKET": (None, str),
        # Backup settings
        "BACKUP_DIR": ("backups", str),
        # Email settings
        "SMTP_HOST": (None, str),
        "SMTP_PORT": (587, int),
        "SMTP_USERNAME": (None, str),
        "SMTP_PASSWORD": (None, str),
        "SMTP_FROM_EMAIL": (None, str),
        "SMTP_TLS": (True, bool)
    }
    
    def __init__(self):
        self.values = {}
        self._load_config()
    
    def _load_config(self):
        # Check for required environment variables
        missing_vars = []
        for var in self.REQUIRED_CONFIGS:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Load all config values with type conversion
        for key, (default_value, type_) in self.CONFIG_DEFAULTS.items():
            value = os.getenv(key)
            
            # Special handling for BACKUP_DIR to ensure it ends with 'backups'
            if key == "BACKUP_DIR":
                if value:
                    # If custom path provided, ensure it ends with 'backups'
                    value = value.replace('\\', '/')  # Normalize path separators
                    value = value.rstrip('/')  # Remove trailing slashes
                    if not value.endswith('/backups'):
                        value = f"{value}/backups"
                else:
                    # Default to 'backups' in project root
                    value = "backups"
                self.values[key] = value
                continue
            
            # Handle other config values normally
            if value is None:
                if default_value is None:
                    raise ConfigError(f"Missing required config value: {key}")
                self.values[key] = default_value
            else:
                try:
                    # Convert string value to expected type
                    if type_ == bool:
                        self.values[key] = value.lower() in ('true', '1', 'yes')
                    else:
                        self.values[key] = type_(value)
                except ValueError as e:
                    raise ConfigError(f"Invalid value for {key}: {str(e)}")
    
    def __getattr__(self, name):
        if name in self.values:
            return self.values[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

# Initialize settings
try:
    settings = Settings()
    
    # Create frequently used objects from settings
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
    # Optional token scheme that doesn't raise an exception for missing Authorization header
    oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
    
    # Make settings available for import
    DATABASE_URL = settings.DATABASE_URL
    DATABASE_NAME = settings.DATABASE_NAME
    JWT_SECRET_KEY = settings.JWT_SECRET_KEY
    JWT_ALGORITHM = settings.JWT_ALGORITHM
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    # Database pool settings
    DB_MAX_POOL_SIZE = settings.DB_MAX_POOL_SIZE
    DB_MAX_RECONNECT_ATTEMPTS = settings.DB_MAX_RECONNECT_ATTEMPTS
    DB_RECONNECT_DELAY = settings.DB_RECONNECT_DELAY
    DB_SERVER_SELECTION_TIMEOUT_MS = settings.DB_SERVER_SELECTION_TIMEOUT_MS
    DB_CONNECT_TIMEOUT_MS = settings.DB_CONNECT_TIMEOUT_MS

    # MINIO Settings
    MINIO_USERNAME = settings.MINIO_USERNAME
    MINIO_PASSWORD = settings.MINIO_PASSWORD
    MINIO_SERVER = settings.MINIO_SERVER
    MINIO_BUCKET = settings.MINIO_BUCKET
    
    # Email Settings
    SMTP_HOST = settings.SMTP_HOST
    SMTP_PORT = settings.SMTP_PORT
    SMTP_USERNAME = settings.SMTP_USERNAME
    SMTP_PASSWORD = settings.SMTP_PASSWORD
    SMTP_FROM_EMAIL = settings.SMTP_FROM_EMAIL
    SMTP_TLS = settings.SMTP_TLS
    
except ConfigError as e:
    # Print error and exit
    print(f"Configuration Error: {e}")
    import sys
    sys.exit(1)