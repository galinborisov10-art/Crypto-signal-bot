"""
🤖 MACHINE LEARNING ENGINE
Самообучаваща се система за оптимизация на сигнали
"""

import json
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

class MLTradingEngine:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        
        # Auto-detect base path (works on Codespace AND server)
        if os.path.exists('/root/Crypto-signal-bot'):
            base_path = '/root/Crypto-signal-bot'
        else:
            base_path = '/workspaces/Crypto-signal-bot'
        
        self.model_path = f'{base_path}/ml_model.pkl'
        self.scaler_path = f'{base_path}/ml_scaler.pkl'
        self.trading_journal_path = f'{base_path}/trading_journal.json'
        self.min_training_samples = 50  # Минимум данни за обучение
        self.hybrid_mode = True  # Стартира в хибриден режим
        self.ml_weight = 0.3  # Първоначално 30% ML, 70% класически
        
        # Зареди модел ако съществува
        self.load_model()
    
    def extract_features(self, analysis):
        """Извлича features от анализа за ML"""
        try:
            features = [
                analysis.get('rsi', 50),
                analysis.get('ma_20', 0),
                analysis.get('ma_50', 0),
                analysis.get('volume_ratio', 1),
                analysis.get('price_position', 50),
                analysis.get('volatility_score', 5),
                analysis.get('trend_strength', 0),
                analysis.get('btc_correlation', 0),
                analysis.get('order_book_pressure', 0),
                analysis.get('sentiment_score', 0),
                analysis.get('change_24h', 0),
                analysis.get('high_low_range', 0),
            ]
            return np.array(features).reshape(1, -1)
        except Exception as e:
            print(f"❌ Feature extraction error: {e}")
            return None
    
    def predict_signal(self, analysis, classical_signal, classical_confidence):
        """Предсказва сигнал с ML и комбинира с класически"""
        try:
            # Ако няма модел или малко данни - използвай класически
            if self.model is None:
                return classical_signal, classical_confidence, "Classical (No ML model)"
            
            # Извлечи features
            features = self.extract_features(analysis)
            if features is None:
                return classical_signal, classical_confidence, "Classical (Feature error)"
            
            # Normalize features
            features_scaled = self.scaler.transform(features)
            
            # ML предсказание
            ml_prediction = self.model.predict(features_scaled)[0]
            ml_proba = self.model.predict_proba(features_scaled)[0]
            ml_confidence = max(ml_proba) * 100
            
            # Mapping: 0 = HOLD, 1 = BUY, 2 = SELL
            signal_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
            ml_signal = signal_map.get(ml_prediction, 'HOLD')
            
            # HYBRID MODE: Комбинирай ML + Classical
            if self.hybrid_mode:
                # Ако сигналите съвпадат - boost confidence
                if ml_signal == classical_signal:
                    final_confidence = (classical_confidence * (1 - self.ml_weight) + 
                                      ml_confidence * self.ml_weight)
                    final_signal = classical_signal
                    mode = f"Hybrid ({int((1-self.ml_weight)*100)}% Classical + {int(self.ml_weight*100)}% ML) ✅"
                else:
                    # Сигналите се различават - използвай weights
                    if ml_confidence * self.ml_weight > classical_confidence * (1 - self.ml_weight):
                        final_signal = ml_signal
                        final_confidence = ml_confidence * 0.9  # Penalty за конфликт
                        mode = f"Hybrid (ML override) ⚠️"
                    else:
                        final_signal = classical_signal
                        final_confidence = classical_confidence * 0.85  # Малък penalty
                        mode = f"Hybrid (Classical override) ⚠️"
            else:
                # FULL ML MODE
                final_signal = ml_signal
                final_confidence = ml_confidence
                mode = "Pure ML 🤖"
            
            return final_signal, final_confidence, mode
            
        except Exception as e:
            print(f"❌ ML prediction error: {e}")
            return classical_signal, classical_confidence, f"Classical (ML error: {e})"
    
    def record_outcome(self, symbol, timeframe, signal, confidence, features, success):
        """Записва резултата за обучение"""
        try:
            # Зареди текущи данни
            if os.path.exists(self.training_data_path):
                with open(self.training_data_path, 'r') as f:
                    data = json.load(f)
            else:
                data = {'samples': []}
            
            # Добави нов sample
            sample = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'timeframe': timeframe,
                'signal': signal,
                'confidence': confidence,
                'features': features.tolist() if isinstance(features, np.ndarray) else features,
                'success': success  # True/False
            }
            
            data['samples'].append(sample)
            
            # Запази
            with open(self.training_data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Recorded outcome: {symbol} {signal} -> {'WIN' if success else 'LOSS'}")
            
            # Автоматично re-train при достигане на праг
            if len(data['samples']) >= self.min_training_samples:
                if len(data['samples']) % 20 == 0:  # Re-train на всеки 20 сигнала
                    self.train_model()
            
        except Exception as e:
            print(f"❌ Record outcome error: {e}")
    
    def train_model(self):
        """Обучава ML модела с данни от trading_journal.json"""
        try:
            # Зареди trading journal
            if not os.path.exists(self.trading_journal_path):
                print("⚠️ No trading journal available")
                return False
            
            with open(self.trading_journal_path, 'r') as f:
                journal = json.load(f)
            
            trades = journal.get('trades', [])
            
            if len(trades) < self.min_training_samples:
                print(f"⚠️ Not enough trades ({len(trades)} / {self.min_training_samples})")
                return False
            
            # Подготви features и labels
            X = []
            y = []
            
            for trade in trades:
                # Пропусни trades без outcome
                if not trade.get('outcome'):
                    continue
                
                conditions = trade.get('conditions', {})
                
                # Calculate normalized MA values if needed (match ml_predictor.py logic)
                ma_20_norm = conditions.get('ma_20_norm', 0)
                ma_50_norm = conditions.get('ma_50_norm', 0)
                
                # If normalized values not stored, calculate from raw values
                if ma_20_norm == 0 and 'ma_20' in conditions:
                    entry_price = trade.get('entry_price', 1)
                    ma_20 = conditions.get('ma_20', 0)
                    ma_20_norm = (ma_20 / entry_price - 1) * 100 if ma_20 > 0 and entry_price > 0 else 0
                
                if ma_50_norm == 0 and 'ma_50' in conditions:
                    entry_price = trade.get('entry_price', 1)
                    ma_50 = conditions.get('ma_50', 0)
                    ma_50_norm = (ma_50 / entry_price - 1) * 100 if ma_50 > 0 and entry_price > 0 else 0
                
                # Extract sentiment confidence
                sentiment_confidence = conditions.get('sentiment_confidence', 0)
                if sentiment_confidence == 0 and 'sentiment' in conditions:
                    sentiment = conditions.get('sentiment', {})
                    if isinstance(sentiment, dict):
                        sentiment_confidence = sentiment.get('confidence', 0)
                
                # Extract BTC correlation strength
                btc_correlation = conditions.get('btc_correlation', 0)
                if isinstance(btc_correlation, dict):
                    btc_correlation = btc_correlation.get('strength', 0)
                
                # Извлечи features (8 features - match ml_predictor.py)
                features = [
                    conditions.get('rsi', 50),
                    ma_20_norm,
                    ma_50_norm,
                    conditions.get('volume_ratio', 1),
                    conditions.get('volatility', 5),
                    trade.get('confidence', 50),
                    btc_correlation,
                    sentiment_confidence,
                ]
                
                X.append(features)
                
                # Label: WIN=1, LOSS=0
                outcome = trade.get('outcome')
                if outcome == 'WIN':
                    y.append(1)
                else:
                    y.append(0)
            
            if len(X) < self.min_training_samples:
                print(f"⚠️ Not enough completed trades ({len(X)} / {self.min_training_samples})")
                return False
            
            X = np.array(X)
            y = np.array(y)
            
            # Normalize features
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Train RandomForest
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
            
            self.model.fit(X_scaled, y)
            
            # Запази модела
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            # Изчисли точност
            accuracy = self.model.score(X_scaled, y)
            
            print(f"✅ ML Model trained successfully!")
            print(f"📊 Samples: {len(X)}")
            print(f"🎯 Training accuracy: {accuracy*100:.1f}%")
            
            # Адаптивно увеличаване на ML weight
            self.adjust_ml_weight(len(X), accuracy)
            
            return True
            
        except Exception as e:
            print(f"❌ Training error: {e}")
            return False
    
    def adjust_ml_weight(self, num_samples, accuracy):
        """Адаптивно регулиране на ML тежестта"""
        # Week 1-2: 30% ML
        if num_samples < 100:
            self.ml_weight = 0.3
        # Week 3-4: 50% ML (ако точност > 65%)
        elif num_samples < 200 and accuracy > 0.65:
            self.ml_weight = 0.5
        # Week 5-6: 70% ML (ако точност > 70%)
        elif num_samples < 300 and accuracy > 0.70:
            self.ml_weight = 0.7
        # Month 2+: 90% ML (ако точност > 75%)
        elif accuracy > 0.75:
            self.ml_weight = 0.9
            self.hybrid_mode = False  # Премини на full ML
        
        print(f"⚙️ ML Weight adjusted to: {int(self.ml_weight*100)}%")
    
    def load_model(self):
        """Зарежда запазен модел"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                print("✅ ML Model loaded successfully")
                return True
            else:
                print("⚠️ No saved ML model found")
                return False
        except Exception as e:
            print(f"❌ Model load error: {e}")
            return False
    
    def get_status(self):
        """Връща статус на ML системата"""
        try:
            # Брой trades от trading_journal
            if os.path.exists(self.trading_journal_path):
                with open(self.trading_journal_path, 'r') as f:
                    journal = json.load(f)
                num_samples = journal.get('metadata', {}).get('total_trades', 0)
            else:
                num_samples = 0
            
            return {
                'model_trained': self.model is not None,
                'hybrid_mode': self.hybrid_mode,
                'ml_weight': self.ml_weight,
                'training_samples': num_samples,
                'min_samples_needed': self.min_training_samples,
                'ready_for_training': num_samples >= self.min_training_samples
            }
        except:
            return {'error': 'Failed to get status'}


# Global ML instance
ml_engine = MLTradingEngine()
