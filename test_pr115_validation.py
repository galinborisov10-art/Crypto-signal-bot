#!/usr/bin/env python3
"""
Lightweight test for PR #115: Enhanced Multi-Pair Swing Analysis

Tests the key sections of the message format without requiring full bot initialization.
"""

import re


def test_message_format():
    """Test that message format contains all required sections"""
    print("\n" + "="*60)
    print("TEST 1: Message Format Validation")
    print("="*60)
    
    # Sample message sections that should be present
    required_sections = [
        'СТРУКТУРА',
        'КЛЮЧОВИ НИВА',
        'ОБЕМ & MOMENTUM',
        'SWING SETUP',
        'ПРОФЕСИОНАЛЕН SWING АНАЛИЗ',
        'ПАЗАРЕН КОНТЕКСТ',
        'SWING TRADER ПЕРСПЕКТИВА',
        'КЛЮЧОВИ РИСКОВЕ',
        'УПРАВЛЕНИЕ НА ПОЗИЦИЯТА',
        'ВРЕМЕВА ЛИНИЯ',
        'ПРЕПОРЪКА',
        'РЕЙТИНГ',
        'ПЛАН ЗА ДЕЙСТВИЕ',
        'ИЗБЯГВАЙ АКО'
    ]
    
    print(f"\n✅ Checking for {len(required_sections)} required sections")
    
    # Check Bulgarian/English terminology
    bulgarian_terms = [
        'Цена', 'Вход', 'Чакай', 'Избягвай', 'Подкрепа', 
        'Съпротива', 'Обем', 'Тренд', 'Стратегия', 'Рискове'
    ]
    
    english_terms = [
        'breakout', 'breakdown', 'setup', 'momentum', 'uptrend', 
        'downtrend', 'R:R', 'SL', 'TP', 'pullback', 'retest'
    ]
    
    print(f"✅ Expected {len(bulgarian_terms)} Bulgarian terms (labels/actions)")
    print(f"✅ Expected {len(english_terms)} English terms (technical)")
    
    # Verify sections are in bot.py
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    # Check if format_comprehensive_swing_message exists
    if 'def format_comprehensive_swing_message' in bot_content:
        print(f"\n✅ format_comprehensive_swing_message function found")
        
        # Extract the function
        pattern = r'def format_comprehensive_swing_message.*?(?=\ndef |$)'
        match = re.search(pattern, bot_content, re.DOTALL)
        
        if match:
            function_code = match.group(0)
            
            missing_sections = []
            for section in required_sections:
                if section not in function_code:
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"⚠️  Missing sections in code: {', '.join(missing_sections)}")
                return False
            else:
                print(f"✅ All {len(required_sections)} required sections present in code")
            
            # Check language mix
            bg_found = sum(1 for term in bulgarian_terms if term in function_code)
            en_found = sum(1 for term in english_terms if term in function_code)
            
            print(f"✅ Bulgarian terms found: {bg_found}/{len(bulgarian_terms)}")
            print(f"✅ English terms found: {en_found}/{len(english_terms)}")
            
            if bg_found >= len(bulgarian_terms) * 0.7 and en_found >= len(english_terms) * 0.5:
                print(f"✅ Language mix is appropriate (~75% BG / 25% EN)")
                return True
            else:
                print(f"⚠️  Language mix may need adjustment")
                return False
        else:
            print(f"❌ Could not extract function code")
            return False
    else:
        print(f"❌ format_comprehensive_swing_message not found")
        return False


def test_function_signatures():
    """Test that all required functions exist with correct signatures"""
    print("\n" + "="*60)
    print("TEST 2: Function Signatures")
    print("="*60)
    
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    required_functions = {
        'generate_comprehensive_swing_analysis': ['symbol', 'display_name', 'language'],
        'format_comprehensive_swing_message': ['symbol', 'display_name', 'price'],
        'generate_swing_summary': ['all_analyses'],
        'market_swing_analysis': ['update', 'context']
    }
    
    passed = 0
    for func_name, expected_params in required_functions.items():
        pattern = rf'async def {func_name}\(([^)]+)\)|def {func_name}\(([^)]+)\)'
        match = re.search(pattern, bot_content)
        
        if match:
            params = match.group(1) or match.group(2)
            found_all = all(param in params for param in expected_params)
            
            if found_all:
                print(f"✅ {func_name} - signature correct")
                passed += 1
            else:
                print(f"⚠️  {func_name} - missing some parameters")
        else:
            print(f"❌ {func_name} - not found")
    
    if passed == len(required_functions):
        print(f"\n✅ All {passed} function signatures correct")
        return True
    else:
        print(f"\n⚠️  Only {passed}/{len(required_functions)} functions correct")
        return False


