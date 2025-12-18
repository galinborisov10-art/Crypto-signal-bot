"""
Chart Annotator
Adds labels, arrows, and annotations to ICT charts.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from ict_signal_engine import ICTSignal

logger = logging.getLogger(__name__)


class ChartAnnotator:
    """
    Adds annotations to ICT charts.
    
    Features:
    - Zone labels with prices
    - Arrow indicators for direction
    - Entry/exit annotations
    - Custom legend with zone counts
    """
    
    def __init__(self):
        logger.info("ChartAnnotator initialized")
    
    def annotate_chart(
        self,
        ax,
        signal: 'ICTSignal',
        df_length: int
    ):
        """
        Add all annotations to chart.
        
        Args:
            ax: Matplotlib axis
            signal: ICTSignal object
            df_length: Length of price data
        """
        # Annotate zones
        self.annotate_whale_blocks(ax, signal.whale_blocks, df_length)
        self.annotate_breaker_blocks(ax, signal.breaker_blocks, df_length)
        self.annotate_mitigation_blocks(ax, signal.mitigation_blocks, df_length)
        self.annotate_sibi_ssib(ax, signal.sibi_ssib_zones, df_length)
        
        # Annotate entry/exit
        if signal.entry_price:
            self.annotate_entry_exit(ax, signal, df_length)
        
        # Add custom legend
        self.add_custom_legend(ax, signal)
    
    def annotate_whale_blocks(self, ax, whale_blocks: List, df_length: int):
        """Add labels to whale blocks"""
        if not whale_blocks:
            return
        
        for i, wb in enumerate(whale_blocks[:3]):  # Top 3 only
            wb_dict = wb.__dict__ if hasattr(wb, '__dict__') else wb
            
            price_mid = wb_dict.get('price_mid', 0)
            strength = wb_dict.get('strength', 0)
            block_type = 'Bullish' if 'BULLISH' in str(wb_dict.get('type', '')) else 'Bearish'
            
            label = f"Whale OB\n{block_type}\n${price_mid:,.2f}\nStr: {strength:.1f}/10"
            
            x_pos = df_length + 1
            ax.text(
                x_pos, price_mid, label,
                fontsize=8, ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                fontweight='bold'
            )
    
    def annotate_breaker_blocks(self, ax, breaker_blocks: List, df_length: int):
        """Add labels to breaker blocks"""
        if not breaker_blocks:
            return
        
        for bb in breaker_blocks[:2]:
            bb_dict = bb.__dict__ if hasattr(bb, '__dict__') else bb
            
            price_mid = (bb_dict.get('price_low', 0) + bb_dict.get('price_high', 0)) / 2
            block_type = 'Bullish' if 'BULLISH' in str(bb_dict.get('type', '')) else 'Bearish'
            
            label = f"Breaker\n{block_type}\n${price_mid:,.2f}"
            
            ax.text(
                df_length + 1, price_mid, label,
                fontsize=7, ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.6)
            )
    
    def annotate_mitigation_blocks(self, ax, mitigation_blocks: List, df_length: int):
        """Add labels to mitigation blocks"""
        if not mitigation_blocks:
            return
        
        for mb in mitigation_blocks[:2]:
            mb_dict = mb.__dict__ if hasattr(mb, '__dict__') else mb
            
            price_mid = (mb_dict.get('price_low', 0) + mb_dict.get('price_high', 0)) / 2
            retest_count = mb_dict.get('retest_count', 0)
            
            label = f"Mitigation\n{retest_count}x retest\n${price_mid:,.2f}"
            
            ax.text(
                df_length + 1, price_mid, label,
                fontsize=7, ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.6)
            )
    
    def annotate_sibi_ssib(self, ax, sibi_ssib_zones: List, df_length: int):
        """Add labels to SIBI/SSIB zones"""
        if not sibi_ssib_zones:
            return
        
        for zone in sibi_ssib_zones[:2]:
            zone_dict = zone.__dict__ if hasattr(zone, '__dict__') else zone
            
            price_mid = (zone_dict.get('price_low', 0) + zone_dict.get('price_high', 0)) / 2
            zone_type = zone_dict.get('type', 'SIBI')
            
            label = f"{zone_type}\n${price_mid:,.2f}"
            
            ax.text(
                df_length + 1, price_mid, label,
                fontsize=7, ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='orange', alpha=0.6)
            )
    
    def annotate_entry_exit(self, ax, signal, df_length: int):
        """Add entry, SL, TP annotations with arrows"""
        if signal.entry_price:
            # Entry arrow
            ax.annotate(
                f'Entry: ${signal.entry_price:,.2f}',
                xy=(df_length - 5, signal.entry_price),
                xytext=(df_length - 15, signal.entry_price + (signal.entry_price * 0.02)),
                fontsize=9, fontweight='bold', color='blue',
                arrowprops=dict(arrowstyle='->', color='blue', lw=2),
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8)
            )
        
        if signal.sl_price:
            ax.annotate(
                f'SL: ${signal.sl_price:,.2f}',
                xy=(df_length - 5, signal.sl_price),
                xytext=(df_length - 15, signal.sl_price - (signal.sl_price * 0.02)),
                fontsize=8, color='red',
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='pink', alpha=0.7)
            )
        
        if signal.tp_prices and len(signal.tp_prices) > 0:
            tp_price = signal.tp_prices[0]
            ax.annotate(
                f'TP: ${tp_price:,.2f}',
                xy=(df_length - 5, tp_price),
                xytext=(df_length - 15, tp_price + (tp_price * 0.02)),
                fontsize=8, color='green',
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7)
            )
    
    def add_custom_legend(self, ax, signal):
        """Add custom legend with zone counts"""
        legend_items = []
        
        # Count zones
        whale_count = len(signal.whale_blocks) if signal.whale_blocks else 0
        breaker_count = len(signal.breaker_blocks) if signal.breaker_blocks else 0
        mitigation_count = len(signal.mitigation_blocks) if signal.mitigation_blocks else 0
        sibi_ssib_count = len(signal.sibi_ssib_zones) if signal.sibi_ssib_zones else 0
        fvg_count = len(signal.fair_value_gaps) if signal.fair_value_gaps else 0
        liq_count = len(signal.liquidity_zones) if signal.liquidity_zones else 0
        
        if whale_count > 0:
            legend_items.append(f"🐋 Whale Blocks: {whale_count}")
        if breaker_count > 0:
            legend_items.append(f"💥 Breaker Blocks: {breaker_count}")
        if mitigation_count > 0:
            legend_items.append(f"🎯 Mitigation Blocks: {mitigation_count}")
        if sibi_ssib_count > 0:
            legend_items.append(f"⚡ SIBI/SSIB: {sibi_ssib_count}")
        if fvg_count > 0:
            legend_items.append(f"📊 FVG: {fvg_count}")
        if liq_count > 0:
            legend_items.append(f"💧 Liquidity: {liq_count}")
        
        legend_text = "\n".join(legend_items)
        
        ax.text(
            0.98, 0.02, legend_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment='bottom',
            horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray'),
            family='monospace'
        )
