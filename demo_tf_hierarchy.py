"""
Demo: Show how TF hierarchy appears in signal messages

This demonstrates the PR #4 feature - Timeframe Hierarchy
"""

from ict_signal_engine import ICTSignal, SignalType, SignalStrength, MarketBias
from datetime import datetime

def create_demo_signal_with_hierarchy(entry_tf='1h', all_tfs_present=True):
    """Create a demo signal with TF hierarchy info"""
    
    # Create hierarchy info based on entry TF
    hierarchy_configs = {
        '1h': {
            'entry_tf': '1h',
            'confirmation_tf': '2h',
            'structure_tf': '4h',
            'htf_bias_tf': '1d',
            'description': '1H entries with 2H confirmation and 4H structure'
        },
        '2h': {
            'entry_tf': '2h',
            'confirmation_tf': '4h',
            'structure_tf': '1d',
            'htf_bias_tf': '1d',
            'description': '2H entries with 4H confirmation and 1D structure'
        }
    }
    
    hierarchy_info = hierarchy_configs.get(entry_tf, hierarchy_configs['1h'])
    
    if all_tfs_present:
        hierarchy_info['confirmation_tf_present'] = True
        hierarchy_info['structure_tf_present'] = True
        hierarchy_info['htf_bias_tf_present'] = True
        hierarchy_info['structure_bias'] = 'BULLISH'
    else:
        hierarchy_info['confirmation_tf_present'] = False
        hierarchy_info['structure_tf_present'] = True
        hierarchy_info['htf_bias_tf_present'] = True
        hierarchy_info['structure_bias'] = 'BULLISH'
    
    # Create demo signal
    signal = ICTSignal(
        timestamp=datetime.now(),
        symbol='BTCUSDT',
        timeframe=entry_tf,
        signal_type=SignalType.BUY,
        signal_strength=SignalStrength.STRONG,
        entry_price=45000.0,
        sl_price=44500.0,
        tp_prices=[46500.0, 47500.0, 49000.0],
        confidence=75.0 if all_tfs_present else 60.0,
        risk_reward_ratio=3.0,
        bias=MarketBias.BULLISH,
        timeframe_hierarchy=hierarchy_info
    )
    
    return signal


def format_tf_hierarchy_section(signal):
    """Extract and format TF hierarchy section from signal"""
    
    if not hasattr(signal, 'timeframe_hierarchy') or not signal.timeframe_hierarchy:
        return "⚠️ No TF hierarchy info available"
    
    hierarchy = signal.timeframe_hierarchy
    
    # Build TF status indicators
    structure_status = "✅" if hierarchy.get('structure_tf_present') else "⚠️"
    confirmation_status = "✅" if hierarchy.get('confirmation_tf_present') else "⚠️"
    htf_bias_status = "✅" if hierarchy.get('htf_bias_tf_present') else "ℹ️"
    
    section = f"""
━━━━━━━━━━━━━━━━━━━━━━
📊 TIMEFRAME ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━

ICT Hierarchy: {hierarchy.get('description', 'N/A')}

• Entry TF: {hierarchy.get('entry_tf', 'N/A')}
• Confirmation TF: {hierarchy.get('confirmation_tf', 'N/A')} {confirmation_status}
• Structure TF: {hierarchy.get('structure_tf', 'N/A')} {structure_status}
• HTF Bias TF: {hierarchy.get('htf_bias_tf', 'N/A')} {htf_bias_status}
"""
    
    return section


def main():
    print("=" * 70)
    print("PR #4: TIMEFRAME HIERARCHY - SIGNAL MESSAGE DEMO")
    print("=" * 70)
    print()
    
    # Demo 1: All TFs present (full compliance)
    print("📊 DEMO 1: Full TF Compliance (All TFs Present)")
    print("-" * 70)
    signal1 = create_demo_signal_with_hierarchy(entry_tf='1h', all_tfs_present=True)
    print(f"Symbol: {signal1.symbol}")
    print(f"Entry TF: {signal1.timeframe}")
    print(f"Confidence: {signal1.confidence}%")
    print(format_tf_hierarchy_section(signal1))
    print()
    
    # Demo 2: Missing Confirmation TF (penalty applied)
    print("📊 DEMO 2: Missing Confirmation TF (15% penalty)")
    print("-" * 70)
    signal2 = create_demo_signal_with_hierarchy(entry_tf='1h', all_tfs_present=False)
    print(f"Symbol: {signal2.symbol}")
    print(f"Entry TF: {signal2.timeframe}")
    print(f"Confidence: {signal2.confidence}% (reduced from 75% due to missing Confirmation TF)")
    print(format_tf_hierarchy_section(signal2))
    print()
    
    # Demo 3: Different entry TF (2H)
    print("📊 DEMO 3: 2H Entry Timeframe")
    print("-" * 70)
    signal3 = create_demo_signal_with_hierarchy(entry_tf='2h', all_tfs_present=True)
    print(f"Symbol: {signal3.symbol}")
    print(f"Entry TF: {signal3.timeframe}")
    print(f"Confidence: {signal3.confidence}%")
    print(format_tf_hierarchy_section(signal3))
    print()
    
    # Summary
    print("=" * 70)
    print("✅ TF HIERARCHY BENEFITS")
    print("=" * 70)
    print("""
1. ✅ TRANSPARENT: Users see exactly which TFs were analyzed
2. ✅ EDUCATIONAL: Shows ICT methodology (Structure → Confirmation → Entry)
3. ✅ QUALITY CONTROL: Status indicators (✅/⚠️) show compliance
4. ✅ CONFIDENCE TRACKING: Penalties visible when TFs missing
5. ✅ ICT COMPLIANT: Follows proper top-down analysis hierarchy

This PR transforms the bot from a "black box" to a transparent,
educational tool that teaches proper ICT timeframe methodology!
""")


if __name__ == "__main__":
    main()
