"""
Secure Token Manager
Encrypts and securely stores the Telegram bot token
"""

import os
import hashlib
import logging
from typing import Optional
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.warning("⚠️ cryptography not installed, token encryption disabled")

logger = logging.getLogger(__name__)


class SecureTokenManager:
    """
    Secure Token Manager with encryption
    
    Features:
    - Encrypt bot token before storing
    - Decrypt when needed
    - Hash validation
    - Token rotation capability
    - Backup old tokens
    """
    
    def __init__(self):
        # Auto-detect BASE_PATH
        if os.path.exists('/root/Crypto-signal-bot'):
            self.base_path = Path('/root/Crypto-signal-bot')
        else:
            self.base_path = Path('/workspaces/Crypto-signal-bot')
        
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = None
        
        if ENCRYPTION_AVAILABLE and self.encryption_key:
            try:
                self.cipher = Fernet(self.encryption_key)
            except Exception as e:
                logger.error(f"❌ Failed to initialize cipher: {e}")
        
        self.token_file = self.base_path / '.bot_token_encrypted'
        self.token_hash_file = self.base_path / '.bot_token_hash'
        self.token_backup_dir = self.base_path / '.token_backups'
        
        # Create backup directory
        self.token_backup_dir.mkdir(exist_ok=True)
        
        logger.info("✅ Secure Token Manager initialized")
    
    def _get_or_create_encryption_key(self) -> Optional[bytes]:
        """
        Get or create encryption key
        
        Returns:
            Encryption key as bytes, or None if encryption not available
        """
        if not ENCRYPTION_AVAILABLE:
            return None
        
        key_file = self.base_path / '.encryption_key'
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                logger.info("✅ Loaded existing encryption key")
                return key
            except Exception as e:
                logger.error(f"❌ Failed to load encryption key: {e}")
                return None
        else:
            try:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set read-only for owner
                os.chmod(key_file, 0o400)
                
                logger.info("✅ Generated new encryption key")
                return key
            except Exception as e:
                logger.error(f"❌ Failed to generate encryption key: {e}")
                return None
    
    def store_token(self, token: str):
        """
        Store token securely with encryption
        
        Args:
            token: Bot token to store
        """
        if not token:
            logger.error("❌ Cannot store empty token")
            return
        
        try:
            # Encrypt token if encryption is available
            if self.cipher:
                encrypted_token = self.cipher.encrypt(token.encode())
                
                # Store encrypted token
                with open(self.token_file, 'wb') as f:
                    f.write(encrypted_token)
                os.chmod(self.token_file, 0o400)
                
                logger.info("✅ Token stored with encryption")
            else:
                logger.warning("⚠️ Encryption not available, token not stored")
            
            # Store hash for validation (always do this)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            with open(self.token_hash_file, 'w') as f:
                f.write(token_hash)
            os.chmod(self.token_hash_file, 0o400)
            
            logger.info("✅ Token hash stored for validation")
            
        except Exception as e:
            logger.error(f"❌ Failed to store token: {e}")
    
    def get_token(self) -> Optional[str]:
        """
        Retrieve and decrypt token
        
        Returns:
            Decrypted token or token from environment variable
        """
        # First, try to load from environment variable (primary method)
        env_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if env_token:
            # Validate against stored hash if it exists
            if self.token_hash_file.exists():
                if self.validate_token(env_token):
                    logger.info("✅ Token loaded from environment (validated)")
                    return env_token
                else:
                    logger.warning("⚠️ Token from environment failed validation")
            else:
                logger.info("✅ Token loaded from environment")
                return env_token
        
        # Fallback to encrypted file
        if self.cipher and self.token_file.exists():
            try:
                with open(self.token_file, 'rb') as f:
                    encrypted_token = f.read()
                
                decrypted_token = self.cipher.decrypt(encrypted_token).decode()
                
                # Validate token
                if self.validate_token(decrypted_token):
                    logger.info("✅ Token loaded from encrypted file (validated)")
                    return decrypted_token
                else:
                    logger.error("❌ Token validation failed")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Failed to decrypt token: {e}")
                return None
        
        logger.error("❌ No token found in environment or encrypted file")
        return None
    
    def validate_token(self, token: str) -> bool:
        """
        Validate token against stored hash
        
        Args:
            token: Token to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self.token_hash_file.exists():
            # No hash file, can't validate
            logger.warning("⚠️ No token hash file for validation")
            return True  # Allow token if no hash exists
        
        try:
            with open(self.token_hash_file, 'r') as f:
                stored_hash = f.read().strip()
            
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            is_valid = token_hash == stored_hash
            
            if not is_valid:
                logger.error("❌ Token hash mismatch!")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"❌ Failed to validate token: {e}")
            return False
    
    def rotate_token(self, new_token: str):
        """
        Rotate to new token, backup old token
        
        Args:
            new_token: New bot token
        """
        try:
            # Backup old token if it exists
            old_token = self.get_token()
            if old_token:
                from datetime import datetime
                backup_file = self.token_backup_dir / f"token_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
                
                if self.cipher:
                    encrypted_old = self.cipher.encrypt(old_token.encode())
                    with open(backup_file, 'wb') as f:
                        f.write(encrypted_old)
                    os.chmod(backup_file, 0o400)
                    
                    logger.info(f"✅ Old token backed up to {backup_file.name}")
            
            # Store new token
            self.store_token(new_token)
            logger.info("✅ Token rotated successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to rotate token: {e}")
    
    def cleanup_old_backups(self, keep_last: int = 5):
        """
        Clean up old token backups, keep only the last N
        
        Args:
            keep_last: Number of recent backups to keep
        """
        try:
            backups = sorted(self.token_backup_dir.glob('token_backup_*.enc'))
            
            if len(backups) > keep_last:
                for backup in backups[:-keep_last]:
                    backup.unlink()
                    logger.info(f"🗑️ Removed old backup: {backup.name}")
            
            logger.info(f"✅ Backup cleanup complete, kept {min(len(backups), keep_last)} backups")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup backups: {e}")


# Global instance
token_manager = SecureTokenManager()


def get_secure_token() -> Optional[str]:
    """
    Get bot token securely
    
    Returns:
        Bot token or None if not found
    """
    return token_manager.get_token()
