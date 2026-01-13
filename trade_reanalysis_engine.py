"""
🔄 TRADE RE-ANALYSIS ENGINE
Automated trade management with checkpoint monitoring and actionable recommendations

Features:
- Checkpoint calculation at 25%, 50%, 75%, 85% to TP1
- Full 12-step ICT re-analysis at each checkpoint
- Decision matrix for HOLD/PARTIAL_CLOSE/CLOSE_NOW/MOVE_SL
- HTF bias tracking and alerts
- Structure break detection
- Confidence delta monitoring
- Risk/reward ratio updates

Author: galinborisov10-art
Date: 2026-01-13
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import logging

# Import ICT Signal Engine for re-analysis
try:
    from ict_signal_engine import ICTSignalEngine, ICTSignal, SignalType, MarketBias
    ICT_ENGINE_AVAILABLE = True
except ImportError:
    ICT_ENGINE_AVAILABLE = False
    logging.warning("ICTSignalEngine not available for re-analysis")
    # Create placeholder types for when ICT engine is not available
    ICTSignalEngine = Any
    ICTSignal = Any
    SignalType = Any
    MarketBias = Any

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Trade recommendation types"""
    HOLD = "HOLD"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    CLOSE_NOW = "CLOSE_NOW"
    MOVE_SL = "MOVE_SL"


@dataclass
class CheckpointAnalysis:
    """
    Checkpoint re-analysis results
    
    Attributes:
        checkpoint_level: Checkpoint name (e.g., "25%", "50%")
        checkpoint_price: Price at checkpoint
        current_price: Current market price
        distance_to_tp: Distance to TP1 in %
        distance_to_sl: Distance to SL in %
        original_signal: Original trade signal
        current_signal: Re-analyzed signal (if available)
        original_confidence: Original confidence score
        current_confidence: Current confidence score
        confidence_delta: Change in confidence (current - original)
        htf_bias_changed: Whether HTF bias has changed
        structure_broken: Whether market structure was broken
        valid_components_count: Number of still-valid ICT components
        current_rr_ratio: Current risk/reward ratio
        recommendation: Recommended action
        reasoning: Human-readable explanation
        warnings: List of warnings
    """
    checkpoint_level: str
    checkpoint_price: float
    current_price: float
    distance_to_tp: float
    distance_to_sl: float
    
    original_signal: Optional[ICTSignal] = None
    current_signal: Optional[ICTSignal] = None
    
    original_confidence: float = 0.0
    current_confidence: float = 0.0
    confidence_delta: float = 0.0
    
    htf_bias_changed: bool = False
    structure_broken: bool = False
    valid_components_count: int = 0
    current_rr_ratio: float = 0.0
    
    recommendation: RecommendationType = RecommendationType.HOLD
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'checkpoint_level': self.checkpoint_level,
            'checkpoint_price': self.checkpoint_price,
            'current_price': self.current_price,
            'distance_to_tp': self.distance_to_tp,
            'distance_to_sl': self.distance_to_sl,
            'original_confidence': self.original_confidence,
            'current_confidence': self.current_confidence,
            'confidence_delta': self.confidence_delta,
            'htf_bias_changed': self.htf_bias_changed,
            'structure_broken': self.structure_broken,
            'valid_components_count': self.valid_components_count,
            'current_rr_ratio': self.current_rr_ratio,
            'recommendation': self.recommendation.value,
            'reasoning': self.reasoning,
            'warnings': self.warnings
        }


