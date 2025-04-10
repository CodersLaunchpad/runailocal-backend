#!/usr/bin/env python3
import os
import sys
import requests
import hashlib
import json
from datetime import datetime
import logging
from pathlib import Path
import argparse
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, api_url: str, backup_dir: str, retention_days: int = 30):
        self.api_url = api_url.rstrip('/')
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create checksum file if it doesn't exist
        self.checksum_file = self.backup_dir / 'last_checksum.txt'
        if not self.checksum_file.exists():
            self.checksum_file.write_text('')
    
    def get_last_checksum(self) -> Optional[str]:
        """Get the last backup checksum from file"""
        try:
            return self.checksum_file.read_text().strip()
        except Exception:
            return None
    
    def save_checksum(self, checksum: str):
        """Save the backup checksum to file"""
        self.checksum_file.write_text(checksum)
    
    def cleanup_old_backups(self):
        """Remove backups older than retention_days"""
        now = datetime.now()
        for backup_file in self.backup_dir.glob('backup_*.zip'):
            try:
                # Extract date from filename (backup_YYYYMMDD_HHMMSS.zip)
                date_str = backup_file.stem.split('_')[1]
                backup_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                
                if (now - backup_date).days > self.retention_days:
                    logger.info(f"Removing old backup: {backup_file}")
                    backup_file.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up backup {backup_file}: {str(e)}")
    
    def download_backup(self) -> tuple[Path, str]:
        """Download backup from API and return (filepath, checksum)"""
        try:
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = self.backup_dir / backup_filename
            
            # Download backup
            response = requests.get(f"{self.api_url}/backup", stream=True)
            response.raise_for_status()
            
            # Get checksum from headers
            checksum = response.headers.get('X-Backup-Checksum')
            if not checksum:
                raise ValueError("No checksum found in response headers")
            
            # Save backup file
            with open(backup_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Backup downloaded successfully: {backup_filename}")
            return backup_path, checksum
            
        except Exception as e:
            logger.error(f"Error downloading backup: {str(e)}")
            raise
    
    def verify_backup(self, backup_path: Path, expected_checksum: str) -> bool:
        """Verify backup integrity"""
        try:
            # Calculate actual checksum
            with open(backup_path, 'rb') as f:
                actual_checksum = hashlib.sha256(f.read()).hexdigest()
            
            if actual_checksum != expected_checksum:
                logger.error(f"Checksum mismatch! Expected: {expected_checksum}, Got: {actual_checksum}")
                return False
            
            logger.info("Backup verification successful")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup: {str(e)}")
            return False
    
    def run_backup(self):
        """Run the complete backup process"""
        try:
            # Get last backup checksum
            last_checksum = self.get_last_checksum()
            
            # Download new backup
            backup_path, new_checksum = self.download_backup()
            
            # Verify backup
            if not self.verify_backup(backup_path, new_checksum):
                logger.error("Backup verification failed")
                backup_path.unlink()  # Remove invalid backup
                return False
            
            # Save new checksum
            self.save_checksum(new_checksum)
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"Backup process failed: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Backup script for MongoDB and MinIO data')
    parser.add_argument('--api-url', required=True, help='API URL for backup endpoint')
    parser.add_argument('--backup-dir', default='backups', help='Directory to store backups')
    parser.add_argument('--retention-days', type=int, default=30, help='Number of days to keep backups')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager(
        api_url=args.api_url,
        backup_dir=args.backup_dir,
        retention_days=args.retention_days
    )
    
    success = backup_manager.run_backup()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 