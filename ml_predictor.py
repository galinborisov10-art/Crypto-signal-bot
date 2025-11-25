"""
ML PREDICTOR - Machine Learning модел за прогнозиране на успешността на сигнали
================================================================================

Този модул тренира Random Forest модел на базата на trading_journal.json
и предсказва вероятността за успех на нови трейдове.

Features използвани за ML:
- RSI (14)
- MA(20), MA(50)
- Volume ratio
- Volatility
- BTC correlation
- News sentiment
- Confidence score
- Timeframe

Автор: Crypto Signal Bot
Версия: 1.0
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("⚠️ scikit-learn не е инсталиран. ML функционалност е недостъпна.")

logger = logging.getLogger(__name__)


class MLPredictor:
    """Machine Learning модел за предсказване на успешни трейдове"""
    
    def __init__(self, model_path='ml_model.pkl', min_training_data=50):
        self.model_path = model_path
        self.min_training_data = min_training_data
        self.model = None
        self.feature_names = [
            'rsi', 'ma_20', 'ma_50', 'volume_ratio', 'volatility',
            'confidence', 'btc_correlation', 'sentiment_score'
        ]
        self.is_trained = False
        
        # Зареди модел ако съществува
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
                logger.info(f"✅ ML модел зареден от {model_path}")
            except Exception as e:
                logger.error(f"❌ Грешка при зареждане на ML модел: {e}")
    
    def extract_features(self, trade_data: Dict) -> Optional[List[float]]:
        """
        Извлича features от trade данни за ML модела
        
        Args:
            trade_data: Речник с analysis_data от трейд
            
        Returns:
            Списък с features или None ако данните са непълни
        """
        try:
            analysis = trade_data.get('analysis_data', {})
            
            # RSI
            rsi = analysis.get('rsi', 50.0)
            if rsi is None:
                rsi = 50.0
            
            # Moving Averages
            ma_20 = analysis.get('ma_20', 0.0)
            ma_50 = analysis.get('ma_50', 0.0)
            
            # Normalize MAs (relative to current price)
            current_price = trade_data.get('entry_price', 1.0)
            ma_20_norm = (ma_20 / current_price - 1) * 100 if ma_20 > 0 else 0.0
            ma_50_norm = (ma_50 / current_price - 1) * 100 if ma_50 > 0 else 0.0
            
            # Volume ratio
            volume_ratio = analysis.get('volume_ratio', 1.0)
            if volume_ratio is None:
                volume_ratio = 1.0
            
            # Volatility (normalized)
            volatility = analysis.get('volatility', 0.0)
            if isinstance(volatility, str):
                volatility_map = {'Ниска': 0.5, 'Средна': 1.0, 'Висока': 2.0, 'Много висока': 3.0}
                volatility = volatility_map.get(volatility, 1.0)
            
            # Confidence
            confidence = trade_data.get('confidence', 50.0)
            
            # BTC correlation
            btc_corr = analysis.get('btc_correlation', {})
            if isinstance(btc_corr, dict):
                btc_corr_strength = btc_corr.get('strength', 0.0)
            else:
                btc_corr_strength = 0.0
            
            # Sentiment
            sentiment = analysis.get('sentiment', {})
            if isinstance(sentiment, dict):
                sentiment_confidence = sentiment.get('confidence', 0.0)
                # Ако sentiment противоречи на signal, направи го отрицателно
                if sentiment.get('sentiment') != trade_data.get('signal_type'):
                    sentiment_confidence = -sentiment_confidence
            else:
                sentiment_confidence = 0.0
            
            features = [
                rsi,
                ma_20_norm,
                ma_50_norm,
                volume_ratio,
                volatility,
                confidence,
                btc_corr_strength,
                sentiment_confidence
            ]
            
            return features
            
        except Exception as e:
            logger.error(f"Грешка при извличане на features: {e}")
            return None
    
    def load_training_data(self, journal_path='trading_journal.json') -> Tuple[np.ndarray, np.ndarray]:
        """
        Зарежда training данни от trading journal
        
        Returns:
            (X, y) - Features и labels
        """
        if not os.path.exists(journal_path):
            logger.warning(f"Trading journal не съществува: {journal_path}")
            return np.array([]), np.array([])
        
        try:
            with open(journal_path, 'r', encoding='utf-8') as f:
                journal = json.load(f)
            
            X = []  # Features
            y = []  # Labels (1=SUCCESS, 0=FAILED)
            
            for trade in journal.get('trades', []):
                # Вземи само завършени трейдове
                if trade.get('outcome') not in ['SUCCESS', 'FAILED']:
                    continue
                
                features = self.extract_features(trade)
                if features is None:
                    continue
                
                X.append(features)
                y.append(1 if trade['outcome'] == 'SUCCESS' else 0)
            
            logger.info(f"📊 Заредени {len(X)} трейда за обучение (SUCCESS: {sum(y)}, FAILED: {len(y) - sum(y)})")
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"❌ Грешка при зареждане на training data: {e}")
            return np.array([]), np.array([])
    
    def train(self, retrain=False) -> bool:
        """
        Тренира ML модела на базата на trading journal
        
        Args:
            retrain: Ако True, препокрива съществуващ модел
            
        Returns:
            True ако обучението е успешно
        """
        if not ML_AVAILABLE:
            logger.error("❌ scikit-learn не е наличен. Инсталирай с: pip install scikit-learn")
            return False
        
        if self.is_trained and not retrain:
            logger.info("ℹ️ ML модел вече е тренирай. Използвай retrain=True за препокриване.")
            return True
        
        # Зареди данни
        X, y = self.load_training_data()
        
        if len(X) < self.min_training_data:
            logger.warning(f"⚠️ Недостатъчно данни за обучение. Нужни {self.min_training_data}, налични {len(X)}")
            return False
        
        try:
            # Split на train/test
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Тренирай Random Forest
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'  # За баланс между SUCCESS/FAILED
            )
            
            logger.info("🔄 Започвам обучение на ML модел...")
            self.model.fit(X_train, y_train)
            
            # Оценка на модела
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)
            
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"✅ ML модел тренирай успешно!")
            logger.info(f"📊 Train accuracy: {train_score*100:.1f}%")
            logger.info(f"📊 Test accuracy: {test_score*100:.1f}%")
            logger.info(f"📊 Overall accuracy: {accuracy*100:.1f}%")
            
            # Feature importance
            feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            logger.info("🔍 Най-важни features:")
            for fname, importance in sorted_features[:5]:
                logger.info(f"   • {fname}: {importance*100:.1f}%")
            
            # Запази модела
            joblib.dump(self.model, self.model_path)
            logger.info(f"💾 ML модел запазен в {self.model_path}")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Грешка при обучение на ML модел: {e}")
            return False
    
    def predict(self, trade_data: Dict) -> Optional[float]:
        """
        Предсказва вероятността за успех на даден трейд
        
        Args:
            trade_data: Речник с analysis_data
            
        Returns:
            Вероятност за успех (0-100%) или None ако модел не е тренирай
        """
        if not self.is_trained:
            logger.warning("⚠️ ML модел не е тренирай. Използвай train() първо.")
            return None
        
        features = self.extract_features(trade_data)
        if features is None:
            return None
        
        try:
            # Predict probability
            features_array = np.array([features])
            probability = self.model.predict_proba(features_array)[0][1]  # Probability of SUCCESS
            
            return probability * 100  # Върни като процент
            
        except Exception as e:
            logger.error(f"❌ Грешка при ML предикция: {e}")
            return None
    
    def get_confidence_adjustment(self, ml_probability: float, current_confidence: float) -> float:
        """
        Изчислява корекция на confidence базирана на ML прогноза
        
        Args:
            ml_probability: ML вероятност за успех (0-100)
            current_confidence: Текущ confidence от техническия анализ (0-100)
            
        Returns:
            Корекция за confidence (-20 до +20)
        """
        # Ако ML е много по-уверен от техническия анализ
        diff = ml_probability - current_confidence
        
        # Ограничи корекцията до ±20%
        adjustment = max(-20, min(20, diff * 0.3))
        
        return adjustment


# Singleton instance
_ml_predictor = None

def get_ml_predictor() -> MLPredictor:
    """Връща singleton instance на ML predictor"""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = MLPredictor()
    return _ml_predictor


if __name__ == '__main__':
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    predictor = MLPredictor()
    
    # Опит за обучение
    if predictor.train():
        print("\n✅ ML модел е готов за използване!")
    else:
        print("\n⚠️ ML модел не може да бъде тренирай (нужни поне 50 завършени трейда)")
