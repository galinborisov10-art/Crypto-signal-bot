#!/usr/bin/env python3
"""
Test script to verify bot version tracking functionality
"""
import os
import json
from datetime import datetime, timezone, timedelta

def test_version_file_exists():
    """Test that VERSION file exists and is readable"""
    print("🧪 Test 1: VERSION file exists...")
    base_path = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(base_path, 'VERSION')
    
    assert os.path.exists(version_file), "VERSION file not found"
    
    with open(version_file, 'r') as f:
        version = f.read().strip()
    
    assert version, "VERSION file is empty"
    assert len(version) > 0, "VERSION is too short"
    
    print(f"✅ VERSION file exists: v{version}")
    return True

def test_deployment_info_structure():
    """Test deployment info file structure"""
    print("\n🧪 Test 2: Deployment info structure...")
    base_path = os.path.dirname(os.path.abspath(__file__))
    deployment_file = os.path.join(base_path, '.deployment-info')
    
    # File might not exist in dev environment - that's OK
    if not os.path.exists(deployment_file):
        print("⚠️ .deployment-info not found (OK in dev environment)")
        return True
    
    with open(deployment_file, 'r') as f:
        deployment_info = json.load(f)
    
    # Verify expected fields
    expected_fields = ['version', 'last_deployed', 'commit_sha', 'deployed_from']
    for field in expected_fields:
        assert field in deployment_info, f"Missing field: {field}"
    
    print(f"✅ Deployment info structure valid")
    print(f"   - Version: {deployment_info.get('version')}")
    print(f"   - Last Deploy: {deployment_info.get('last_deployed')}")
    print(f"   - Commit: {deployment_info.get('commit_sha')}")
    
    return True

def test_bot_start_time_tracking():
    """Test BOT_START_TIME variable and uptime calculation"""
    print("\n🧪 Test 3: Bot start time tracking...")
    
    # Simulate bot start
    bot_start_time = datetime.now(timezone.utc)
    
    # Wait a moment
    import time
    time.sleep(1)
    
    # Calculate uptime
    uptime = datetime.now(timezone.utc) - bot_start_time
    uptime_str = str(uptime).split('.')[0]
    
    # Verify uptime is reasonable
    assert uptime.total_seconds() >= 1, "Uptime should be at least 1 second"
    assert uptime.total_seconds() < 10, "Uptime should be less than 10 seconds for test"
    
    print(f"✅ Uptime calculation works: {uptime_str}")
    
    return True

def test_systemd_service_file():
    """Test systemd service file has required configurations"""
    print("\n🧪 Test 4: Systemd service file configuration...")
    base_path = os.path.dirname(os.path.abspath(__file__))
    service_file = os.path.join(base_path, 'crypto-signal-bot.service')
    
    assert os.path.exists(service_file), "Service file not found"
    
    with open(service_file, 'r') as f:
        content = f.read()
    
    # Check for critical configurations
    required_configs = [
        'PYTHONDONTWRITEBYTECODE=1',
        'PYTHONUNBUFFERED=1',
        'ExecStartPre',
        'KillMode=mixed',
        'KillSignal=SIGTERM'
    ]
    
    missing = []
    for config in required_configs:
        if config not in content:
            missing.append(config)
    
    if missing:
        print(f"❌ Missing configurations: {', '.join(missing)}")
        return False
    
    print("✅ Systemd service file has all required configurations")
    return True

def test_deployment_workflow():
    """Test deployment workflow has proper cleanup steps"""
    print("\n🧪 Test 5: Deployment workflow configuration...")
    base_path = os.path.dirname(os.path.abspath(__file__))
    workflow_file = os.path.join(base_path, '.github/workflows/deploy.yml')
    
    assert os.path.exists(workflow_file), "Deploy workflow not found"
    
    with open(workflow_file, 'r') as f:
        content = f.read()
    
    # Check for critical steps
    required_steps = [
        'systemctl stop crypto-bot',
        'pkill -9 -f "python.*bot.py"',
        'systemctl daemon-reload',
        'systemctl start crypto-bot',
        'BOT_PID='
    ]
    
    missing = []
    for step in required_steps:
        if step not in content:
            missing.append(step)
    
    if missing:
        print(f"❌ Missing workflow steps: {', '.join(missing)}")
        return False
    
    print("✅ Deployment workflow has proper cleanup and verification")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 VERSION TRACKING TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_version_file_exists,
        test_deployment_info_structure,
        test_bot_start_time_tracking,
        test_systemd_service_file,
        test_deployment_workflow
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("✅ All tests passed! Version tracking is properly configured.")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