class TradeReanalysisEngine:
    """
    Trade Re-analysis Engine
    
    Monitors trades at key checkpoints and provides actionable recommendations
    based on re-analysis of ICT components and market conditions.
    """
    
    def __init__(self, ict_engine: Optional[ICTSignalEngine] = None):
        """
        Initialize Trade Re-analysis Engine
        
        Args:
            ict_engine: ICTSignalEngine instance for re-analysis (optional)
        """
        self.ict_engine = ict_engine
        self.checkpoint_levels = [0.25, 0.50, 0.75, 0.85]  # 25%, 50%, 75%, 85% to TP1
        
        logger.info("✅ TradeReanalysisEngine initialized")
        logger.info(f"   → Checkpoint levels: {[f'{int(x*100)}%' for x in self.checkpoint_levels]}")
        logger.info(f"   → ICT Engine available: {self.ict_engine is not None}")
    
    def calculate_checkpoint_prices(
        self,
        signal_type: str,
        entry_price: float,
        tp1_price: float,
        sl_price: float
    ) -> Dict[str, float]:
        """
        Calculate checkpoint prices at 25%, 50%, 75%, 85% progress to TP1
        
        Args:
            signal_type: "BUY" or "SELL"
            entry_price: Entry price
            tp1_price: Take Profit 1 price
            sl_price: Stop Loss price
        
        Returns:
            Dictionary with checkpoint levels and prices
            
        Example:
            BUY signal: Entry $45,000, TP1 $46,500
            - 25%: $45,375
            - 50%: $45,750
            - 75%: $46,125
            - 85%: $46,275
        """
        checkpoints = {}
        
        if signal_type.upper() == "BUY":
            # BUY: Move from entry UP to TP1
            distance = tp1_price - entry_price
            for level in self.checkpoint_levels:
                checkpoint_price = entry_price + (distance * level)
                checkpoints[f"{int(level * 100)}%"] = checkpoint_price
        else:  # SELL
            # SELL: Move from entry DOWN to TP1
            distance = entry_price - tp1_price
            for level in self.checkpoint_levels:
                checkpoint_price = entry_price - (distance * level)
                checkpoints[f"{int(level * 100)}%"] = checkpoint_price
        
        logger.info(f"📊 Calculated checkpoints for {signal_type} signal:")
        logger.info(f"   → Entry: ${entry_price:.2f}, TP1: ${tp1_price:.2f}, SL: ${sl_price:.2f}")
        for level, price in checkpoints.items():
            logger.info(f"   → {level}: ${price:.2f}")
        
        return checkpoints
    
    def reanalyze_at_checkpoint(
        self,
        symbol: str,
        timeframe: str,
        checkpoint_level: str,
        checkpoint_price: float,
        current_price: float,
        original_signal: ICTSignal,
        tp1_price: float,
        sl_price: float
    ) -> CheckpointAnalysis:
        """
        Perform full re-analysis at checkpoint
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            checkpoint_level: Checkpoint name (e.g., "25%", "50%")
            checkpoint_price: Price at checkpoint
            current_price: Current market price
            original_signal: Original trade signal
            tp1_price: Take Profit 1 price
            sl_price: Stop Loss price
        
        Returns:
            CheckpointAnalysis with recommendation
        """
        logger.info(f"🔄 Re-analyzing trade at {checkpoint_level} checkpoint")
        logger.info(f"   → Symbol: {symbol}, Timeframe: {timeframe}")
        logger.info(f"   → Checkpoint: ${checkpoint_price:.2f}, Current: ${current_price:.2f}")
        
        # Calculate distances
        signal_type = original_signal.signal_type.value
        if signal_type == "BUY" or signal_type == "STRONG_BUY":
            distance_to_tp = ((tp1_price - current_price) / current_price) * 100
            distance_to_sl = ((current_price - sl_price) / current_price) * 100
        else:  # SELL
            distance_to_tp = ((current_price - tp1_price) / current_price) * 100
            distance_to_sl = ((sl_price - current_price) / current_price) * 100
        
        # Initialize analysis
        analysis = CheckpointAnalysis(
            checkpoint_level=checkpoint_level,
            checkpoint_price=checkpoint_price,
            current_price=current_price,
            distance_to_tp=distance_to_tp,
            distance_to_sl=distance_to_sl,
            original_signal=original_signal,
            original_confidence=original_signal.confidence
        )
        
        # Perform re-analysis if ICT engine available
        if self.ict_engine:
            try:
                logger.info(f"   → Running full 12-step re-analysis...")
                current_signal = self.ict_engine.generate_signal(symbol, timeframe)
                analysis.current_signal = current_signal
                
                if current_signal and hasattr(current_signal, 'confidence'):
                    analysis.current_confidence = current_signal.confidence
                    analysis.confidence_delta = current_signal.confidence - original_signal.confidence
                    
                    # Check HTF bias change
                    original_htf = getattr(original_signal, 'htf_bias', 'UNKNOWN')
                    current_htf = getattr(current_signal, 'htf_bias', 'UNKNOWN')
                    analysis.htf_bias_changed = (original_htf != current_htf)
                    
                    # Check structure break (signal type flip)
                    original_type = original_signal.signal_type.value
                    current_type = current_signal.signal_type.value if hasattr(current_signal, 'signal_type') else 'UNKNOWN'
                    
                    # Structure broken if signal flipped (BUY -> SELL or vice versa)
                    if 'BUY' in original_type and 'SELL' in current_type:
                        analysis.structure_broken = True
                    elif 'SELL' in original_type and 'BUY' in current_type:
                        analysis.structure_broken = True
                    
                    # Count still-valid components
                    analysis.valid_components_count = self._count_valid_components(current_signal)
                    
                    # Calculate current R:R
                    if signal_type == "BUY" or signal_type == "STRONG_BUY":
                        risk = current_price - sl_price
                        reward = tp1_price - current_price
                    else:
                        risk = sl_price - current_price
                        reward = current_price - tp1_price
                    
                    if risk > 0:
                        analysis.current_rr_ratio = reward / risk
                    
                    logger.info(f"   ✅ Re-analysis complete:")
                    logger.info(f"      • Confidence: {original_signal.confidence:.1f}% → {current_signal.confidence:.1f}% (Δ{analysis.confidence_delta:+.1f}%)")
                    logger.info(f"      • HTF Bias: {original_htf} → {current_htf} (Changed: {analysis.htf_bias_changed})")
                    logger.info(f"      • Structure: Broken = {analysis.structure_broken}")
                    logger.info(f"      • Valid Components: {analysis.valid_components_count}")
                    logger.info(f"      • Current R:R: {analysis.current_rr_ratio:.2f}")
                    
            except Exception as e:
                logger.error(f"❌ Re-analysis failed: {e}")
                analysis.warnings.append(f"Re-analysis error: {str(e)}")
                # Continue with fallback recommendation
        else:
            logger.warning("⚠️ ICT engine not available - using basic analysis")
            analysis.warnings.append("Full re-analysis unavailable - ICT engine not initialized")
        
        # Determine recommendation based on analysis
        analysis.recommendation, analysis.reasoning = self._determine_recommendation(
            analysis, checkpoint_level
        )
        
        return analysis
    
    def _count_valid_components(self, signal: ICTSignal) -> int:
        """Count still-valid ICT components in signal"""
        count = 0
        
        if hasattr(signal, 'order_blocks') and signal.order_blocks:
            count += len(signal.order_blocks)
        
        if hasattr(signal, 'fair_value_gaps') and signal.fair_value_gaps:
            count += len(signal.fair_value_gaps)
        
        if hasattr(signal, 'whale_blocks') and signal.whale_blocks:
            count += len(signal.whale_blocks)
        
        if hasattr(signal, 'liquidity_zones') and signal.liquidity_zones:
            count += len(signal.liquidity_zones)
        
        return count
    
    def _determine_recommendation(
        self,
        analysis: CheckpointAnalysis,
        checkpoint: str
    ) -> Tuple[RecommendationType, str]:
        """
        Determine trade recommendation based on decision matrix
        
        Decision Matrix:
        1. HTF bias changed → CLOSE_NOW
        2. Structure broken → CLOSE_NOW
        3. Confidence delta < -30% → CLOSE_NOW
        4. Confidence delta < -15% AND checkpoint in [75%, 85%] → PARTIAL_CLOSE
        5. Confidence delta >= -5% AND checkpoint in [50%, 75%, 85%] → MOVE_SL
        6. Otherwise → HOLD
        
        Args:
            analysis: CheckpointAnalysis object
            checkpoint: Checkpoint level (e.g., "50%")
        
        Returns:
            Tuple of (RecommendationType, reasoning string)
        """
        # RULE 1: HTF bias changed
        if analysis.htf_bias_changed:
            return (
                RecommendationType.CLOSE_NOW,
                "HTF bias changed - trend reversal detected. Exit immediately."
            )
        
        # RULE 2: Structure broken
        if analysis.structure_broken:
            return (
                RecommendationType.CLOSE_NOW,
                "Market structure broken - signal invalidated. Exit immediately."
            )
        
        # RULE 3: Large confidence drop
        if analysis.confidence_delta < -30:
            return (
                RecommendationType.CLOSE_NOW,
                f"Confidence dropped {abs(analysis.confidence_delta):.1f}% - significant deterioration. Exit immediately."
            )
        
        # RULE 4: Moderate confidence drop near TP
        if analysis.confidence_delta < -15 and checkpoint in ["75%", "85%"]:
            return (
                RecommendationType.PARTIAL_CLOSE,
                f"Confidence dropped {abs(analysis.confidence_delta):.1f}% near TP1. Consider taking partial profits."
            )
        
        # RULE 5: Low R:R ratio near TP
        if analysis.current_rr_ratio < 0.5 and checkpoint in ["75%", "85%"]:
            return (
                RecommendationType.PARTIAL_CLOSE,
                f"R:R ratio now {analysis.current_rr_ratio:.2f} - risk outweighs remaining reward. Take profits."
            )
        
        # RULE 6: Confidence stable/improved - move SL
        if analysis.confidence_delta >= -5 and checkpoint in ["50%", "75%", "85%"]:
            return (
                RecommendationType.MOVE_SL,
                f"Confidence stable/improved ({analysis.confidence_delta:+.1f}%). Move SL to breakeven."
            )
        
        # DEFAULT: Hold position
        return (
            RecommendationType.HOLD,
            f"All conditions favorable. Confidence delta: {analysis.confidence_delta:+.1f}%. Continue holding."
        )
    
    def _create_close_recommendation(
        self,
        checkpoint_level: str,
        reason: str
    ) -> CheckpointAnalysis:
        """
        Create a fallback CLOSE_NOW recommendation when re-analysis fails
        
        Args:
            checkpoint_level: Checkpoint name
            reason: Reason for close recommendation
        
        Returns:
            CheckpointAnalysis with CLOSE_NOW recommendation
        """
        analysis = CheckpointAnalysis(
            checkpoint_level=checkpoint_level,
            checkpoint_price=0.0,
            current_price=0.0,
            distance_to_tp=0.0,
            distance_to_sl=0.0,
            recommendation=RecommendationType.CLOSE_NOW,
            reasoning=reason
        )
        
        return analysis
