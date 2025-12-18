"""
Zone Explainer - Natural Language ICT Zone Explanations
Generates detailed explanations for each ICT zone type with probability ratings.

Author: galinborisov10-art
Date: 2025-12-18
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ZoneExplainer:
    """
    Generates natural language explanations for ICT zones.
    
    For each zone type, explains:
    - Why institutions act here (displacement, volume, retests)
    - What liquidity they target (IBSL/ISSL)
    - Expected direction based on bias
    - Role in ICT structure (BOS/CHOCH)
    - Probability rating (0-100%)
    """
    
    def __init__(self):
        """Initialize the Zone Explainer"""
        logger.info("ZoneExplainer initialized")
    
    def explain_whale_block(
        self,
        whale_block: Any,
        liquidity_zones: List[Any],
        bias: str
    ) -> str:
        """
        Generate explanation for a whale order block.
        
        Args:
            whale_block: WhaleOrderBlock object or dict
            liquidity_zones: List of nearby liquidity zones
            bias: Market bias (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            Formatted explanation string
        """
        try:
            # Extract whale block data
            if hasattr(whale_block, '__dict__'):
                wb_dict = whale_block.__dict__
            elif hasattr(whale_block, 'to_dict'):
                wb_dict = whale_block.to_dict()
            else:
                wb_dict = whale_block
            
            wb_type = wb_dict.get('type', 'UNKNOWN')
            strength = wb_dict.get('strength', 0)
            volume_spike = wb_dict.get('volume_spike', 1.0)
            displacement = wb_dict.get('displacement_pct', 0)
            retest_count = wb_dict.get('retest_count', 0)
            
            # Calculate probability
            probability = self._calculate_whale_probability(
                wb_dict, liquidity_zones, bias, displacement, volume_spike, strength, retest_count
            )
            
            # Build explanation
            direction = "bullish" if "BULLISH" in str(wb_type) else "bearish"
            opposite_dir = "bearish" if direction == "bullish" else "bullish"
            
            explanation = f"🐋 **Whale Order Block ({direction.upper()})** - {probability}% probability\n\n"
            
            # Why institutions act here
            explanation += "**Why Institutions Act Here:**\n"
            if displacement > 0.5:
                explanation += f"• Strong displacement detected ({displacement:.2f}%) indicates institutional activity\n"
            if volume_spike > 2.0:
                explanation += f"• Exceptional volume spike ({volume_spike:.1f}x average) confirms large orders\n"
            elif volume_spike > 1.5:
                explanation += f"• Elevated volume ({volume_spike:.1f}x average) suggests significant interest\n"
            if strength >= 8.0:
                explanation += f"• High strength rating ({strength:.1f}/10) shows strong zone quality\n"
            if retest_count > 0:
                explanation += f"• Zone has been retested {retest_count} time(s), confirming validity\n"
            
            # Liquidity targets
            explanation += "\n**Liquidity Targets:**\n"
            nearby_liq = self._count_nearby_liquidity(whale_block, liquidity_zones)
            if nearby_liq > 0:
                explanation += f"• {nearby_liq} liquidity zone(s) nearby - institutions likely targeting IBSL/ISSL\n"
                if direction == "bullish":
                    explanation += "• Buy-Side Liquidity (IBSL) below as potential draw\n"
                else:
                    explanation += "• Sell-Side Liquidity (ISSL) above as potential target\n"
            else:
                explanation += "• No immediate liquidity zones identified\n"
            
            # Expected direction
            explanation += "\n**Expected Direction:**\n"
            bias_aligned = self._check_bias_alignment(direction, bias)
            if bias_aligned:
                explanation += f"• ✅ Zone aligns with {bias} bias - higher probability setup\n"
                explanation += f"• Expect price to respect this zone and move {direction}\n"
            else:
                explanation += f"• ⚠️ Zone conflicts with {bias} bias - lower probability\n"
                explanation += f"• Wait for bias shift or stronger confirmation\n"
            
            # Role in structure
            explanation += "\n**Role in ICT Structure:**\n"
            explanation += f"• Acts as institutional {direction} zone after {opposite_dir} move\n"
            if retest_count == 0:
                explanation += "• Untested zone - first retest may be optimal entry\n"
            else:
                explanation += f"• Previously tested {retest_count}x - still valid if holding\n"
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining whale block: {e}")
            return "Error generating whale block explanation"
    
    def explain_breaker_block(
        self,
        breaker_block: Any,
        bias: str
    ) -> str:
        """
        Generate explanation for a breaker block.
        
        Args:
            breaker_block: BreakerBlock object or dict
            bias: Market bias (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            Formatted explanation string
        """
        try:
            # Extract breaker block data
            if hasattr(breaker_block, '__dict__'):
                bb_dict = breaker_block.__dict__
            elif hasattr(breaker_block, 'to_dict'):
                bb_dict = breaker_block.to_dict()
            else:
                bb_dict = breaker_block
            
            bb_type = bb_dict.get('type', 'UNKNOWN')
            original_type = bb_dict.get('original_type', 'UNKNOWN')
            strength = bb_dict.get('strength', 0)
            retest_count = bb_dict.get('retest_count', 0)
            status = bb_dict.get('status', 'UNKNOWN')
            
            # Calculate probability
            probability = self._calculate_breaker_probability(
                bb_dict, bias, strength, retest_count
            )
            
            # Build explanation
            direction = "bullish" if "BULLISH" in str(bb_type) else "bearish"
            prev_direction = "bearish" if direction == "bullish" else "bullish"
            
            explanation = f"💥 **Breaker Block ({direction.upper()})** - {probability}% probability\n\n"
            
            # Why institutions act here
            explanation += "**Why Institutions Act Here:**\n"
            explanation += f"• Original {prev_direction} order block was breached (Break of Structure)\n"
            explanation += f"• Zone now acts with opposite polarity as {direction} zone\n"
            if strength >= 6.0:
                explanation += f"• Strong breach strength ({strength:.1f}/10) confirms reversal\n"
            if retest_count > 0:
                explanation += f"• Already tested {retest_count}x with opposite polarity\n"
            
            # Liquidity targets
            explanation += "\n**Liquidity Targets:**\n"
            explanation += "• Breaker blocks often target liquidity at previous extremes\n"
            if direction == "bullish":
                explanation += "• Institutions may target sell-side liquidity above breached zone\n"
            else:
                explanation += "• Institutions may target buy-side liquidity below breached zone\n"
            
            # Expected direction
            explanation += "\n**Expected Direction:**\n"
            bias_aligned = self._check_bias_alignment(direction, bias)
            if bias_aligned:
                explanation += f"• ✅ Breaker aligns with {bias} bias\n"
                explanation += f"• Price likely to respect zone and continue {direction}\n"
            else:
                explanation += f"• ⚠️ Breaker conflicts with {bias} bias\n"
                explanation += "• Reduced probability - wait for confirmation\n"
            
            # Role in structure
            explanation += "\n**Role in ICT Structure:**\n"
            explanation += "• Represents Change of Character (CHOCH) in market structure\n"
            explanation += f"• Zone transition: {prev_direction} → {direction}\n"
            if status == "ACTIVE":
                explanation += "• Currently active and untested at new polarity\n"
            elif status == "TESTED":
                explanation += "• Successfully tested - confirms new polarity\n"
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining breaker block: {e}")
            return "Error generating breaker block explanation"
    
    def explain_mitigation_block(
        self,
        mitigation_block: Any,
        bias: str
    ) -> str:
        """
        Generate explanation for a mitigation block.
        
        Args:
            mitigation_block: MitigationBlock object or dict
            bias: Market bias (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            Formatted explanation string
        """
        try:
            # Extract mitigation block data
            if hasattr(mitigation_block, '__dict__'):
                mb_dict = mitigation_block.__dict__
            elif hasattr(mitigation_block, 'to_dict'):
                mb_dict = mitigation_block.to_dict()
            else:
                mb_dict = mitigation_block
            
            mb_type = mb_dict.get('type', 'UNKNOWN')
            strength = mb_dict.get('strength', 0)
            mitigation_pct = mb_dict.get('mitigation_pct', 0)
            status = mb_dict.get('status', 'UNKNOWN')
            
            # Calculate probability
            probability = self._calculate_mitigation_probability(
                mb_dict, bias, strength, mitigation_pct
            )
            
            # Build explanation
            direction = "bullish" if "BULLISH" in str(mb_type) else "bearish"
            
            explanation = f"🎯 **Mitigation Block ({direction.upper()})** - {probability}% probability\n\n"
            
            # Why institutions act here
            explanation += "**Why Institutions Act Here:**\n"
            explanation += "• Order block has been partially mitigated (price returned to zone)\n"
            if mitigation_pct > 0:
                explanation += f"• {mitigation_pct:.1f}% of zone has been filled\n"
            if strength >= 7.0:
                explanation += f"• High strength ({strength:.1f}/10) despite mitigation\n"
            explanation += "• Remaining zone still valid for institutional interest\n"
            
            # Liquidity targets
            explanation += "\n**Liquidity Targets:**\n"
            if direction == "bullish":
                explanation += "• Institutions targeting liquidity below mitigation zone\n"
                explanation += "• IBSL (Internal Buy-Side Liquidity) as draw on liquidity\n"
            else:
                explanation += "• Institutions targeting liquidity above mitigation zone\n"
                explanation += "• ISSL (Internal Sell-Side Liquidity) as draw on liquidity\n"
            
            # Expected direction
            explanation += "\n**Expected Direction:**\n"
            bias_aligned = self._check_bias_alignment(direction, bias)
            if bias_aligned:
                explanation += f"• ✅ Mitigation zone aligns with {bias} bias\n"
                if mitigation_pct < 50:
                    explanation += "• Zone mostly intact - good probability of reaction\n"
                else:
                    explanation += "• Zone significantly mitigated - reduced reaction probability\n"
            else:
                explanation += f"• ⚠️ Zone conflicts with {bias} bias\n"
                explanation += "• Lower probability - may be fully mitigated\n"
            
            # Role in structure
            explanation += "\n**Role in ICT Structure:**\n"
            explanation += "• Represents partial order fulfillment by institutions\n"
            if status == "PARTIALLY_MITIGATED":
                explanation += "• Zone still has unfilled orders remaining\n"
            explanation += f"• Expect {direction} reaction if price returns to zone\n"
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining mitigation block: {e}")
            return "Error generating mitigation block explanation"
    
    def explain_sibi_ssib(
        self,
        sibi_ssib_zone: Any,
        bias: str
    ) -> str:
        """
        Generate explanation for SIBI/SSIB zone.
        
        Args:
            sibi_ssib_zone: SIBISSIBZone object or dict
            bias: Market bias (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            Formatted explanation string
        """
        try:
            # Extract zone data
            if hasattr(sibi_ssib_zone, '__dict__'):
                zone_dict = sibi_ssib_zone.__dict__
            elif hasattr(sibi_ssib_zone, 'to_dict'):
                zone_dict = sibi_ssib_zone.to_dict()
            else:
                zone_dict = sibi_ssib_zone
            
            zone_type = zone_dict.get('type', 'UNKNOWN')
            strength = zone_dict.get('strength', 0)
            displacement_size = zone_dict.get('displacement_size', 0)
            displacement_direction = zone_dict.get('displacement_direction', 'UNKNOWN')
            fvg_count = zone_dict.get('fvg_count', 0)
            liquidity_void = zone_dict.get('liquidity_void', False)
            
            # Calculate probability
            probability = self._calculate_sibi_ssib_probability(
                zone_dict, bias, strength, displacement_size, fvg_count
            )
            
            # Build explanation
            is_sibi = zone_type == 'SIBI'
            direction = "bullish" if is_sibi else "bearish"
            zone_name = "SIBI (Sell-Side Imbalance Buy-Side Inefficiency)" if is_sibi else "SSIB (Buy-Side Imbalance Sell-Side Inefficiency)"
            
            explanation = f"⚡ **{zone_name}** - {probability}% probability\n\n"
            
            # Why institutions act here
            explanation += "**Why Institutions Act Here:**\n"
            if displacement_size > 1.0:
                explanation += f"• Strong displacement ({displacement_size:.2f}%) created imbalance\n"
            else:
                explanation += f"• Moderate displacement ({displacement_size:.2f}%) left inefficiency\n"
            
            if fvg_count > 0:
                explanation += f"• {fvg_count} Fair Value Gap(s) present in zone\n"
            
            if liquidity_void:
                explanation += "• Liquidity void detected - price moved too fast\n"
                explanation += "• Institutions need to fill orders in this zone\n"
            
            if strength >= 7.0:
                explanation += f"• High quality zone (strength: {strength:.1f}/10)\n"
            
            # Liquidity targets
            explanation += "\n**Liquidity Targets:**\n"
            if is_sibi:
                explanation += "• Created during bullish displacement\n"
                explanation += "• Sell-side imbalance + buy-side inefficiency below\n"
                explanation += "• Price may return to fill inefficiency (support)\n"
            else:
                explanation += "• Created during bearish displacement\n"
                explanation += "• Buy-side imbalance + sell-side inefficiency above\n"
                explanation += "• Price may return to fill inefficiency (resistance)\n"
            
            # Expected direction
            explanation += "\n**Expected Direction:**\n"
            bias_aligned = self._check_bias_alignment(direction, bias)
            if bias_aligned:
                explanation += f"• ✅ Zone aligns with {bias} bias\n"
                explanation += f"• Expect {direction} reaction when price returns\n"
            else:
                explanation += f"• ⚠️ Zone conflicts with {bias} bias\n"
                explanation += "• May be filled during counter-trend move\n"
            
            # Role in structure
            explanation += "\n**Role in ICT Structure:**\n"
            explanation += "• Advanced ICT concept combining displacement + imbalance\n"
            if is_sibi:
                explanation += "• Acts as potential support after bullish move\n"
            else:
                explanation += "• Acts as potential resistance after bearish move\n"
            explanation += "• High-probability reversal zone if retested\n"
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining SIBI/SSIB zone: {e}")
            return "Error generating SIBI/SSIB explanation"
    
    def generate_all_explanations(
        self,
        ict_components: Dict[str, List],
        bias: str
    ) -> Dict[str, List[str]]:
        """
        Generate explanations for all ICT components.
        
        Args:
            ict_components: Dict containing all ICT zones
            bias: Market bias (BULLISH/BEARISH/NEUTRAL)
            
        Returns:
            Dict with zone type as key and list of explanations as value
        """
        explanations = {
            'whale_blocks': [],
            'breaker_blocks': [],
            'mitigation_blocks': [],
            'sibi_ssib_zones': []
        }
        
        try:
            # Explain whale blocks
            whale_blocks = ict_components.get('whale_blocks', [])
            liquidity_zones = ict_components.get('liquidity_zones', [])
            for wb in whale_blocks[:3]:  # Limit to top 3
                explanation = self.explain_whale_block(wb, liquidity_zones, bias)
                explanations['whale_blocks'].append(explanation)
            
            # Explain breaker blocks
            breaker_blocks = ict_components.get('breaker_blocks', [])
            for bb in breaker_blocks[:3]:  # Limit to top 3
                explanation = self.explain_breaker_block(bb, bias)
                explanations['breaker_blocks'].append(explanation)
            
            # Explain mitigation blocks
            mitigation_blocks = ict_components.get('mitigation_blocks', [])
            for mb in mitigation_blocks[:3]:  # Limit to top 3
                explanation = self.explain_mitigation_block(mb, bias)
                explanations['mitigation_blocks'].append(explanation)
            
            # Explain SIBI/SSIB zones
            sibi_ssib_zones = ict_components.get('sibi_ssib_zones', [])
            for zone in sibi_ssib_zones[:3]:  # Limit to top 3
                explanation = self.explain_sibi_ssib(zone, bias)
                explanations['sibi_ssib_zones'].append(explanation)
            
            logger.info(f"Generated explanations for {sum(len(v) for v in explanations.values())} zones")
            
        except Exception as e:
            logger.error(f"Error generating all explanations: {e}")
        
        return explanations
    
    # Helper methods for probability calculation
    
    def _calculate_whale_probability(
        self,
        whale_block: Dict,
        liquidity_zones: List,
        bias: str,
        displacement: float,
        volume_spike: float,
        strength: float,
        retest_count: int
    ) -> int:
        """Calculate probability for whale block (0-100%)"""
        probability = 50  # Base probability
        
        # Displacement presence (+20%)
        if displacement > 0.5:
            probability += 20
        
        # Volume spike
        if volume_spike > 2.0:
            probability += 15
        elif volume_spike > 1.5:
            probability += 10
        
        # Bias alignment (+10%)
        wb_type = whale_block.get('type', '')
        is_bullish = "BULLISH" in str(wb_type)
        if (is_bullish and "BULLISH" in bias) or (not is_bullish and "BEARISH" in bias):
            probability += 10
        
        # Nearby liquidity (+3% per zone, max 10%)
        nearby_count = self._count_nearby_liquidity(whale_block, liquidity_zones)
        probability += min(10, nearby_count * 3)
        
        # Retest count (+5% per retest, max 10%)
        probability += min(10, retest_count * 5)
        
        # High strength (+5%)
        if strength >= 8.0:
            probability += 5
        
        return min(100, max(0, probability))
    
    def _calculate_breaker_probability(
        self,
        breaker_block: Dict,
        bias: str,
        strength: float,
        retest_count: int
    ) -> int:
        """Calculate probability for breaker block (0-100%)"""
        probability = 55  # Base probability (slightly higher due to structure break)
        
        # Strength
        if strength >= 8.0:
            probability += 15
        elif strength >= 6.0:
            probability += 10
        
        # Bias alignment
        bb_type = breaker_block.get('type', '')
        is_bullish = "BULLISH" in str(bb_type)
        if (is_bullish and "BULLISH" in bias) or (not is_bullish and "BEARISH" in bias):
            probability += 10
        
        # Retest count
        probability += min(10, retest_count * 5)
        
        # Status bonus
        if breaker_block.get('status') == 'TESTED':
            probability += 10
        
        return min(100, max(0, probability))
    
    def _calculate_mitigation_probability(
        self,
        mitigation_block: Dict,
        bias: str,
        strength: float,
        mitigation_pct: float
    ) -> int:
        """Calculate probability for mitigation block (0-100%)"""
        probability = 45  # Base probability (lower due to partial fill)
        
        # Strength
        if strength >= 7.0:
            probability += 15
        elif strength >= 5.0:
            probability += 10
        
        # Mitigation percentage (inverse - less mitigation = higher probability)
        if mitigation_pct < 30:
            probability += 15
        elif mitigation_pct < 50:
            probability += 10
        elif mitigation_pct < 70:
            probability += 5
        
        # Bias alignment
        mb_type = mitigation_block.get('type', '')
        is_bullish = "BULLISH" in str(mb_type)
        if (is_bullish and "BULLISH" in bias) or (not is_bullish and "BEARISH" in bias):
            probability += 10
        
        return min(100, max(0, probability))
    
    def _calculate_sibi_ssib_probability(
        self,
        zone: Dict,
        bias: str,
        strength: float,
        displacement_size: float,
        fvg_count: int
    ) -> int:
        """Calculate probability for SIBI/SSIB zone (0-100%)"""
        probability = 60  # Base probability (higher due to advanced nature)
        
        # Displacement
        if displacement_size > 1.5:
            probability += 20
        elif displacement_size > 1.0:
            probability += 15
        elif displacement_size > 0.5:
            probability += 10
        
        # Strength
        if strength >= 8.0:
            probability += 10
        elif strength >= 6.0:
            probability += 5
        
        # FVG count
        probability += min(10, fvg_count * 3)
        
        # Liquidity void
        if zone.get('liquidity_void', False):
            probability += 10
        
        # Bias alignment
        zone_type = zone.get('type', '')
        is_sibi = zone_type == 'SIBI'
        if (is_sibi and "BULLISH" in bias) or (not is_sibi and "BEARISH" in bias):
            probability += 10
        
        return min(100, max(0, probability))
    
    def _count_nearby_liquidity(self, zone: Any, liquidity_zones: List) -> int:
        """Count liquidity zones near the given zone"""
        if not liquidity_zones:
            return 0
        
        try:
            # Get zone price range
            if hasattr(zone, '__dict__'):
                zone_dict = zone.__dict__
            elif hasattr(zone, 'to_dict'):
                zone_dict = zone.to_dict()
            else:
                zone_dict = zone
            
            zone_low = zone_dict.get('price_low', 0) or zone_dict.get('bottom', 0)
            zone_high = zone_dict.get('price_high', 0) or zone_dict.get('top', 0)
            
            if zone_low == 0 or zone_high == 0:
                return 0
            
            zone_mid = (zone_low + zone_high) / 2
            zone_range = zone_high - zone_low
            search_distance = zone_range * 2  # Search within 2x zone size
            
            # Count nearby liquidity zones
            count = 0
            for liq_zone in liquidity_zones:
                if hasattr(liq_zone, '__dict__'):
                    liq_dict = liq_zone.__dict__
                else:
                    liq_dict = liq_zone
                
                liq_price = liq_dict.get('price', 0)
                if liq_price > 0:
                    distance = abs(liq_price - zone_mid)
                    if distance <= search_distance:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting nearby liquidity: {e}")
            return 0
    
    def _check_bias_alignment(self, zone_direction: str, bias: str) -> bool:
        """Check if zone direction aligns with market bias"""
        zone_direction = zone_direction.upper()
        bias = bias.upper()
        
        if "BULLISH" in zone_direction and "BULLISH" in bias:
            return True
        if "BEARISH" in zone_direction and "BEARISH" in bias:
            return True
        
        return False


# Example usage
if __name__ == "__main__":
    print("🎯 Zone Explainer - Test Mode")
    
    explainer = ZoneExplainer()
    
    # Test whale block explanation
    test_whale = {
        'type': 'BULLISH_WHALE',
        'strength': 8.5,
        'volume_spike': 2.3,
        'displacement_pct': 1.2,
        'retest_count': 1,
        'price_low': 50000,
        'price_high': 50500
    }
    
    test_liquidity = [
        {'price': 49800},
        {'price': 50700}
    ]
    
    explanation = explainer.explain_whale_block(test_whale, test_liquidity, "BULLISH")
    print(explanation)
    print("\n" + "="*80 + "\n")
    
    # Test all explanations
    test_components = {
        'whale_blocks': [test_whale],
        'breaker_blocks': [],
        'mitigation_blocks': [],
        'sibi_ssib_zones': []
    }
    
    all_explanations = explainer.generate_all_explanations(test_components, "BULLISH")
    print(f"Generated {sum(len(v) for v in all_explanations.values())} total explanations")
    
    print("\n✅ Zone Explainer test completed!")
