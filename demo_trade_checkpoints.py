"""
Demo: Trade Re-analysis with Checkpoint Monitoring

Demonstrates:
1. Checkpoint price calculation
2. Example trade scenarios
3. Recommendation logic
4. Benefits summary
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from trade_reanalysis_engine import (
    TradeReanalysisEngine,
    RecommendationType,
    CheckpointAnalysis
)
from ict_signal_engine import ICTSignal, SignalType, SignalStrength, MarketBias


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_scenario(number: int, title: str, description: str):
    """Print scenario header"""
    print(f"\n📊 SCENARIO {number}: {title}")
    print(f"   {description}\n")


def demo_checkpoint_calculation():
    """Demo 1: Show checkpoint calculation"""
    print_header("DEMO 1: Checkpoint Calculation")
    
    engine = TradeReanalysisEngine()
    
    print("📈 Example Trade Setup:")
    print("   Symbol: BTCUSDT")
    print("   Signal: BUY")
    print("   Entry: $45,000")
    print("   TP1: $46,500 (3.3% gain)")
    print("   TP2: $47,500 (5.5% gain)")
    print("   TP3: $49,000 (8.9% gain)")
    print("   SL: $44,500 (-1.1% loss)")
    print()
    
    checkpoints = engine.calculate_checkpoint_prices(
        signal_type="BUY",
        entry_price=45000,
        tp1_price=46500,
        sl_price=44500
    )
    
    print("🎯 Checkpoint Monitoring Points:")
    for level, price in checkpoints.items():
        distance = ((price - 45000) / 45000) * 100
        print(f"   ✓ {level:>3}: ${price:,.2f} (+{distance:.2f}% from entry)")


def demo_scenarios():
    """Demo 2: Show different checkpoint scenarios"""
    print_header("DEMO 2: Checkpoint Analysis Scenarios")
    
    engine = TradeReanalysisEngine()
    
    # Create mock original signal
    original_signal = ICTSignal(
        timestamp=datetime.now(timezone.utc),
        symbol="BTCUSDT",
        timeframe="1h",
        signal_type=SignalType.BUY,
        signal_strength=SignalStrength.STRONG,
        entry_price=45000,
        sl_price=44500,
        tp_prices=[46500, 47500, 49000],
        confidence=75.0,
        risk_reward_ratio=3.0,
        bias=MarketBias.BULLISH,
        htf_bias="BULLISH"
    )
    
    # Scenario 1: 25% checkpoint, minor drop → HOLD
    print_scenario(
        1,
        "Early Checkpoint - Minor Confidence Drop",
        "Price at 25% checkpoint, confidence dropped slightly"
    )
    
    analysis1 = CheckpointAnalysis(
        checkpoint_level="25%",
        checkpoint_price=45375,
        current_price=45400,
        distance_to_tp=2.4,
        distance_to_sl=2.0,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=70.0,
        confidence_delta=-5.0,
        htf_bias_changed=False,
        structure_broken=False,
        valid_components_count=8,
        current_rr_ratio=2.2
    )
    
    rec1, reason1 = engine._determine_recommendation(analysis1, "25%")
    
    print(f"   Current Price: ${analysis1.current_price:,.2f}")
    print(f"   Confidence: {analysis1.original_confidence:.1f}% → {analysis1.current_confidence:.1f}% (Δ{analysis1.confidence_delta:+.1f}%)")
    print(f"   HTF Bias: Unchanged (BULLISH)")
    print(f"   Structure: Intact")
    print(f"   Valid Components: {analysis1.valid_components_count}")
    print(f"   Current R:R: {analysis1.current_rr_ratio:.2f}")
    print(f"\n   🎯 RECOMMENDATION: {rec1.value}")
    print(f"   💡 Reason: {reason1}")
    
    # Scenario 2: 50% checkpoint, confidence improved → MOVE_SL
    print_scenario(
        2,
        "Midpoint Checkpoint - Improved Confidence",
        "Price at 50% checkpoint, confidence increased"
    )
    
    analysis2 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=85.0,
        confidence_delta=+10.0,
        htf_bias_changed=False,
        structure_broken=False,
        valid_components_count=10,
        current_rr_ratio=1.8
    )
    
    rec2, reason2 = engine._determine_recommendation(analysis2, "50%")
    
    print(f"   Current Price: ${analysis2.current_price:,.2f}")
    print(f"   Confidence: {analysis2.original_confidence:.1f}% → {analysis2.current_confidence:.1f}% (Δ{analysis2.confidence_delta:+.1f}%)")
    print(f"   HTF Bias: Unchanged (BULLISH)")
    print(f"   Structure: Intact")
    print(f"   Valid Components: {analysis2.valid_components_count}")
    print(f"   Current R:R: {analysis2.current_rr_ratio:.2f}")
    print(f"\n   🎯 RECOMMENDATION: {rec2.value}")
    print(f"   💡 Reason: {reason2}")
    
    # Scenario 3: 75% checkpoint, moderate drop → PARTIAL_CLOSE
    print_scenario(
        3,
        "Pre-TP Checkpoint - Moderate Confidence Drop",
        "Price at 75% checkpoint, confidence dropped moderately"
    )
    
    analysis3 = CheckpointAnalysis(
        checkpoint_level="75%",
        checkpoint_price=46125,
        current_price=46150,
        distance_to_tp=0.75,
        distance_to_sl=3.7,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=55.0,
        confidence_delta=-20.0,
        htf_bias_changed=False,
        structure_broken=False,
        valid_components_count=6,
        current_rr_ratio=0.9
    )
    
    rec3, reason3 = engine._determine_recommendation(analysis3, "75%")
    
    print(f"   Current Price: ${analysis3.current_price:,.2f}")
    print(f"   Confidence: {analysis3.original_confidence:.1f}% → {analysis3.current_confidence:.1f}% (Δ{analysis3.confidence_delta:+.1f}%)")
    print(f"   HTF Bias: Unchanged (BULLISH)")
    print(f"   Structure: Intact")
    print(f"   Valid Components: {analysis3.valid_components_count}")
    print(f"   Current R:R: {analysis3.current_rr_ratio:.2f}")
    print(f"\n   🎯 RECOMMENDATION: {rec3.value}")
    print(f"   💡 Reason: {reason3}")
    
    # Scenario 4: 50% checkpoint, HTF bias changed → CLOSE_NOW
    print_scenario(
        4,
        "Midpoint Checkpoint - HTF Bias Changed",
        "Price at 50% checkpoint, HTF bias reversed"
    )
    
    analysis4 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=70.0,
        confidence_delta=-5.0,
        htf_bias_changed=True,
        structure_broken=False,
        valid_components_count=8,
        current_rr_ratio=1.5
    )
    
    rec4, reason4 = engine._determine_recommendation(analysis4, "50%")
    
    print(f"   Current Price: ${analysis4.current_price:,.2f}")
    print(f"   Confidence: {analysis4.original_confidence:.1f}% → {analysis4.current_confidence:.1f}% (Δ{analysis4.confidence_delta:+.1f}%)")
    print(f"   HTF Bias: BULLISH → BEARISH ⚠️")
    print(f"   Structure: Intact")
    print(f"   Valid Components: {analysis4.valid_components_count}")
    print(f"   Current R:R: {analysis4.current_rr_ratio:.2f}")
    print(f"\n   🎯 RECOMMENDATION: {rec4.value}")
    print(f"   💡 Reason: {reason4}")


def demo_benefits():
    """Demo 3: Show benefits summary"""
    print_header("DEMO 3: Benefits Summary")
    
    benefits = [
        ("✅ Automated Monitoring", "4 checkpoints (25%, 50%, 75%, 85%) automatically tracked"),
        ("✅ Professional Trade Management", "ICT-compliant re-analysis at each checkpoint"),
        ("✅ Risk Management", "Automated alerts when conditions deteriorate"),
        ("✅ Actionable Recommendations", "Clear HOLD/PARTIAL_CLOSE/CLOSE_NOW/MOVE_SL signals"),
        ("✅ HTF Bias Tracking", "Detects trend reversals automatically"),
        ("✅ Structure Monitoring", "Alerts if market structure breaks"),
        ("✅ Confidence Tracking", "Monitors signal confidence changes"),
        ("✅ Educational Value", "Teaches when to hold vs exit based on ICT principles"),
        ("✅ Complete Trade Lifecycle", "From entry → monitoring → exit"),
        ("✅ Foundation for Future", "Enables auto-close, trailing SL, position sizing")
    ]
    
    for title, description in benefits:
        print(f"{title}")
        print(f"   {description}\n")
    
    print("\n📊 Before vs After PR #5:\n")
    
    comparison = [
        ("Trade Monitoring", "Manual", "Automated (4 checkpoints)", "100% automation"),
        ("Re-analysis", "None", "Full 12-step at each checkpoint", "New feature"),
        ("Recommendations", "None", "HOLD/CLOSE/PARTIAL/MOVE_SL", "Actionable"),
        ("HTF Tracking", "Manual", "Automated alerts", "Automated"),
        ("Risk Management", "Manual", "Rule-based recommendations", "Professional"),
        ("Trade Lifecycle", "Entry only", "Entry → Monitor → Exit", "Complete")
    ]
    
    print(f"{'Aspect':<20} {'Before':<20} {'After':<30} {'Change'}")
    print("-" * 90)
    
    for aspect, before, after, change in comparison:
        print(f"{aspect:<20} {before:<20} {after:<30} {change}")


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("  TRADE RE-ANALYSIS ENGINE - DEMO")
    print("  Checkpoint Monitoring & Automated Trade Management")
    print("=" * 70)
    
    demo_checkpoint_calculation()
    demo_scenarios()
    demo_benefits()
    
    print("\n" + "=" * 70)
    print("  Demo complete! Ready for production use.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
