"""
Authentication & Authorization Module
Manages user access control, admin privileges, and blacklist/whitelist
"""

import os
import logging
import secrets
from typing import Set, Optional
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Authentication and Authorization Manager
    
    Features:
    - Admin user management (from ADMIN_USER_IDS env variable)
    - Blacklist/Whitelist system
    - Role-based access control
    - API key generation (for future external access)
    """
    
    def __init__(self):
        self.admin_users: Set[int] = self._load_admin_users()
        self.whitelisted_users: Set[int] = self._load_whitelisted_users()
        self.blacklisted_users: Set[int] = set()
        self.api_keys: dict = {}  # For external API access (future feature)
        
        logger.info(f"✅ Auth Manager initialized: {len(self.admin_users)} admins")
    
    def _load_admin_users(self) -> Set[int]:
        """
        Load admin user IDs from environment variable ADMIN_USER_IDS
        
        Returns:
            Set of admin user IDs
        """
        admin_ids = os.getenv('ADMIN_USER_IDS', '')
        if admin_ids:
            try:
                admin_set = set(int(uid.strip()) for uid in admin_ids.split(',') if uid.strip())
                logger.info(f"✅ Loaded {len(admin_set)} admin users from ADMIN_USER_IDS")
                return admin_set
            except ValueError as e:
                logger.error(f"❌ Error parsing ADMIN_USER_IDS: {e}")
                return set()
        
        # Fallback to OWNER_CHAT_ID if no ADMIN_USER_IDS
        owner_id = os.getenv('OWNER_CHAT_ID', '')
        if owner_id:
            try:
                owner_set = {int(owner_id)}
                logger.info(f"✅ Using OWNER_CHAT_ID as admin: {owner_id}")
                return owner_set
            except ValueError:
                logger.error(f"❌ Invalid OWNER_CHAT_ID: {owner_id}")
        
        logger.warning("⚠️ No admin users configured!")
        return set()
    
    def _load_whitelisted_users(self) -> Set[int]:
        """
        Load whitelisted users (optional whitelist mode)
        
        Returns:
            Set of whitelisted user IDs
        """
        whitelist_mode = os.getenv('WHITELIST_MODE', 'false').lower() == 'true'
        
        if not whitelist_mode:
            logger.info("ℹ️ Whitelist mode DISABLED (public bot)")
            return set()
        
        whitelist_ids = os.getenv('WHITELISTED_USER_IDS', '')
        if whitelist_ids:
            try:
                whitelist_set = set(int(uid.strip()) for uid in whitelist_ids.split(',') if uid.strip())
                logger.info(f"✅ Whitelist mode ENABLED: {len(whitelist_set)} users")
                return whitelist_set
            except ValueError as e:
                logger.error(f"❌ Error parsing WHITELISTED_USER_IDS: {e}")
                return set()
        
        logger.warning("⚠️ Whitelist mode enabled but no users configured!")
        return set()
    
    def is_admin(self, user_id: int) -> bool:
        """
        Check if user is admin
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if admin, False otherwise
        """
        return user_id in self.admin_users
    
    def is_authorized(self, user_id: int) -> bool:
        """
        Check if user is authorized to use bot
        
        Rules:
        - Blacklisted users: DENIED
        - If whitelist mode enabled: Only whitelisted + admins allowed
        - Otherwise: Everyone allowed (except blacklisted)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if authorized, False otherwise
        """
        # Check blacklist first
        if user_id in self.blacklisted_users:
            logger.warning(f"🚫 User {user_id} is BLACKLISTED")
            return False
        
        # Admins always have access
        if user_id in self.admin_users:
            return True
        
        # If whitelist mode enabled
        if self.whitelisted_users:
            authorized = user_id in self.whitelisted_users
            if not authorized:
                logger.warning(f"🚫 User {user_id} not in WHITELIST")
            return authorized
        
        # Public mode - everyone allowed (except blacklisted)
        return True
    
    def blacklist_user(self, user_id: int, reason: str = "Abuse"):
        """
        Add user to blacklist
        
        Args:
            user_id: Telegram user ID
            reason: Reason for blacklisting
        """
        # Don't blacklist admins
        if user_id in self.admin_users:
            logger.warning(f"⚠️ Cannot blacklist admin user {user_id}")
            return
        
        self.blacklisted_users.add(user_id)
        logger.error(f"🚫 User {user_id} BLACKLISTED: {reason}")
    
    def unblacklist_user(self, user_id: int):
        """
        Remove user from blacklist
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.blacklisted_users:
            self.blacklisted_users.remove(user_id)
            logger.info(f"✅ User {user_id} REMOVED from blacklist")
    
    def whitelist_user(self, user_id: int):
        """
        Add user to whitelist
        
        Args:
            user_id: Telegram user ID
        """
        self.whitelisted_users.add(user_id)
        logger.info(f"✅ User {user_id} ADDED to whitelist")
    
    def remove_from_whitelist(self, user_id: int):
        """
        Remove user from whitelist
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.whitelisted_users:
            self.whitelisted_users.remove(user_id)
            logger.info(f"ℹ️ User {user_id} REMOVED from whitelist")
    
    def add_admin(self, user_id: int):
        """
        Add user to admin list
        
        Args:
            user_id: Telegram user ID
        """
        self.admin_users.add(user_id)
        logger.info(f"✅ User {user_id} ADDED as admin")
    
    def remove_admin(self, user_id: int):
        """
        Remove user from admin list
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.admin_users:
            self.admin_users.remove(user_id)
            logger.info(f"ℹ️ User {user_id} REMOVED from admins")
    
    def generate_api_key(self, user_id: int) -> str:
        """
        Generate API key for external access (future feature)
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Generated API key
        """
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = user_id
        logger.info(f"🔑 API key generated for user {user_id}")
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[int]:
        """
        Validate API key and return user_id
        
        Args:
            api_key: API key to validate
            
        Returns:
            User ID if valid, None otherwise
        """
        return self.api_keys.get(api_key)
    
    def revoke_api_key(self, api_key: str):
        """
        Revoke API key
        
        Args:
            api_key: API key to revoke
        """
        if api_key in self.api_keys:
            user_id = self.api_keys[api_key]
            del self.api_keys[api_key]
            logger.info(f"🔑 API key revoked for user {user_id}")
    
    def get_auth_stats(self) -> dict:
        """
        Get authentication statistics
        
        Returns:
            Dictionary with auth stats
        """
        return {
            'total_admins': len(self.admin_users),
            'total_blacklisted': len(self.blacklisted_users),
            'total_whitelisted': len(self.whitelisted_users),
            'whitelist_mode': len(self.whitelisted_users) > 0,
            'total_api_keys': len(self.api_keys)
        }


# Global instance
auth_manager = AuthManager()


def require_auth(func):
    """
    Decorator to require authentication
    
    Usage:
        @require_auth
        async def my_command(update, context):
            ...
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not auth_manager.is_authorized(user_id):
            await update.message.reply_text(
                "🚫 Access denied. You are not authorized to use this bot."
            )
            logger.warning(f"🚫 Unauthorized access attempt from user {user_id}")
            return
        
        return await func(update, context)
    
    return wrapper


def require_admin(func):
    """
    Decorator to require admin privileges
    
    Usage:
        @require_admin
        async def my_admin_command(update, context):
            ...
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if not auth_manager.is_admin(user_id):
            await update.message.reply_text(
                "🚫 This command requires admin privileges."
            )
            logger.warning(f"🚫 Non-admin user {user_id} attempted admin command")
            return
        
        return await func(update, context)
    
    return wrapper