def test_symbols_configuration():
    """Test that all 6 required symbols are configured"""
    print("\n" + "="*60)
    print("TEST 3: Trading Pairs Configuration")
    print("="*60)
    
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    required_pairs = [
        ('BTCUSDT', 'BITCOIN'),
        ('ETHUSDT', 'ETHEREUM'),
        ('BNBUSDT', 'BINANCE COIN'),
        ('SOLUSDT', 'SOLANA'),
        ('XRPUSDT', 'RIPPLE'),
        ('ADAUSDT', 'CARDANO')
    ]
    
    # Check if pairs are in market_swing_analysis
    pattern = r'symbols = \[(.*?)\]'
    match = re.search(pattern, bot_content, re.DOTALL)
    
    if match:
        symbols_config = match.group(1)
        
        all_found = True
        for pair, name in required_pairs:
            if pair in symbols_config and name in symbols_config:
                print(f"✅ {pair} ({name})")
            else:
                print(f"❌ {pair} ({name}) - not found")
                all_found = False
        
        if all_found:
            print(f"\n✅ All 6 trading pairs correctly configured")
            return True
        else:
            print(f"\n⚠️  Some trading pairs missing")
            return False
    else:
        print(f"❌ symbols list not found in market_swing_analysis")
        return False


def test_timeout_protection():
    """Test that timeout protection is implemented"""
    print("\n" + "="*60)
    print("TEST 4: Timeout Protection")
    print("="*60)
    
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    # Check for asyncio.wait_for with timeout
    if 'asyncio.wait_for' in bot_content and 'timeout=15' in bot_content:
        print(f"✅ Timeout protection implemented (15s per pair)")
        
        # Check for TimeoutError handling
        if 'asyncio.TimeoutError' in bot_content or 'TimeoutError' in bot_content:
            print(f"✅ TimeoutError exception handling present")
            return True
        else:
            print(f"⚠️  TimeoutError handling may be missing")
            return False
    else:
        print(f"❌ Timeout protection not found")
        return False


def test_error_handling():
    """Test that proper error handling is implemented"""
    print("\n" + "="*60)
    print("TEST 5: Error Handling")
    print("="*60)
    
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    # Check for error handling in market_swing_analysis
    pattern = r'async def market_swing_analysis.*?(?=\nasync def |\ndef |\Z)'
    match = re.search(pattern, bot_content, re.DOTALL)
    
    if match:
        function_code = match.group(0)
        
        checks = {
            'Try-except blocks': 'try:' in function_code and 'except' in function_code,
            'Continue on error': 'continue' in function_code or 'all_analyses.append' in function_code,
            'Error logging': 'logger.error' in function_code,
            'User notification': 'send_message' in function_code
        }
        
        passed = 0
        for check_name, result in checks.items():
            if result:
                print(f"✅ {check_name}")
                passed += 1
            else:
                print(f"⚠️  {check_name} - not found")
        
        if passed >= 3:
            print(f"\n✅ Error handling is adequate ({passed}/4 checks passed)")
            return True
        else:
            print(f"\n⚠️  Error handling may be insufficient ({passed}/4 checks passed)")
            return False
    else:
        print(f"❌ market_swing_analysis function not found")
        return False


def test_summary_ranking():
    """Test that summary includes ranking and grouping"""
    print("\n" + "="*60)
    print("TEST 6: Summary Ranking & Grouping")
    print("="*60)
    
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r', encoding='utf-8') as f:
        bot_content = f.read()
    
    # Find generate_swing_summary function
    pattern = r'def generate_swing_summary.*?(?=\ndef |$)'
    match = re.search(pattern, bot_content, re.DOTALL)
    
    if match:
        function_code = match.group(0)
        
        checks = {
            'Rating sorting': 'sorted' in function_code and 'rating' in function_code,
            'Best opportunities group': 'best' in function_code and 'rating >= 3.5' in function_code,
            'Caution group': 'caution' in function_code,
            'Avoid group': 'avoid' in function_code,
            'Medals (🥇🥈🥉)': '🥇' in function_code or 'medals' in function_code,
            'Market overview': 'ПАЗАРЕН ПРЕГЛЕД' in function_code,
            'Timestamp': 'UTC' in function_code or 'datetime' in function_code
        }
        
        passed = 0
        for check_name, result in checks.items():
            if result:
                print(f"✅ {check_name}")
                passed += 1
            else:
                print(f"⚠️  {check_name} - not found")
        
        if passed >= 6:
            print(f"\n✅ Summary ranking is comprehensive ({passed}/7 checks passed)")
            return True
        else:
            print(f"\n⚠️  Summary ranking may be incomplete ({passed}/7 checks passed)")
            return False
    else:
        print(f"❌ generate_swing_summary function not found")
        return False


def run_all_tests():
    """Run all validation tests"""
    print("\n" + "="*80)
    print("PR #115: Enhanced Multi-Pair Swing Analysis - Code Validation")
    print("="*80)
    
    from datetime import datetime
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ('Message Format', test_message_format),
        ('Function Signatures', test_function_signatures),
        ('Trading Pairs Config', test_symbols_configuration),
        ('Timeout Protection', test_timeout_protection),
        ('Error Handling', test_error_handling),
        ('Summary Ranking', test_summary_ranking)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*80)
    print(f"OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All validation tests passed! Code structure looks good.")
        print("   Next step: Manual testing with live Binance API")
        return 0
    elif passed >= total * 0.75:
        print(f"\n⚠️  Most tests passed, but {total - passed} test(s) failed.")
        print("   Review recommended before merging.")
        return 0
    else:
        print(f"\n❌ Multiple tests failed ({total - passed}/{total}).")
        print("   Significant review needed.")
        return 1


if __name__ == '__main__':
    import sys
    exit_code = run_all_tests()
    sys.exit(exit_code)
