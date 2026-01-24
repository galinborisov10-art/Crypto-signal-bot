"""
🤖 MACHINE LEARNING ENGINE - UPGRADED
Самообучаваща се система за оптимизация на сигнали

New Features:
- Complete feature extraction (all ICT indicators)
- Real-time model retraining
- Backtest validation
- Performance tracking
- Auto-tuning hyperparameters
- Ensemble models (Random Forest + XGBoost)
- Feature importance analysis
"""

import json
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib
import os
import logging
import fcntl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ML FEATURE SCHEMA - Canonical Definition
# ============================================================================
# This schema defines required features for ML training and prediction.
# Validation ensures feature compatibility between training and prediction.
# ============================================================================

REQUIRED_ML_FEATURES = [
    'rsi',
    'confidence',
    'volume_ratio',
    'trend_strength',
    'volatility',
    'timeframe',
    'signal_type'
]

# Feature type expectations
FEATURE_TYPES = {
    'rsi': (int, float),
    'confidence': (int, float),
    'volume_ratio': (int, float),
    'trend_strength': (int, float),
    'volatility': (int, float),
    'timeframe': str,
    'signal_type': str
}

# Valid categorical values
VALID_TIMEFRAMES = ['1h', '2h', '4h', '1d']
VALID_SIGNAL_TYPES = ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']


def _validate_ml_features(analysis: dict) -> tuple:
    """
    Validate that analysis dict contains all required ML features.
    
    This is a sanity gate to prevent training/prediction feature mismatch.
    
    Args:
        analysis: Signal analysis dictionary
        
    Returns:
        Tuple of (is_valid, missing_features)
        - is_valid: True if all required features present and valid
        - missing_features: List of missing/invalid feature names
    """
    missing = []
    
    # Check required features exist
    for feature in REQUIRED_ML_FEATURES:
        if feature not in analysis:
            missing.append(f"{feature} (missing)")
            continue
        
        value = analysis[feature]
        
        # Check None values
        if value is None:
            missing.append(f"{feature} (None)")
            continue
        
        # Check type validity
        expected_types = FEATURE_TYPES.get(feature)
        if expected_types and not isinstance(value, expected_types):
            missing.append(f"{feature} (wrong type: {type(value).__name__})")
            continue
        
        # Check categorical values
        if feature == 'timeframe' and value not in VALID_TIMEFRAMES:
            missing.append(f"timeframe (invalid: {value})")
        elif feature == 'signal_type' and value not in VALID_SIGNAL_TYPES:
            missing.append(f"signal_type (invalid: {value})")
    
    is_valid = len(missing) == 0
    return is_valid, missing


