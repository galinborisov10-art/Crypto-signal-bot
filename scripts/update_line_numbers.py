#!/usr/bin/env python3
"""Auto-update line numbers in documentation after code changes"""
import re
from pathlib import Path

def find_function_line(file_path, function_name):
    """Find line number where function is defined"""
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if re.search(rf'^\s*(async\s+)?def\s+{re.escape(function_name)}\s*\(', line):
                return i
    return None

def main():
    repo_root = Path(__file__).parent.parent
    bot_file = repo_root / 'bot.py'
    docs_dir = repo_root / 'docs'
    
    # Functions to track
    functions = [
        'auto_signal_job',
        'monitor_positions_job',
        'generate_signal',
        'main',
        'open_position'
    ]
    
    # Scan current line numbers
    line_numbers = {}
    print("📂 Scanning bot.py...")
    for func in functions:
        line = find_function_line(bot_file, func)
        if line:
            line_numbers[func] = line
            print(f"  ✅ {func:30s} → Line {line}")
        else:
            print(f"  ⚠️  {func:30s} → NOT FOUND")
    
    if not line_numbers:
        print("❌ No functions found - aborting")
        return
    
    # Update documentation files
    print(f"\n📝 Updating documentation in {docs_dir}...")
    updated_count = 0
    
    for doc_file in docs_dir.glob('*.md'):
        with open(doc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        changes = 0
        
        for func, line in line_numbers.items():
            # Pattern: "function() - Line XXXX"
            pattern = rf'({re.escape(func)}\(\).*?-\s*Line\s+)\d+'
            matches = len(re.findall(pattern, content))
            content = re.sub(pattern, rf'\g<1>{line}', content)
            changes += matches
        
        if content != original:
            with open(doc_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  📝 {doc_file.name:40s} → {changes} updates")
            updated_count += 1
        else:
            print(f"  ⏭️  {doc_file.name:40s} → No changes needed")
    
    print(f"\n{'='*70}")
    if updated_count > 0:
        print(f"✅ Successfully updated {updated_count} documentation file(s)")
    else:
        print("ℹ️  No documentation updates were necessary")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
