"""
Unit tests for access control decorator and functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import directly from bot.py module (not bot package)
import importlib.util
bot_module_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bot.py')
spec = importlib.util.spec_from_file_location("bot_module", bot_module_path)
bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)


class TestAccessControl:
    """Test access control decorator and functionality"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Update object"""
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_chat = Mock()
        update.effective_chat.id = 12345
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object"""
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    async def test_decorator_allows_authorized_user(self, mock_update, mock_context):
        """Test that authorized users can access commands"""
        # Import the decorator
        require_access = bot_module.require_access
        
        # Define a test function
        test_func_called = False
        
        @require_access()
        async def test_command(update, context):
            nonlocal test_func_called
            test_func_called = True
            return "Success"
        
        # Set user as authorized
        mock_update.effective_user.id = 7003238836  # OWNER_CHAT_ID
        
        # Execute the decorated function
        result = await test_command(mock_update, mock_context)
        
        # Assert command executed
        assert test_func_called
        assert result == "Success"
        # Denial message should not be sent
        mock_update.message.reply_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_decorator_blocks_unauthorized_user(self, mock_update, mock_context):
        """Test that unauthorized users are blocked"""
        require_access = bot_module.require_access
        
        test_func_called = False
        
        @require_access()
        async def test_command(update, context):
            nonlocal test_func_called
            test_func_called = True
            return "Success"
        
        # Set user as unauthorized
        mock_update.effective_user.id = 99999  # Not in ALLOWED_USERS
        
        # Execute the decorated function
        result = await test_command(mock_update, mock_context)
        
        # Assert command NOT executed
        assert not test_func_called
        assert result is None
        
        # Assert denial message sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "ACCESS DENIED" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_owner_notification_sent(self, mock_update, mock_context):
        """Test that owner receives notification on unauthorized attempt"""
        require_access = bot_module.require_access
        
        @require_access()
        async def test_command(update, context):
            return "Success"
        
        # Set user as unauthorized
        mock_update.effective_user.id = 99999
        mock_update.effective_user.username = "hacker"
        
        # Execute
        await test_command(mock_update, mock_context)
        
        # Assert owner notification sent
        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args[1]
        
        # Check notification content
        assert "UNAUTHORIZED ACCESS ATTEMPT" in call_kwargs['text']
        assert "hacker" in call_kwargs['text']
        assert "99999" in call_kwargs['text']
        assert call_kwargs['parse_mode'] == 'HTML'
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring"""
        require_access = bot_module.require_access
        
        @require_access()
        async def test_command(update, context):
            """Test docstring"""
            pass
        
        # Assert metadata preserved
        assert test_command.__name__ == "test_command"
        assert test_command.__doc__ == "Test docstring"
    
    @pytest.mark.asyncio
    async def test_decorator_with_custom_allowed_users(self, mock_update, mock_context):
        """Test decorator with custom allowed users set"""
        require_access = bot_module.require_access
        
        # Custom whitelist
        custom_users = {11111, 22222}
        
        test_func_called = False
        
        @require_access(allowed_users=custom_users)
        async def test_command(update, context):
            nonlocal test_func_called
            test_func_called = True
            return "Success"
        
        # Test with user in custom list
        mock_update.effective_user.id = 11111
        result = await test_command(mock_update, mock_context)
        assert test_func_called
        
        # Reset and test with user NOT in custom list
        test_func_called = False
        mock_update.effective_user.id = 33333
        mock_update.message.reply_text.reset_mock()
        
        result = await test_command(mock_update, mock_context)
        assert not test_func_called
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_unauthorized_attempts(self, mock_update, mock_context):
        """Test multiple unauthorized attempts are all blocked and logged"""
        require_access = bot_module.require_access
        
        @require_access()
        async def test_command(update, context):
            return "Success"
        
        # Set user as unauthorized
        mock_update.effective_user.id = 88888
        
        # Make 3 unauthorized attempts
        for i in range(3):
            await test_command(mock_update, mock_context)
        
        # Assert 3 denial messages sent
        assert mock_update.message.reply_text.call_count == 3
        
        # Assert 3 owner notifications sent
        assert mock_context.bot.send_message.call_count == 3
    
    @pytest.mark.asyncio
    async def test_notification_failure_handling(self, mock_update, mock_context):
        """Test that decorator handles notification failures gracefully"""
        require_access = bot_module.require_access
        
        @require_access()
        async def test_command(update, context):
            return "Success"
        
        # Make notification fail
        mock_context.bot.send_message.side_effect = Exception("Network error")
        
        # Set user as unauthorized
        mock_update.effective_user.id = 77777
        
        # Execute - should not raise exception
        try:
            await test_command(mock_update, mock_context)
        except Exception as e:
            pytest.fail(f"Decorator should handle notification failures: {e}")
        
        # Denial message should still be sent to user
        mock_update.message.reply_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_decorator_with_args_and_kwargs(self, mock_update, mock_context):
        """Test that decorator passes through args and kwargs"""
        require_access = bot_module.require_access
        
        received_args = None
        received_kwargs = None
        
        @require_access()
        async def test_command(update, context, *args, **kwargs):
            nonlocal received_args, received_kwargs
            received_args = args
            received_kwargs = kwargs
            return "Success"
        
        # Set user as authorized
        mock_update.effective_user.id = 7003238836  # OWNER
        
        # Call with additional args and kwargs
        await test_command(mock_update, mock_context, "arg1", "arg2", key1="value1", key2="value2")
        
        # Assert args and kwargs passed through
        assert received_args == ("arg1", "arg2")
        assert received_kwargs == {"key1": "value1", "key2": "value2"}
    
    def test_allowed_users_configuration(self):
        """Test ALLOWED_USERS configuration loading"""
        ALLOWED_USERS = bot_module.ALLOWED_USERS
        OWNER_CHAT_ID = bot_module.OWNER_CHAT_ID
        
        # Assert owner is in allowed users
        assert OWNER_CHAT_ID in ALLOWED_USERS
        
        # Assert it's a set
        assert isinstance(ALLOWED_USERS, set)
    
    @pytest.mark.asyncio
    async def test_logging_authorized_access(self, mock_update, mock_context, caplog):
        """Test that authorized access is logged"""
        require_access = bot_module.require_access
        import logging
        
        @require_access()
        async def test_command(update, context):
            return "Success"
        
        # Set user as authorized
        mock_update.effective_user.id = 7003238836  # OWNER
        
        with caplog.at_level(logging.INFO):
            await test_command(mock_update, mock_context)
        
        # Check for authorized access log
        assert any("✅ Authorized access" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_logging_unauthorized_access(self, mock_update, mock_context, caplog):
        """Test that unauthorized access is logged"""
        require_access = bot_module.require_access
        import logging
        
        @require_access()
        async def test_command(update, context):
            return "Success"
        
        # Set user as unauthorized
        mock_update.effective_user.id = 66666
        
        with caplog.at_level(logging.WARNING):
            await test_command(mock_update, mock_context)
        
        # Check for unauthorized access log
        assert any("⛔ UNAUTHORIZED ACCESS ATTEMPT" in record.message for record in caplog.records)


class TestStartCommandAccessControl:
    """Test start command with access control"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Update object"""
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_chat = Mock()
        update.effective_chat.id = 12345
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        update.message.forward_origin = None  # Not forwarded
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object"""
        context = Mock()
        context.bot = Mock()
        context.bot.send_message = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    async def test_start_unauthorized_user_gets_info_message(self, mock_update, mock_context):
        """Test that unauthorized users get informative message on /start"""
        start_cmd = bot_module.start_cmd
        
        # Set user as unauthorized
        mock_update.effective_user.id = 55555
        
        # Execute start command
        await start_cmd(mock_update, mock_context)
        
        # Assert info message sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        # Check message content
        assert "private trading bot" in call_args.lower()
        assert "55555" in call_args  # User ID shown
        assert "/approve 55555" in call_args  # Approval command shown


class TestHelpCommandAccessControl:
    """Test help command with access control"""
    
    @pytest.fixture
    def mock_update(self):
        """Create a mock Update object"""
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 12345
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        return update
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Context object"""
        context = Mock()
        return context
    
    @pytest.mark.asyncio
    async def test_help_unauthorized_user_gets_info_message(self, mock_update, mock_context):
        """Test that unauthorized users get informative message on /help"""
        help_cmd = bot_module.help_cmd
        
        # Set user as unauthorized
        mock_update.effective_user.id = 44444
        
        # Execute help command
        await help_cmd(mock_update, mock_context)
        
        # Assert info message sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        
        # Check message content
        assert "private trading bot" in call_args.lower()
        assert "44444" in call_args  # User ID shown
        assert "/approve 44444" in call_args  # Approval command shown
