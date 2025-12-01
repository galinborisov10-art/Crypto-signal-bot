"""
ТЕСТ НА ENVIRONMENT VARIABLES
===============================

Проверява дали .env файлът е правилно конфигуриран
"""

import os
from dotenv import load_dotenv

def test_env_variables():
    """Тест на environment variables"""
    
    print("=" * 60)
    print("🔐 ТЕСТ НА ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    # Зареди .env
    load_dotenv()
    
    # Провери критични променливи
    variables = {
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'OWNER_CHAT_ID': os.getenv('OWNER_CHAT_ID'),
        'ADMIN_PASSWORD_HASH': os.getenv('ADMIN_PASSWORD_HASH'),
        'BINANCE_PRICE_URL': os.getenv('BINANCE_PRICE_URL'),
        'BINANCE_24H_URL': os.getenv('BINANCE_24H_URL'),
        'BINANCE_KLINES_URL': os.getenv('BINANCE_KLINES_URL'),
    }
    
    print("\n📋 Environment Variables статус:\n")
    
    all_ok = True
    for var_name, var_value in variables.items():
        if var_value:
            # Маскирай токени за сигурност
            if 'TOKEN' in var_name:
                masked = var_value[:10] + "..." + var_value[-10:] if len(var_value) > 20 else "***"
                print(f"   ✅ {var_name}: {masked}")
            elif 'HASH' in var_name:
                print(f"   ✅ {var_name}: {var_value[:16]}... (SHA-256)")
            else:
                print(f"   ✅ {var_name}: {var_value}")
        else:
            print(f"   ❌ {var_name}: НЕ Е ЗАДАДЕН")
            all_ok = False
    
    print("\n" + "=" * 60)
    
    if all_ok:
        print("✅ ВСИЧКИ ENVIRONMENT VARIABLES СА КОРЕКТНИ!")
        print("=" * 60)
        print("\n💡 Бот може да стартира с .env конфигурация")
        return True
    else:
        print("❌ НЯКОИ ENVIRONMENT VARIABLES ЛИПСВАТ!")
        print("=" * 60)
        print("\n💡 Моля попълни .env файла с липсващите стойности")
        return False


if __name__ == '__main__':
    test_env_variables()