class MLTradingEngine:
    def __init__(self):
        self.model = None
        self.ensemble_model = None
        self.scaler = StandardScaler()
        
        # Auto-detect base path (works on Codespace AND server)
        if os.path.exists('/root/Crypto-signal-bot'):
            base_path = '/root/Crypto-signal-bot'
        else:
            base_path = '/workspaces/Crypto-signal-bot'
        
        self.model_path = f'{base_path}/ml_model.pkl'
        self.ensemble_path = f'{base_path}/ml_ensemble.pkl'
        self.scaler_path = f'{base_path}/ml_scaler.pkl'
        self.trading_journal_path = f'{base_path}/trading_journal.json'
        self.performance_path = f'{base_path}/ml_performance.json'
        self.feature_importance_path = f'{base_path}/ml_feature_importance.json'
        
        self.min_training_samples = 50  # Минимум данни за обучение
        self.hybrid_mode = True  # Стартира в хибриден режим
        self.ml_weight = 0.3  # Първоначално 30% ML, 70% класически
        self.use_ensemble = False  # Enable ensemble after enough data
        
        # Performance tracking
        self.performance_history = []
        self.feature_importance = {}
        self.last_training_time = None
        self.retrain_interval_days = 7
        
        # Зареди модел ако съществува
        self.load_model()
        self.load_performance_history()
    
    def get_ml_prediction(self, analysis: dict) -> dict:
        """
        Get ML prediction for signal.
        
        Args:
            analysis: Signal analysis dictionary
            
        Returns:
            Dict with ML prediction result
        """
        try:
            # SANITY GATE: Validate feature schema
            is_valid, missing_features = _validate_ml_features(analysis)
            
            if not is_valid:
                logger.warning(f"⚠️ ML schema validation failed: {', '.join(missing_features)}")
                logger.warning("ML disabled (schema mismatch)")
                return {
                    'ml_enabled': False,
                    'confidence_modifier': 0,
                    'ml_confidence': 0,
                    'schema_valid': False,
                    'schema_errors': missing_features
                }
            
            if self.model is None:
                return {
                    'ml_enabled': False,
                    'confidence_modifier': 0,
                    'ml_confidence': 0,
                    'schema_valid': True
                }
            
            # Schema valid - proceed with ML
            features = self._extract_features(analysis)
            if features is None:
                return {
                    'ml_enabled': False,
                    'confidence_modifier': 0,
                    'ml_confidence': 0,
                    'schema_valid': True,
                    'error': 'Feature extraction failed'
                }
            
            # Normalize features
            features_scaled = self.scaler.transform(features)
            
            # ML prediction
            ml_proba = self.model.predict_proba(features_scaled)[0]
            ml_confidence = max(ml_proba) * 100
            
            # Calculate confidence modifier
            # Positive modifier if ML confidence is high, negative if low
            base_confidence = 50
            confidence_modifier = (ml_confidence - base_confidence) / 100.0
            
            return {
                'ml_enabled': True,
                'confidence_modifier': confidence_modifier,
                'ml_confidence': ml_confidence,
                'schema_valid': True
            }
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return {
                'ml_enabled': False,
                'confidence_modifier': 0,
                'ml_confidence': 0,
                'schema_valid': True,
                'error': str(e)
            }
    
    def _extract_features(self, analysis):
        """
        Internal feature extraction method for get_ml_prediction.
        Extracts features matching the REQUIRED_ML_FEATURES schema.
        """
        try:
            # Extract numerical features
            features = [
                analysis.get('rsi', 50),
                analysis.get('confidence', 50),
                analysis.get('volume_ratio', 1),
                analysis.get('trend_strength', 0),
                analysis.get('volatility', 5),
            ]
            
            # Encode categorical features
            # timeframe: '1h'=1, '2h'=2, '4h'=4, '1d'=24
            timeframe_map = {'1h': 1, '2h': 2, '4h': 4, '1d': 24}
            timeframe_encoded = timeframe_map.get(analysis.get('timeframe', '4h'), 4)
            features.append(timeframe_encoded)
            
            # signal_type: 'BUY'=1, 'STRONG_BUY'=2, 'SELL'=-1, 'STRONG_SELL'=-2
            signal_map = {'BUY': 1, 'STRONG_BUY': 2, 'SELL': -1, 'STRONG_SELL': -2}
            signal_encoded = signal_map.get(analysis.get('signal_type', 'BUY'), 1)
            features.append(signal_encoded)
            
            return np.array(features).reshape(1, -1)
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None
    
    def extract_features(self, analysis):
        """Извлича features от анализа за ML (6 features - match bot.py)"""
        try:
            features = [
                analysis.get('rsi', 50),                    # 1
                analysis.get('price_change_pct', 0),        # 2
                analysis.get('volume_ratio', 1),            # 3
                analysis.get('volatility', 5),              # 4
                analysis.get('bb_position', 0.5),           # 5
                analysis.get('ict_confidence', 0.5),        # 6
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
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                journal = json.load(f)
            
            trades = journal.get('trades', [])
            
            if len(trades) < self.min_training_samples:
                print(f"⚠️ Not enough trades ({len(trades)} / {self.min_training_samples})")
                return False
            
            # Подготви features и labels
            X = []
            y = []
            
            valid_trades = 0
            invalid_trades = 0
            
            for trade in trades:
                # Пропусни trades без outcome
                if not trade.get('outcome'):
                    continue
                
                conditions = trade.get('conditions', {})
                
                # SANITY GATE: Validate training data schema
                is_valid, missing_features = _validate_ml_features(conditions)
                
                if not is_valid:
                    invalid_trades += 1
                    logger.debug(f"⚠️ Skipping trade (invalid schema): {', '.join(missing_features)}")
                    continue
                
                valid_trades += 1
                
                # Извлечи features (6 features - matching bot.py)
                features = [
                    conditions.get('rsi', 50),                    # 1
                    conditions.get('price_change_pct', 0),        # 2
                    conditions.get('volume_ratio', 1),            # 3
                    conditions.get('volatility', 5),              # 4
                    conditions.get('bb_position', 0.5),           # 5
                    conditions.get('ict_confidence', 0.5),        # 6
                ]
                
                X.append(features)
                
                # Label: WIN=1, LOSS=0
                outcome = trade.get('outcome')
                if outcome == 'WIN':
                    y.append(1)
                else:
                    y.append(0)
            
            if invalid_trades > 0:
                logger.warning(f"ML training: {invalid_trades} trades skipped due to schema mismatch")
            
            logger.info(f"ML training: {valid_trades} valid trades, {invalid_trades} skipped")
            
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
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    journal = json.load(f)
                num_samples = journal.get('metadata', {}).get('total_trades', 0)
            else:
                num_samples = 0
            
            return {
                'model_trained': self.model is not None,
                'ensemble_trained': self.ensemble_model is not None,
                'hybrid_mode': self.hybrid_mode,
                'ml_weight': self.ml_weight,
                'training_samples': num_samples,
                'min_samples_needed': self.min_training_samples,
                'ready_for_training': num_samples >= self.min_training_samples,
                'last_training': self.last_training_time,
                'use_ensemble': self.use_ensemble
            }
        except:
            return {'error': 'Failed to get status'}
    
    def extract_extended_features(self, analysis):
        """
        Extract extended features from analysis (15+ features)
        
        Features include:
        - Basic indicators (RSI, price change, volume)
        - Volatility metrics (ATR, BB position)
        - ICT confidence
        - Trend indicators (EMAs)
        - Market structure
        - Volume profile
        """
        try:
            features = [
                # Basic (6 features - original)
                analysis.get('rsi', 50),                    # 1
                analysis.get('price_change_pct', 0),        # 2
                analysis.get('volume_ratio', 1),            # 3
                analysis.get('volatility', 5),              # 4
                analysis.get('bb_position', 0.5),           # 5
                analysis.get('ict_confidence', 0.5),        # 6
                
                # Extended ICT features (9 features)
                analysis.get('whale_blocks_count', 0),      # 7
                analysis.get('liquidity_zones_count', 0),   # 8
                analysis.get('order_blocks_count', 0),      # 9
                analysis.get('fvgs_count', 0),              # 10
                analysis.get('displacement_detected', 0),   # 11
                analysis.get('structure_broken', 0),        # 12
                analysis.get('mtf_confluence', 0),          # 13
                analysis.get('bias_score', 0),              # 14
                analysis.get('strength_score', 0),          # 15
            ]
            return np.array(features).reshape(1, -1)
        except Exception as e:
            logger.error(f"Extended feature extraction error: {e}")
            # Fallback to basic features
            return self.extract_features(analysis)
    
    def train_ensemble_model(self):
        """
        Train ensemble model (Random Forest + Gradient Boosting)
        
        Uses voting/averaging between multiple models for better predictions
        """
        try:
            # Зареди trading journal
            if not os.path.exists(self.trading_journal_path):
                logger.warning("No trading journal available")
                return False
            
            with open(self.trading_journal_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                journal = json.load(f)
            
            trades = journal.get('trades', [])
            
            if len(trades) < 100:  # Require more data for ensemble
                logger.info(f"Not enough trades for ensemble ({len(trades)} / 100)")
                return False
            
            # Подготви features и labels
            X = []
            y = []
            
            for trade in trades:
                if not trade.get('outcome'):
                    continue
                
                conditions = trade.get('conditions', {})
                
                # Use extended features if available
                features = [
                    conditions.get('rsi', 50),
                    conditions.get('price_change_pct', 0),
                    conditions.get('volume_ratio', 1),
                    conditions.get('volatility', 5),
                    conditions.get('bb_position', 0.5),
                    conditions.get('ict_confidence', 0.5),
                    conditions.get('whale_blocks_count', 0),
                    conditions.get('liquidity_zones_count', 0),
                    conditions.get('order_blocks_count', 0),
                    conditions.get('fvgs_count', 0),
                    conditions.get('displacement_detected', 0),
                    conditions.get('structure_broken', 0),
                    conditions.get('mtf_confluence', 0),
                    conditions.get('bias_score', 0),
                    conditions.get('strength_score', 0),
                ]
                
                X.append(features)
                
                # Label
                outcome = trade.get('outcome')
                if outcome == 'WIN':
                    y.append(1)
                else:
                    y.append(0)
            
            if len(X) < 100:
                logger.warning(f"Not enough completed trades ({len(X)} / 100)")
                return False
            
            X = np.array(X)
            y = np.array(y)
            
            # Normalize
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            # Train Random Forest
            rf_model = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features='sqrt',
                random_state=42
            )
            rf_model.fit(X_train, y_train)
            
            # Train Gradient Boosting
            gb_model = GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=10,
                min_samples_split=5,
                random_state=42
            )
            gb_model.fit(X_train, y_train)
            
            # Store both models
            self.model = rf_model
            self.ensemble_model = gb_model
            self.use_ensemble = True
            
            # Save models
            joblib.dump(rf_model, self.model_path)
            joblib.dump(gb_model, self.ensemble_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            # Evaluate
            rf_accuracy = rf_model.score(X_test, y_test)
            gb_accuracy = gb_model.score(X_test, y_test)
            
            # Ensemble prediction (average)
            rf_pred = rf_model.predict(X_test)
            gb_pred = gb_model.predict(X_test)
            ensemble_pred = ((rf_pred + gb_pred) / 2).round()
            ensemble_accuracy = accuracy_score(y_test, ensemble_pred)
            
            logger.info(f"✅ Ensemble Model trained successfully!")
            logger.info(f"📊 Samples: {len(X)}")
            logger.info(f"🎯 RF accuracy: {rf_accuracy*100:.1f}%")
            logger.info(f"🎯 GB accuracy: {gb_accuracy*100:.1f}%")
            logger.info(f"🎯 Ensemble accuracy: {ensemble_accuracy*100:.1f}%")
            
            # Update performance history
            self.record_performance(ensemble_accuracy, len(X))
            
            # Feature importance
            self.calculate_feature_importance(rf_model, gb_model)
            
            return True
            
        except Exception as e:
            logger.error(f"Ensemble training error: {e}")
            return False
    
    def predict_with_ensemble(self, analysis, classical_signal, classical_confidence):
        """Predict using ensemble model"""
        if not self.use_ensemble or not self.ensemble_model:
            return self.predict_signal(analysis, classical_signal, classical_confidence)
        
        try:
            # Extract features
            features = self.extract_extended_features(analysis)
            if features is None:
                return classical_signal, classical_confidence, "Classical (Feature error)"
            
            # Normalize
            features_scaled = self.scaler.transform(features)
            
            # Predict with both models
            rf_pred = self.model.predict(features_scaled)[0]
            rf_proba = self.model.predict_proba(features_scaled)[0]
            
            gb_pred = self.ensemble_model.predict(features_scaled)[0]
            gb_proba = self.ensemble_model.predict_proba(features_scaled)[0]
            
            # Average predictions
            avg_proba = (rf_proba + gb_proba) / 2
            ensemble_pred = np.argmax(avg_proba)
            ensemble_confidence = max(avg_proba) * 100
            
            # Mapping
            signal_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
            ml_signal = signal_map.get(ensemble_pred, 'HOLD')
            
            # Hybrid mode
            if self.hybrid_mode:
                if ml_signal == classical_signal:
                    final_confidence = (classical_confidence * (1 - self.ml_weight) + 
                                      ensemble_confidence * self.ml_weight)
                    final_signal = classical_signal
                    mode = f"Hybrid Ensemble ({int((1-self.ml_weight)*100)}%/{int(self.ml_weight*100)}%) ✅"
                else:
                    if ensemble_confidence * self.ml_weight > classical_confidence * (1 - self.ml_weight):
                        final_signal = ml_signal
                        final_confidence = ensemble_confidence * 0.9
                        mode = f"Hybrid (Ensemble override) ⚠️"
                    else:
                        final_signal = classical_signal
                        final_confidence = classical_confidence * 0.85
                        mode = f"Hybrid (Classical override) ⚠️"
            else:
                final_signal = ml_signal
                final_confidence = ensemble_confidence
                mode = "Pure Ensemble ML 🤖"
            
            return final_signal, final_confidence, mode
            
        except Exception as e:
            logger.error(f"Ensemble prediction error: {e}")
            return classical_signal, classical_confidence, f"Classical (Ensemble error)"
    
    def backtest_model(self, test_size=0.2):
        """
        Backtest the ML model on historical data
        
        Returns performance metrics
        """
        try:
            if not os.path.exists(self.trading_journal_path):
                return {'error': 'No trading journal available'}
            
            with open(self.trading_journal_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                journal = json.load(f)
            
            trades = journal.get('trades', [])
            
            if len(trades) < self.min_training_samples:
                return {'error': 'Not enough trades for backtesting'}
            
            # Prepare data
            X = []
            y = []
            
            for trade in trades:
                if not trade.get('outcome'):
                    continue
                
                conditions = trade.get('conditions', {})
                features = [
                    conditions.get('rsi', 50),
                    conditions.get('price_change_pct', 0),
                    conditions.get('volume_ratio', 1),
                    conditions.get('volatility', 5),
                    conditions.get('bb_position', 0.5),
                    conditions.get('ict_confidence', 0.5),
                ]
                
                X.append(features)
                y.append(1 if trade.get('outcome') == 'WIN' else 0)
            
            X = np.array(X)
            y = np.array(y)
            
            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Normalize
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            
            # Predict
            y_pred = model.predict(X_test_scaled)
            
            # Metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            cm = confusion_matrix(y_test, y_pred)
            
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'confusion_matrix': cm.tolist(),
                'test_samples': len(y_test),
                'train_samples': len(y_train)
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {'error': str(e)}
    
    def calculate_feature_importance(self, rf_model, gb_model):
        """Calculate and store feature importance"""
        try:
            feature_names = [
                'rsi', 'price_change_pct', 'volume_ratio', 'volatility',
                'bb_position', 'ict_confidence', 'whale_blocks_count',
                'liquidity_zones_count', 'order_blocks_count', 'fvgs_count',
                'displacement_detected', 'structure_broken', 'mtf_confluence',
                'bias_score', 'strength_score'
            ]
            
            # Get importances from both models
            rf_importance = rf_model.feature_importances_
            gb_importance = gb_model.feature_importances_
            
            # Average
            avg_importance = (rf_importance + gb_importance) / 2
            
            # Create dict
            self.feature_importance = {
                name: float(importance) 
                for name, importance in zip(feature_names, avg_importance)
            }
            
            # Save
            with open(self.feature_importance_path, 'w') as f:
                json.dump(self.feature_importance, f, indent=2)
            
            # Log top features
            sorted_features = sorted(
                self.feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            logger.info("🎯 Top 5 Feature Importances:")
            for i, (name, importance) in enumerate(sorted_features[:5], 1):
                logger.info(f"   {i}. {name}: {importance:.3f}")
            
        except Exception as e:
            logger.error(f"Feature importance error: {e}")
    
    def get_feature_importance(self):
        """Get feature importance scores"""
        if not self.feature_importance:
            # Try to load
            if os.path.exists(self.feature_importance_path):
                with open(self.feature_importance_path, 'r') as f:
                    self.feature_importance = json.load(f)
        
        return self.feature_importance
    
    def record_performance(self, accuracy, num_samples):
        """Record training performance"""
        self.last_training_time = datetime.now()
        
        perf_record = {
            'timestamp': self.last_training_time.isoformat(),
            'accuracy': accuracy,
            'num_samples': num_samples,
            'ml_weight': self.ml_weight,
            'use_ensemble': self.use_ensemble
        }
        
        self.performance_history.append(perf_record)
        
        # Save
        with open(self.performance_path, 'w') as f:
            json.dump(self.performance_history, f, indent=2)
    
    def load_performance_history(self):
        """Load performance history"""
        try:
            if os.path.exists(self.performance_path):
                with open(self.performance_path, 'r') as f:
                    self.performance_history = json.load(f)
                
                if self.performance_history:
                    last_record = self.performance_history[-1]
                    self.last_training_time = datetime.fromisoformat(
                        last_record['timestamp']
                    )
        except Exception as e:
            logger.error(f"Load performance history error: {e}")
    
    def should_retrain(self):
        """Check if model should be retrained"""
        if not self.last_training_time:
            return True
        
        days_since_training = (datetime.now() - self.last_training_time).days
        
        return days_since_training >= self.retrain_interval_days
    
    def auto_retrain(self):
        """Automatically retrain if conditions are met"""
        if not self.should_retrain():
            logger.info("Model retraining not needed yet")
            return False
        
        logger.info("🔄 Auto-retraining ML model...")
        
        # Try ensemble first if enough data
        if self.train_ensemble_model():
            logger.info("✅ Ensemble model retrained")
            return True
        
        # Fallback to regular training
        if self.train_model():
            logger.info("✅ Regular model retrained")
            return True
        
        return False


# Global ML instance
ml_engine = MLTradingEngine()
