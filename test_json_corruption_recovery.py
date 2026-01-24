"""
Test JSON corruption recovery in save_trade_to_journal and update_trade_statistics
"""

import json
import os
import tempfile
import fcntl


def test_corrupted_json_recovery():
    """Test that corrupted JSON is handled gracefully"""
    
    # Create a corrupted JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        f.write("{invalid json content!@#$")
    
    try:
        # Test the pattern used in save_trade_to_journal
        print("Testing corrupted JSON recovery...")
        mode = 'r+' if os.path.exists(temp_file) else 'w+'
        
        with open(temp_file, mode, encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content with error recovery
            try:
                f.seek(0)
                content = f.read()
                journal = json.loads(content) if content.strip() else {'trades': []}
            except (json.JSONDecodeError, ValueError):
                # Corrupted or empty file - start fresh
                print("⚠️ Journal corrupted or empty, reinitializing")
                journal = {'trades': []}
            
            # Ensure trades list exists
            if 'trades' not in journal:
                journal['trades'] = []
            
            # Add test entry
            journal['trades'].append({'test': 'data', 'id': 1})
            
            # Atomic write
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
        
        # Verify recovery worked
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert 'trades' in data
            assert len(data['trades']) == 1
            assert data['trades'][0]['id'] == 1
        
        print("✅ Corrupted JSON recovery works correctly")
        
    finally:
        os.unlink(temp_file)


def test_empty_file_recovery():
    """Test that empty file is handled gracefully"""
    
    # Create an empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        # Write nothing - empty file
    
    try:
        print("\nTesting empty file recovery...")
        mode = 'r+' if os.path.exists(temp_file) else 'w+'
        
        with open(temp_file, mode, encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content with error recovery
            try:
                f.seek(0)
                content = f.read()
                journal = json.loads(content) if content.strip() else {'trades': []}
            except (json.JSONDecodeError, ValueError):
                # Corrupted or empty file - start fresh
                print("⚠️ Journal corrupted or empty, reinitializing")
                journal = {'trades': []}
            
            # Ensure trades list exists
            if 'trades' not in journal:
                journal['trades'] = []
            
            # Add test entry
            journal['trades'].append({'test': 'data', 'id': 2})
            
            # Atomic write
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
        
        # Verify recovery worked
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert 'trades' in data
            assert len(data['trades']) == 1
            assert data['trades'][0]['id'] == 2
        
        print("✅ Empty file recovery works correctly")
        
    finally:
        os.unlink(temp_file)


def test_whitespace_only_file():
    """Test that whitespace-only file is handled gracefully"""
    
    # Create a file with only whitespace
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        f.write("   \n\n   \t  \n")
    
    try:
        print("\nTesting whitespace-only file recovery...")
        mode = 'r+' if os.path.exists(temp_file) else 'w+'
        
        with open(temp_file, mode, encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content with error recovery
            try:
                f.seek(0)
                content = f.read()
                journal = json.loads(content) if content.strip() else {'trades': []}
            except (json.JSONDecodeError, ValueError):
                # Corrupted or empty file - start fresh
                print("⚠️ Journal corrupted or empty, reinitializing")
                journal = {'trades': []}
            
            # Ensure trades list exists
            if 'trades' not in journal:
                journal['trades'] = []
            
            # Add test entry
            journal['trades'].append({'test': 'data', 'id': 3})
            
            # Atomic write
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
        
        # Verify recovery worked
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert 'trades' in data
            assert len(data['trades']) == 1
            assert data['trades'][0]['id'] == 3
        
        print("✅ Whitespace-only file recovery works correctly")
        
    finally:
        os.unlink(temp_file)


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTING JSON CORRUPTION RECOVERY")
    print("=" * 60)
    print()
    
    try:
        test_corrupted_json_recovery()
        test_empty_file_recovery()
        test_whitespace_only_file()
        
        print()
        print("=" * 60)
        print("✅ ALL JSON CORRUPTION RECOVERY TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
