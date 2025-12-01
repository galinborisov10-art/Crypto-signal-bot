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
        # Динамични пътища
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(base_dir, 'ml_model.pkl')
        self.scaler_path = os.path.join(base_dir, 'ml_scaler.pkl')
        self.training_data_path = os.path.join(base_dir, 'ml_training_data.json')
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
        """Обучава ML модела с наличните данни"""
        try:
            # Зареди training data
            if not os.path.exists(self.training_data_path):
                print("⚠️ No training data available")
                return False
            
            with open(self.training_data_path, 'r') as f:
                data = json.load(f)
            
            if len(data['samples']) < self.min_training_samples:
                print(f"⚠️ Not enough samples ({len(data['samples'])} / {self.min_training_samples})")
                return False
            
            # Подготви features и labels
            X = []
            y = []
            
            for sample in data['samples']:
                X.append(sample['features'])
                
                # Mapping: BUY=1, SELL=2, HOLD=0
                signal = sample['signal']
                success = sample['success']
                
                # Ако сигналът е успешен - запомни го
                if success:
                    if signal == 'BUY':
                        y.append(1)
                    elif signal == 'SELL':
                        y.append(2)
                    else:
                        y.append(0)
                else:
                    # Ако сигналът FAIL - обърни го (учи от грешки)
                    if signal == 'BUY':
                        y.append(2)  # Трябваше да е SELL
                    elif signal == 'SELL':
                        y.append(1)  # Трябваше да е BUY
                    else:
                        y.append(0)
            
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
            print(f"📊 Samples: {len(data['samples'])}")
            print(f"🎯 Training accuracy: {accuracy*100:.1f}%")
            
            # Адаптивно увеличаване на ML weight
            self.adjust_ml_weight(len(data['samples']), accuracy)
            
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
            if os.path.exists(self.training_data_path):
                with open(self.training_data_path, 'r') as f:
                    data = json.load(f)
                num_samples = len(data['samples'])
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
