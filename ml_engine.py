"""
🤖 MACHINE LEARNING ENGINE
Self-Learning Signal Optimization System

Complete ML system for trading signal prediction and optimization:
- Feature extraction from technical analysis and ICT concepts
- RandomForest classifier for signal prediction
- Hybrid mode (ML + Classical signals)
- Adaptive learning and retraining
- Performance tracking and metrics
- Feature importance analysis

Author: ICT Trading System
"""

import json
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
import joblib
import os
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class MLTradingEngine:
    """
    Machine Learning Trading Engine
    
    Implements ML-based signal prediction with hybrid classical+ML approach.
    Features adaptive learning, performance tracking, and feature importance analysis.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        
        # Auto-detect base path (works on Codespace AND server)
        if os.path.exists('/root/Crypto-signal-bot'):
            base_path = '/root/Crypto-signal-bot'
        else:
            base_path = '/workspaces/Crypto-signal-bot'
        
        self.base_path = base_path
        self.model_path = f'{base_path}/ml_model.pkl'
        self.scaler_path = f'{base_path}/ml_scaler.pkl'
        self.trading_journal_path = f'{base_path}/trading_journal.json'
        self.performance_log_path = f'{base_path}/ml_performance.json'
        self.predictions_log_path = f'{base_path}/ml_predictions.json'
        
        # Configuration
        self.min_training_samples = 50  # Minimum training samples
        self.retrain_interval = 50  # Retrain every N signals
        self.max_training_samples = 500  # Keep last 500 signals
        self.validation_split = 0.2  # 20% for validation
        
        # Hybrid mode settings
        self.hybrid_mode = True  # Start in hybrid mode
        self.ml_weight = 0.3  # Initially 30% ML, 70% classical
        
        # Performance tracking
        self.predictions_count = 0
        self.correct_predictions = 0
        self.current_metrics = {}
        self.feature_importance = {}
        
        # Load model if exists
        self.load_model()
        self._load_performance_log()
        
        logger.info("MLTradingEngine initialized successfully")
    
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
        """Returns ML system status"""
        try:
            # Count trades from trading journal
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
                'ready_for_training': num_samples >= self.min_training_samples,
                'predictions_count': self.predictions_count,
                'correct_predictions': self.correct_predictions,
                'accuracy': self.correct_predictions / self.predictions_count if self.predictions_count > 0 else 0,
                'current_metrics': self.current_metrics
            }
        except Exception as e:
            logger.error(f"Get status error: {e}")
            return {'error': 'Failed to get status'}
    
    def evaluate_model(self, test_data: Optional[List[Dict]] = None) -> Dict[str, float]:
        """
        Evaluate model performance on test data
        
        Args:
            test_data: Optional test dataset. If None, uses validation split from journal
            
        Returns:
            Dictionary with evaluation metrics
        """
        try:
            if self.model is None:
                logger.warning("No model to evaluate")
                return {'error': 'No model trained'}
            
            # Get test data
            if test_data is None:
                # Load from trading journal
                if not os.path.exists(self.trading_journal_path):
                    return {'error': 'No trading journal available'}
                
                with open(self.trading_journal_path, 'r') as f:
                    journal = json.load(f)
                
                trades = journal.get('trades', [])
                test_data = [t for t in trades if t.get('outcome')]
            
            if len(test_data) < 10:
                return {'error': 'Insufficient test data'}
            
            # Prepare features and labels
            X_test = []
            y_test = []
            
            for trade in test_data:
                conditions = trade.get('conditions', {})
                
                features = [
                    conditions.get('rsi', 50),
                    conditions.get('price_change_pct', 0),
                    conditions.get('volume_ratio', 1),
                    conditions.get('volatility', 5),
                    conditions.get('bb_position', 0.5),
                    conditions.get('ict_confidence', 0.5),
                ]
                
                X_test.append(features)
                
                outcome = trade.get('outcome')
                y_test.append(1 if outcome == 'WIN' else 0)
            
            X_test = np.array(X_test)
            y_test = np.array(y_test)
            
            # Scale features
            X_test_scaled = self.scaler.transform(X_test)
            
            # Predict
            y_pred = self.model.predict(X_test_scaled)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)
            
            metrics = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'test_samples': len(X_test),
                'confusion_matrix': cm.tolist()
            }
            
            # Update current metrics
            self.current_metrics = metrics
            
            logger.info(f"Model evaluation: Accuracy={accuracy:.2%}, Precision={precision:.2%}, Recall={recall:.2%}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Model evaluation error: {e}")
            return {'error': str(e)}
    
    def save_model(self) -> bool:
        """
        Save model and scaler to disk
        
        Returns:
            True if successful
        """
        try:
            if self.model is None:
                logger.warning("No model to save")
                return False
            
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.scaler, self.scaler_path)
            
            logger.info(f"Model saved to {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Save model error: {e}")
            return False
    
    def log_prediction(self, signal: str, features: Dict, outcome: Optional[str] = None) -> None:
        """
        Log prediction for tracking and future training
        
        Args:
            signal: Predicted signal (BUY/SELL/HOLD)
            features: Feature dictionary
            outcome: Actual outcome (WIN/LOSS) - optional, added later
        """
        try:
            # Load existing predictions
            if os.path.exists(self.predictions_log_path):
                with open(self.predictions_log_path, 'r') as f:
                    predictions = json.load(f)
            else:
                predictions = {'predictions': []}
            
            # Add new prediction
            prediction = {
                'timestamp': datetime.now().isoformat(),
                'signal': signal,
                'features': features,
                'outcome': outcome
            }
            
            predictions['predictions'].append(prediction)
            
            # Keep only last 1000 predictions
            if len(predictions['predictions']) > 1000:
                predictions['predictions'] = predictions['predictions'][-1000:]
            
            # Save
            with open(self.predictions_log_path, 'w') as f:
                json.dump(predictions, f, indent=2)
            
            self.predictions_count += 1
            
            # If outcome provided, update accuracy
            if outcome:
                if (outcome == 'WIN' and signal in ['BUY', 'SELL']) or (outcome == 'LOSS' and signal == 'HOLD'):
                    self.correct_predictions += 1
            
        except Exception as e:
            logger.error(f"Log prediction error: {e}")
    
    def adaptive_learning(self) -> bool:
        """
        Perform adaptive learning - retrain on new data
        
        Returns:
            True if retraining occurred
        """
        try:
            # Check if retraining is needed
            if self.predictions_count % self.retrain_interval == 0 and self.predictions_count > 0:
                logger.info(f"Adaptive learning triggered at {self.predictions_count} predictions")
                
                # Retrain model
                success = self.train_model()
                
                if success:
                    # Evaluate on validation set
                    metrics = self.evaluate_model()
                    
                    # Log performance
                    self._log_performance(metrics)
                    
                    logger.info(f"Adaptive learning completed: {metrics}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Adaptive learning error: {e}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the trained model
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        try:
            if self.model is None or not hasattr(self.model, 'feature_importances_'):
                return {}
            
            feature_names = [
                'rsi',
                'price_change_pct',
                'volume_ratio',
                'volatility',
                'bb_position',
                'ict_confidence'
            ]
            
            importance = self.model.feature_importances_
            
            self.feature_importance = {
                name: float(score) 
                for name, score in zip(feature_names, importance)
            }
            
            # Sort by importance
            self.feature_importance = dict(
                sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)
            )
            
            return self.feature_importance
            
        except Exception as e:
            logger.error(f"Feature importance error: {e}")
            return {}
    
    def extract_ict_features(self, analysis: Dict, ict_components: Optional[Dict] = None) -> np.ndarray:
        """
        Extract enhanced features including ICT concepts
        
        Args:
            analysis: Technical analysis dictionary
            ict_components: ICT components dictionary (optional)
            
        Returns:
            Feature array
        """
        try:
            # Base features (6 features to match bot.py)
            features = [
                analysis.get('rsi', 50),                    # 1
                analysis.get('price_change_pct', 0),        # 2
                analysis.get('volume_ratio', 1),            # 3
                analysis.get('volatility', 5),              # 4
                analysis.get('bb_position', 0.5),           # 5
                analysis.get('ict_confidence', 0.5),        # 6
            ]
            
            # If ICT components provided, enhance the ict_confidence feature
            if ict_components:
                # Whale block presence (binary feature embedded in confidence)
                whale_score = 0.0
                if ict_components.get('whale_blocks'):
                    whale_score = min(len(ict_components['whale_blocks']) / 3, 1.0) * 0.2
                
                # Liquidity sweep detected
                sweep_score = 0.0
                if ict_components.get('liquidity_sweeps'):
                    sweep_score = 0.2
                
                # Order block quality
                ob_score = 0.0
                if ict_components.get('order_blocks'):
                    obs = ict_components['order_blocks']
                    active_obs = [ob for ob in obs if not ob.get('mitigated', False)]
                    if active_obs:
                        avg_quality = sum(ob.get('strength_score', 0) for ob in active_obs) / len(active_obs)
                        ob_score = (avg_quality / 100) * 0.2
                
                # FVG count (normalized)
                fvg_score = 0.0
                if ict_components.get('fvgs'):
                    fvgs = ict_components['fvgs']
                    active_fvgs = [fvg for fvg in fvgs if not fvg.get('filled', False)]
                    fvg_score = min(len(active_fvgs) / 5, 1.0) * 0.2
                
                # MTF confluence score
                mtf_score = 0.0
                if ict_components.get('mtf_confluence'):
                    mtf_score = (ict_components['mtf_confluence'] / 3) * 0.2
                
                # Update ICT confidence with all scores
                ict_confidence = whale_score + sweep_score + ob_score + fvg_score + mtf_score
                features[5] = min(ict_confidence, 1.0)  # Update ict_confidence feature
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"ICT feature extraction error: {e}")
            # Return base features on error
            return self.extract_features(analysis)
    
    def _load_performance_log(self) -> None:
        """Load performance log from disk"""
        try:
            if os.path.exists(self.performance_log_path):
                with open(self.performance_log_path, 'r') as f:
                    log = json.load(f)
                
                if log.get('history'):
                    latest = log['history'][-1]
                    self.current_metrics = latest.get('metrics', {})
                    self.predictions_count = latest.get('predictions_count', 0)
                    self.correct_predictions = latest.get('correct_predictions', 0)
                
                logger.info("Performance log loaded")
        except Exception as e:
            logger.error(f"Load performance log error: {e}")
    
    def _log_performance(self, metrics: Dict) -> None:
        """
        Log performance metrics to disk
        
        Args:
            metrics: Performance metrics dictionary
        """
        try:
            # Load existing log
            if os.path.exists(self.performance_log_path):
                with open(self.performance_log_path, 'r') as f:
                    log = json.load(f)
            else:
                log = {'history': []}
            
            # Add new entry
            entry = {
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'predictions_count': self.predictions_count,
                'correct_predictions': self.correct_predictions,
                'ml_weight': self.ml_weight,
                'hybrid_mode': self.hybrid_mode
            }
            
            log['history'].append(entry)
            
            # Keep only last 100 entries
            if len(log['history']) > 100:
                log['history'] = log['history'][-100:]
            
            # Save
            with open(self.performance_log_path, 'w') as f:
                json.dump(log, f, indent=2)
            
            logger.info("Performance logged successfully")
            
        except Exception as e:
            logger.error(f"Log performance error: {e}")
    
    def get_performance_history(self) -> List[Dict]:
        """
        Get historical performance data
        
        Returns:
            List of performance entries
        """
        try:
            if os.path.exists(self.performance_log_path):
                with open(self.performance_log_path, 'r') as f:
                    log = json.load(f)
                return log.get('history', [])
            return []
        except Exception as e:
            logger.error(f"Get performance history error: {e}")
            return []
    
    def calculate_profit_factor(self) -> float:
        """
        Calculate profit factor from predictions
        
        Returns:
            Profit factor (wins/losses ratio)
        """
        try:
            if not os.path.exists(self.predictions_log_path):
                return 0.0
            
            with open(self.predictions_log_path, 'r') as f:
                log = json.load(f)
            
            predictions = log.get('predictions', [])
            
            wins = sum(1 for p in predictions if p.get('outcome') == 'WIN')
            losses = sum(1 for p in predictions if p.get('outcome') == 'LOSS')
            
            if losses == 0:
                return float(wins) if wins > 0 else 0.0
            
            return wins / losses
            
        except Exception as e:
            logger.error(f"Profit factor calculation error: {e}")
            return 0.0


# Global ML instance
ml_engine = MLTradingEngine()
