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
            'rsi',                      # Keep - RSI indicator
            'market_structure_score',   # NEW - Pure ICT: Market structure (HH/HL vs LH/LL)
            'order_block_strength',     # NEW - Pure ICT: Order block count and quality
            'displacement_score',       # NEW - Pure ICT: Price displacement strength
            'fvg_quality',             # NEW - Pure ICT: Fair Value Gap quality
            'liquidity_grab_score',    # NEW - Pure ICT: Liquidity sweep strength
            'volume_ratio',            # Keep - Volume analysis
            'volatility',              # Keep - Price volatility
            'confidence',              # Keep - ICT confidence score
            'btc_correlation',         # Keep - BTC correlation
            'sentiment_score',         # Keep - Market sentiment
            'mtf_alignment',           # NEW - Pure ICT: Multi-timeframe confluence
            'risk_reward_ratio'        # NEW - Pure ICT: Risk/reward from signal
        ]
        self.is_trained = False
        
        # Зареди модел ако съществува
        if os.path.exists(model_path):
            try:
                loaded_model = joblib.load(model_path)
                
                # Validate model compatibility (feature count)
                if hasattr(loaded_model, 'n_features_in_'):
                    expected_features = loaded_model.n_features_in_
                    current_features = len(self.feature_names)
                    
                    if expected_features != current_features:
                        logger.warning("=" * 60)
                        logger.warning(f"⚠️ ML MODEL INCOMPATIBILITY DETECTED")
                        logger.warning(f"⚠️ Model expects: {expected_features} features")
                        logger.warning(f"⚠️ Current code has: {current_features} features")
                        logger.warning(f"⚠️ ML Predictor will be DISABLED")
                        logger.warning(f"⚠️ Action: Delete {model_path} and retrain after 50+ trades")
                        logger.warning("=" * 60)
                        self.model = None
                        self.is_trained = False
                    else:
                        self.model = loaded_model
                        self.is_trained = True
                        logger.info(f"✅ ML модел зареден от {model_path} ({expected_features} features)")
                else:
                    # Old sklearn version or unsupported model type
                    logger.warning(f"⚠️ Cannot verify feature count for model {model_path}")
                    logger.warning(f"⚠️ Loading anyway, but may cause errors if incompatible")
                    self.model = loaded_model
                    self.is_trained = True
                    
            except Exception as e:
                logger.error(f"❌ Грешка при зареждане на ML модел: {e}")
                self.model = None
                self.is_trained = False
    
    def extract_features(self, trade_data: Dict) -> Optional[List[float]]:
        """
        ✅ UPDATED: Extract Pure ICT features (NO MA/EMA!)
        
        Args:
            trade_data: Dictionary with ICT signal data
            
        Returns:
            List of 13 features or None if data is incomplete
            
        Features:
        1. RSI (0-100)
        2. Market Structure Score (0-100) - Pure ICT
        3. Order Block Strength (0-100) - Pure ICT
        4. Displacement Score (0-100) - Pure ICT
        5. FVG Quality (0-100) - Pure ICT
        6. Liquidity Grab Score (0-100) - Pure ICT
        7. Volume Ratio (0-5+)
        8. Volatility (0-10+)
        9. Confidence (0-100)
        10. BTC Correlation (-1 to 1, normalized to 0-100)
        11. Sentiment Score (0-100)
        12. MTF Alignment (0-100)
        13. Risk/Reward Ratio (0-10+)
        """
        try:
            # Try to get ICT components (new format)
            ict_components = trade_data.get('ict_components', {})
            analysis = trade_data.get('analysis_data', {})
            
            # === FEATURE 1: RSI (KEEP AS IS) ===
            rsi = analysis.get('rsi') or trade_data.get('rsi', 50.0)
            if rsi is None or rsi < 0 or rsi > 100:
                rsi = 50.0
            
            # === FEATURE 2: MARKET STRUCTURE SCORE (NEW - Pure ICT) ===
            market_structure = ict_components.get('market_structure', {})
            if isinstance(market_structure, dict):
                # Try to calculate from structure data
                structure_breaks = market_structure.get('structure_breaks', [])
                bos_count = market_structure.get('bos_count', 0)
                choch_count = market_structure.get('choch_count', 0)
                
                # Score based on structure strength
                structure_score = min(100, (bos_count * 20) + (choch_count * 15) + (len(structure_breaks) * 10))
            else:
                structure_score = 50.0  # Neutral default
            
            # === FEATURE 3: ORDER BLOCK STRENGTH (NEW - Pure ICT) ===
            order_blocks = ict_components.get('order_blocks', [])
            if order_blocks and isinstance(order_blocks, list):
                # Calculate strength from order block count and properties
                ob_count = len(order_blocks)
                ob_strength = min(100, ob_count * 20)  # Max 5 OBs = 100%
                
                # Boost if OBs have high strength property
                try:
                    avg_ob_quality = sum(ob.get('strength', 50) for ob in order_blocks if isinstance(ob, dict)) / max(1, ob_count)
                    ob_strength = (ob_strength + avg_ob_quality) / 2
                except:
                    pass
            else:
                ob_strength = 50.0  # Neutral default
            
            # === FEATURE 4: DISPLACEMENT SCORE (NEW - Pure ICT) ===
            displacement = ict_components.get('displacement', {})
            if isinstance(displacement, dict):
                disp_detected = displacement.get('detected', False)
                disp_strength = displacement.get('strength', 50.0)
                disp_score = disp_strength if disp_detected else 50.0
            else:
                disp_score = 50.0  # Neutral default
            
            # === FEATURE 5: FVG QUALITY (NEW - Pure ICT) ===
            fvgs = ict_components.get('fvgs', []) or ict_components.get('fair_value_gaps', [])
            if fvgs and isinstance(fvgs, list):
                fvg_count = len(fvgs)
                fvg_quality = min(100, fvg_count * 25)  # Max 4 FVGs = 100%
                
                # Boost if FVGs have size property
                try:
                    avg_fvg_size = sum(fvg.get('size_percent', 1.0) for fvg in fvgs if isinstance(fvg, dict)) / max(1, fvg_count)
                    fvg_quality = min(100, fvg_quality + (avg_fvg_size * 10))
                except:
                    pass
            else:
                fvg_quality = 50.0  # Neutral default
            
            # === FEATURE 6: LIQUIDITY GRAB SCORE (NEW - Pure ICT) ===
            liquidity_zones = ict_components.get('liquidity_zones', [])
            if liquidity_zones and isinstance(liquidity_zones, list):
                liq_count = len(liquidity_zones)
                liq_score = min(100, liq_count * 15)  # Max 6-7 zones = 100%
            else:
                liq_score = 50.0  # Neutral default
            
            # === FEATURE 7: VOLUME RATIO (KEEP AS IS) ===
            volume_ratio = analysis.get('volume_ratio') or trade_data.get('volume_ratio', 1.0)
            if volume_ratio is None or volume_ratio < 0:
                volume_ratio = 1.0
            
            # === FEATURE 8: VOLATILITY (KEEP AS IS) ===
            volatility = analysis.get('volatility') or trade_data.get('volatility', 1.0)
            if volatility is None or volatility < 0:
                volatility = 1.0
            
            # === FEATURE 9: CONFIDENCE (KEEP AS IS) ===
            confidence = trade_data.get('confidence', 50.0)
            if confidence is None or confidence < 0 or confidence > 100:
                confidence = 50.0
            
            # === FEATURE 10: BTC CORRELATION (KEEP AS IS) ===
            btc_correlation = analysis.get('btc_correlation') or trade_data.get('btc_correlation', 0.0)
            if btc_correlation is None:
                btc_correlation = 0.0
            # Normalize to 0-100 scale: -1 to 1 → 0 to 100
            btc_correlation_normalized = (btc_correlation + 1) * 50
            
            # === FEATURE 11: SENTIMENT SCORE (KEEP AS IS) ===
            sentiment_score = analysis.get('sentiment_score') or trade_data.get('sentiment_score', 50.0)
            if sentiment_score is None or sentiment_score < 0 or sentiment_score > 100:
                sentiment_score = 50.0
            
            # === FEATURE 12: MTF ALIGNMENT (NEW - Pure ICT) ===
            mtf_confluence = trade_data.get('mtf_confluence', 0.5)
            if mtf_confluence is None:
                mtf_confluence = 0.5
            mtf_alignment = mtf_confluence * 100  # Convert 0-1 to 0-100
            
            # === FEATURE 13: RISK/REWARD RATIO (NEW - Pure ICT) ===
            risk_reward_ratio = trade_data.get('risk_reward_ratio', 2.0)
            if risk_reward_ratio is None or risk_reward_ratio < 0:
                risk_reward_ratio = 2.0
            
            # ✅ RETURN FEATURE VECTOR (13 features)
            features = [
                float(rsi),
                float(structure_score),
                float(ob_strength),
                float(disp_score),
                float(fvg_quality),
                float(liq_score),
                float(volume_ratio),
                float(volatility),
                float(confidence),
                float(btc_correlation_normalized),
                float(sentiment_score),
                float(mtf_alignment),
                float(risk_reward_ratio)
            ]
            
            # Validate all features are valid numbers
            if any(not isinstance(f, (int, float)) or np.isnan(f) or np.isinf(f) for f in features):
                logger.warning("Invalid feature values detected, using defaults")
                return None
            
            return features
            
        except Exception as e:
            logger.error(f"❌ Feature extraction error: {e}")
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
        
        # Validate feature consistency
        logger.info(f"📊 Extracted features from {len(X)} trades")
        logger.info(f"📊 Feature dimensions: {len(self.feature_names)} features per trade")
        if len(X) > 0:
            logger.info(f"📊 First trade features: {self.feature_names}")
            logger.info(f"📊 Sample values: {X[0]}")
        
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
