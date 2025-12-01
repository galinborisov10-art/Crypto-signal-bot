"""
ТЕСТОВ СКРИПТ ЗА ML PREDICTOR
===============================

Тества ML predictor функционалността с реални данни от trading_journal.json
"""

import json
import os
from ml_predictor import MLPredictor, get_ml_predictor

def test_ml_predictor():
    """Тест на ML predictor"""
    
    print("=" * 60)
    print("🧪 ТЕСТ НА ML PREDICTOR")
    print("=" * 60)
    
    # 1. Провери дали има trading journal
    if not os.path.exists('trading_journal.json'):
        print("\n⚠️ trading_journal.json не съществува.")
        print("💡 ML модел ще се трейни автоматично след 50+ завършени трейда")
        return False
    
    # 2. Зареди trading journal
    with open('trading_journal.json', 'r', encoding='utf-8') as f:
        journal = json.load(f)
    
    total_trades = len(journal.get('trades', []))
    completed_trades = [t for t in journal.get('trades', []) if t.get('outcome') in ['SUCCESS', 'FAILED']]
    
    print(f"\n📊 Trading Journal статистика:")
    print(f"   • Общо трейдове: {total_trades}")
    print(f"   • Завършени трейдове: {len(completed_trades)}")
    print(f"   • Успешни: {sum(1 for t in completed_trades if t['outcome'] == 'SUCCESS')}")
    print(f"   • Неуспешни: {sum(1 for t in completed_trades if t['outcome'] == 'FAILED')}")
    
    # 3. Създай ML predictor
    predictor = MLPredictor(min_training_data=10)  # Понижени изисквания за тест
    
    # 4. Опитай се да тренираш модела
    print(f"\n🔄 Опит за тренировка на ML модел...")
    
    if len(completed_trades) < 10:
        print(f"\n⚠️ Недостатъчно данни за обучение.")
        print(f"💡 Нужни поне 10 завършени трейда, налични {len(completed_trades)}")
        print(f"✅ ML модел ще се активира автоматично след още {10 - len(completed_trades)} трейда")
        return False
    
    success = predictor.train()
    
    if not success:
        print("\n❌ ML модел не може да бъде тренирай")
        return False
    
    print("\n✅ ML модел е тренирай успешно!")
    
    # 5. Тест на прогнозиране
    print("\n🔍 Тест на прогнозиране с примерни данни...")
    
    # Примерен трейд данни
    test_trade = {
        'signal_type': 'BUY',
        'confidence': 75,
        'entry_price': 95000,
        'analysis_data': {
            'rsi': 45,
            'ma_20': 94500,
            'ma_50': 93000,
            'volume_ratio': 1.5,
            'volatility': 'Средна',
            'btc_correlation': {'strength': 0.8, 'trend': 'BUY'},
            'sentiment': {'sentiment': 'BUY', 'confidence': 5}
        }
    }
    
    probability = predictor.predict(test_trade)
    
    if probability is not None:
        print(f"   🤖 ML Прогноза: {probability:.1f}% вероятност за успех")
        
        if probability >= 75:
            print(f"   ✅ Висока вероятност - препоръчителен трейд")
        elif probability >= 60:
            print(f"   👍 Добра вероятност - разгледай трейд")
        elif probability >= 50:
            print(f"   ⚠️ Средна вероятност - внимавай")
        else:
            print(f"   ❌ Ниска вероятност - избягвай трейд")
        
        # Confidence adjustment
        adjustment = predictor.get_confidence_adjustment(probability, test_trade['confidence'])
        print(f"   📊 Confidence корекция: {adjustment:+.0f}%")
        
    else:
        print("   ❌ Грешка при прогнозиране")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ВСИЧКИ ТЕСТОВЕ УСПЕШНИ!")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    test_ml_predictor()
