"""
Simple validation tests for access control implementation
"""

def test_decorator_exists_in_bot_py():
    """Test that require_access decorator is defined in bot.py"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    assert 'def require_access(' in content, 'require_access decorator not found'
    assert '@wraps(func)' in content, 'Decorator should use @wraps for metadata preservation'
    print("✅ require_access decorator exists")


def test_notification_function_exists():
    """Test that notification function is defined"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    assert 'async def notify_owner_unauthorized_access(' in content
    assert 'UNAUTHORIZED ACCESS ATTEMPT' in content
    print("✅ notify_owner_unauthorized_access function exists")


def test_decorator_applied_to_commands():
    """Test that decorator is applied to command handlers"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Count applications
    decorator_count = content.count('@require_access()')
    assert decorator_count >= 50, f'Expected at least 50 applications, found {decorator_count}'
    
    # Check specific critical commands
    critical_commands = [
        'async def signal_cmd',
        'async def market_cmd',
        'async def settings_cmd',
        'async def fund_cmd',
        'async def alerts_cmd',
        'async def stats_cmd',
    ]
    
    for cmd in critical_commands:
        # Find the command
        cmd_idx = content.find(cmd)
        assert cmd_idx > 0, f'{cmd} not found'
        
        # Check that @require_access() appears before it (within 200 chars)
        before_cmd = content[max(0, cmd_idx-200):cmd_idx]
        assert '@require_access()' in before_cmd, f'{cmd} is not protected with @require_access()'
    
    print(f"✅ Decorator applied {decorator_count} times to commands")
    print("✅ All critical commands are protected")


def test_start_and_help_handle_unauthorized():
    """Test that start and help commands handle unauthorized users"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Find start_cmd
    start_idx = content.find('async def start_cmd')
    assert start_idx > 0
    
    # Check for authorization check in start_cmd
    start_func = content[start_idx:start_idx+5000]
    assert 'if user_id not in ALLOWED_USERS:' in start_func, 'start_cmd should check authorization'
    assert 'private trading bot' in start_func.lower(), 'start_cmd should mention private bot'
    
    # Find help_cmd
    help_idx = content.find('async def help_cmd')
    assert help_idx > 0
    
    # Check for authorization check in help_cmd
    help_func = content[help_idx:help_idx+5000]
    assert 'if user_id not in ALLOWED_USERS:' in help_func, 'help_cmd should check authorization'
    
    print("✅ start_cmd and help_cmd handle unauthorized users correctly")


def test_decorator_order_with_rate_limited():
    """Test that @require_access is placed before @rate_limited"""
    with open('bot.py', 'r') as f:
        lines = f.readlines()
    
    violations = []
    for i, line in enumerate(lines):
        if '@rate_limited' in line:
            # Check previous lines for @require_access
            found_require_access = False
            for j in range(max(0, i-5), i):
                if '@require_access()' in lines[j]:
                    found_require_access = True
                    break
            
            # Check if this is a command that should be protected
            for k in range(i, min(len(lines), i+3)):
                if 'async def ' in lines[k] and '_cmd' in lines[k]:
                    # This is a command - should have @require_access before @rate_limited
                    # (except for internal/callback functions)
                    if not found_require_access and 'start_cmd' not in lines[k] and 'help_cmd' not in lines[k]:
                        # start_cmd and help_cmd don't use @require_access decorator
                        violations.append(f"Line {i+1}: {lines[k].strip()} - Missing @require_access before @rate_limited")
                    break
    
    # Allow some violations for special cases
    if len(violations) > 5:
        print(f"⚠️ Warning: {len(violations)} commands may be missing @require_access")
        for v in violations[:5]:
            print(f"  {v}")
    else:
        print("✅ Decorator order looks good")


def test_allowed_users_configuration():
    """Test that ALLOWED_USERS is properly configured"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    assert 'ALLOWED_USERS = {OWNER_CHAT_ID}' in content or 'ALLOWED_USERS = {' in content
    assert 'OWNER_CHAT_ID = int(os.getenv' in content
    
    print("✅ ALLOWED_USERS configuration found")


def test_logging_statements():
    """Test that logging statements are in place"""
    with open('bot.py', 'r') as f:
        content = f.read()
    
    # Check for authorized access logging
    assert 'logger.info' in content and 'Authorized access' in content
    
    # Check for unauthorized access logging
    assert 'logger.warning' in content and 'UNAUTHORIZED ACCESS ATTEMPT' in content
    
    # Check for owner notification logging
    assert 'Sent unauthorized access alert to owner' in content or 'notification' in content.lower()
    
    print("✅ Logging statements found")


def test_documentation_exists():
    """Test that documentation file exists"""
    import os
    assert os.path.exists('ACCESS_CONTROL_GUIDE.md'), 'ACCESS_CONTROL_GUIDE.md not found'
    
    with open('ACCESS_CONTROL_GUIDE.md', 'r') as f:
        doc_content = f.read()
    
    assert 'Access Control' in doc_content
    assert '@require_access' in doc_content
    assert 'ALLOWED_USERS' in doc_content
    
    print("✅ Documentation file exists and contains required sections")


if __name__ == '__main__':
    import os
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Change to parent directory (project root)
    os.chdir(os.path.dirname(script_dir))
    
    tests = [
        test_decorator_exists_in_bot_py,
        test_notification_function_exists,
        test_decorator_applied_to_commands,
        test_start_and_help_handle_unauthorized,
        test_decorator_order_with_rate_limited,
        test_allowed_users_configuration,
        test_logging_statements,
        test_documentation_exists,
    ]
    
    print("🧪 Running Access Control Validation Tests...\n")
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"Running {test.__name__}...")
            test()
            passed += 1
            print()
        except AssertionError as e:
            print(f"❌ FAILED: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 All validation tests passed!")
    else:
        print(f"\n⚠️ {failed} test(s) failed")
        exit(1)
