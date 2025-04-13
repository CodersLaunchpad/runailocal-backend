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
        "MINIO_BUCKET"
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
        "BACKUP_DIR": ("backups", str)
    }
    
    def __init__(self):
        self.values = {}
        self._load_config()
    
    def _load_config(self):
        # Check for required environment variables
        missing_vars = []
        
        for key, (default_value, expected_type) in self.CONFIG_DEFAULTS.items():
            # Get raw value from environment or use default
            env_value = os.getenv(key)
            
            if env_value is None:
                # Use default if no environment variable is set
                value = default_value
                # If value is None and it's in required configs, add to missing list
                if value is None and key in self.REQUIRED_CONFIGS:
                    missing_vars.append(key)
                    continue
            else:
                # Convert environment value to expected type
                try:
                    if expected_type == bool:
                        # Special handling for boolean values
                        value = env_value.lower() in ('true', 'yes', '1', 't', 'y')
                    else:
                        # Use the specified type constructor
                        value = expected_type(env_value)
                except (ValueError, TypeError) as e:
                    raise ConfigError(f"Invalid value for {key}: {env_value} - expected {expected_type.__name__} - {e}")
            
            # Store the converted value
            self.values[key] = value
        
        # If any required variables are missing, raise an error
        if missing_vars:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
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
    
except ConfigError as e:
    # Print error and exit
    print(f"Configuration Error: {e}")
    import sys
    sys.exit(1)