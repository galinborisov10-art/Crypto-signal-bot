"""
ICT Chart Generator
Generates color-coded price charts with ICT zones overlay.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.dates import DateFormatter
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import io
import logging

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates ICT signal charts with color-coded zones.
    
    Features:
    - OHLC candlestick chart
    - Color-coded ICT zones (whale blocks, breakers, etc.)
    - Price levels and support/resistance
    - Volume subplot
    - Professional styling
    """
    
    # Color scheme for ICT zones
    COLORS = {
        'whale_bullish': '#2ECC71',      # Green
        'whale_bearish': '#E74C3C',      # Red
        'breaker_bullish': '#3498DB',    # Blue
        'breaker_bearish': '#E67E22',    # Orange
        'mitigation_bullish': '#1ABC9C', # Teal
        'mitigation_bearish': '#9B59B6', # Purple
        'sibi': '#F39C12',               # Yellow
        'ssib': '#34495E',               # Dark gray
        'fvg_bullish': '#2ECC71',        # Light green (will use alpha in plotting)
        'fvg_bearish': '#E74C3C',        # Light red (will use alpha in plotting)
        'liquidity_buy': '#16A085',      # Dark teal
        'liquidity_sell': '#C0392B',     # Dark red
        'background': '#FFFFFF',
        'grid': '#E0E0E0',
        'text': '#2C3E50',
        'candle_up': '#26A69A',
        'candle_down': '#EF5350'
    }
    
    def __init__(self, style: str = 'professional'):
        """
        Initialize chart generator.
        
        Args:
            style: Chart style ('professional', 'dark', 'minimal')
        """
        self.style = style
        self.fig_size = (14, 10)
        self.dpi = 100
        logger.info(f"ChartGenerator initialized (style={style})")
    
    def generate(
        self,
        df: pd.DataFrame,
        signal: 'ICTSignal',
        symbol: str,
        timeframe: str,
        title: Optional[str] = None
    ) -> bytes:
        """
        Generate complete ICT chart.
        
        Args:
            df: OHLCV DataFrame with columns ['open', 'high', 'low', 'close', 'volume', 'timestamp']
            signal: ICTSignal object with all zones
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "4H")
            title: Optional custom title
            
        Returns:
            PNG image as bytes
        """
        try:
            # Create figure with subplots
            fig, (ax_price, ax_volume) = plt.subplots(
                2, 1, 
                figsize=self.fig_size,
                gridspec_kw={'height_ratios': [3, 1]},
                dpi=self.dpi
            )
            
            # Plot candlesticks
            self._plot_candlesticks(ax_price, df)
            
            # Plot ICT zones (layered by priority)
            self._plot_fvg_zones(ax_price, signal.fair_value_gaps)
            self._plot_whale_blocks(ax_price, signal.whale_blocks)
            self._plot_breaker_blocks(ax_price, signal.breaker_blocks)
            self._plot_mitigation_blocks(ax_price, signal.mitigation_blocks)
            self._plot_sibi_ssib_zones(ax_price, signal.sibi_ssib_zones)
            self._plot_liquidity_zones(ax_price, signal.liquidity_zones)
            
            # Plot entry/exit levels
            if signal.entry_price:
                self._plot_entry_exit(ax_price, signal)
            
            # Plot volume
            self._plot_volume(ax_volume, df)
            
            # Styling and labels
            self._apply_styling(ax_price, ax_volume, df)
            
            # Title
            chart_title = title or f"{symbol} {timeframe} - ICT Analysis"
            fig.suptitle(chart_title, fontsize=16, fontweight='bold', color=self.COLORS['text'])
            
            # Add signal info box
            self._add_info_box(ax_price, signal)
            
            # Tight layout
            plt.tight_layout()
            
            # Convert to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            
            logger.info(f"Chart generated successfully for {symbol} {timeframe}")
            return buf.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            plt.close('all')
            raise
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot OHLC candlesticks"""
        for i, row in df.iterrows():
            color = self.COLORS['candle_up'] if row['close'] >= row['open'] else self.COLORS['candle_down']
            
            # High-Low line
            ax.plot([i, i], [row['low'], row['high']], color=color, linewidth=1)
            
            # Open-Close body
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            ax.add_patch(patches.Rectangle(
                (i - 0.3, bottom), 0.6, height,
                facecolor=color, edgecolor=color, linewidth=1
            ))
    
    def _plot_whale_blocks(self, ax, whale_blocks: List):
        """Plot whale order blocks"""
        if not whale_blocks:
            return
        
        for wb in whale_blocks:
            wb_dict = wb.__dict__ if hasattr(wb, '__dict__') else wb
            
            block_type = str(wb_dict.get('type', ''))
            is_bullish = 'BULLISH' in block_type
            color = self.COLORS['whale_bullish'] if is_bullish else self.COLORS['whale_bearish']
            
            # Extract zone boundaries
            x_start = wb_dict.get('start_index', 0)
            x_end = len(ax.get_xlim()) if wb_dict.get('is_active', True) else x_start + 10
            y_low = wb_dict.get('price_low', 0)
            y_high = wb_dict.get('price_high', 0)
            
            # Draw rectangle
            rect = patches.Rectangle(
                (x_start, y_low),
                x_end - x_start,
                y_high - y_low,
                linewidth=2,
                edgecolor=color,
                facecolor=color,
                alpha=0.15,
                label='Whale OB'
            )
            ax.add_patch(rect)
    
    def _plot_breaker_blocks(self, ax, breaker_blocks: List):
        """Plot breaker blocks with dashed borders"""
        if not breaker_blocks:
            return
        
        for bb in breaker_blocks:
            bb_dict = bb.__dict__ if hasattr(bb, '__dict__') else bb
            
            block_type = str(bb_dict.get('type', ''))
            is_bullish = 'BULLISH' in block_type
            color = self.COLORS['breaker_bullish'] if is_bullish else self.COLORS['breaker_bearish']
            
            x_start = bb_dict.get('start_index', 0)
            x_end = x_start + 10
            y_low = bb_dict.get('price_low', 0)
            y_high = bb_dict.get('price_high', 0)
            
            # Dashed rectangle for breakers
            rect = patches.Rectangle(
                (x_start, y_low),
                x_end - x_start,
                y_high - y_low,
                linewidth=2,
                edgecolor=color,
                facecolor=color,
                alpha=0.12,
                linestyle='--',
                label='Breaker'
            )
            ax.add_patch(rect)
    
    def _plot_mitigation_blocks(self, ax, mitigation_blocks: List):
        """Plot mitigation blocks with dotted borders"""
        if not mitigation_blocks:
            return
        
        for mb in mitigation_blocks:
            mb_dict = mb.__dict__ if hasattr(mb, '__dict__') else mb
            
            block_type = str(mb_dict.get('type', ''))
            is_bullish = 'BULLISH' in block_type
            color = self.COLORS['mitigation_bullish'] if is_bullish else self.COLORS['mitigation_bearish']
            
            x_start = mb_dict.get('start_index', 0)
            x_end = x_start + 8
            y_low = mb_dict.get('price_low', 0)
            y_high = mb_dict.get('price_high', 0)
            
            rect = patches.Rectangle(
                (x_start, y_low),
                x_end - x_start,
                y_high - y_low,
                linewidth=1.5,
                edgecolor=color,
                facecolor=color,
                alpha=0.1,
                linestyle=':',
                label='Mitigation'
            )
            ax.add_patch(rect)
    
    def _plot_sibi_ssib_zones(self, ax, sibi_ssib_zones: List):
        """Plot SIBI/SSIB zones"""
        if not sibi_ssib_zones:
            return
        
        for zone in sibi_ssib_zones:
            zone_dict = zone.__dict__ if hasattr(zone, '__dict__') else zone
            
            zone_type = zone_dict.get('type', '')
            color = self.COLORS['sibi'] if zone_type == 'SIBI' else self.COLORS['ssib']
            
            x_start = zone_dict.get('start_index', 0)
            x_end = x_start + 6
            y_low = zone_dict.get('price_low', 0)
            y_high = zone_dict.get('price_high', 0)
            
            rect = patches.Rectangle(
                (x_start, y_low),
                x_end - x_start,
                y_high - y_low,
                linewidth=1,
                edgecolor=color,
                facecolor=color,
                alpha=0.2,
                label=zone_type
            )
            ax.add_patch(rect)
    
    def _plot_fvg_zones(self, ax, fvg_zones: List):
        """Plot Fair Value Gaps"""
        if not fvg_zones:
            return
        
        for fvg in fvg_zones:
            fvg_dict = fvg.__dict__ if hasattr(fvg, '__dict__') else fvg
            
            fvg_type = str(fvg_dict.get('type', ''))
            is_bullish = 'BULLISH' in fvg_type
            color = self.COLORS['fvg_bullish'] if is_bullish else self.COLORS['fvg_bearish']
            
            x_start = fvg_dict.get('start_index', 0)
            x_end = x_start + 5
            y_low = fvg_dict.get('bottom', fvg_dict.get('price_low', 0))
            y_high = fvg_dict.get('top', fvg_dict.get('price_high', 0))
            
            rect = patches.Rectangle(
                (x_start, y_low),
                x_end - x_start,
                y_high - y_low,
                facecolor=color,
                alpha=0.3,
                label='FVG'
            )
            ax.add_patch(rect)
    
    def _plot_liquidity_zones(self, ax, liquidity_zones: List):
        """Plot liquidity zones as horizontal lines"""
        if not liquidity_zones:
            return
        
        for liq in liquidity_zones:
            liq_dict = liq.__dict__ if hasattr(liq, '__dict__') else liq
            
            liq_type = str(liq_dict.get('type', ''))
            is_buy_side = 'BSL' in liq_type or 'IBSL' in liq_type
            color = self.COLORS['liquidity_buy'] if is_buy_side else self.COLORS['liquidity_sell']
            
            price = liq_dict.get('price', 0)
            ax.axhline(y=price, color=color, linestyle='-.', linewidth=1.5, alpha=0.7, label='Liquidity')
    
    def _plot_entry_exit(self, ax, signal):
        """Plot entry, stop loss, and take profit levels"""
        if signal.entry_price:
            ax.axhline(y=signal.entry_price, color='blue', linestyle='-', linewidth=2, label='Entry', alpha=0.8)
        
        if signal.sl_price:
            ax.axhline(y=signal.sl_price, color='red', linestyle='--', linewidth=2, label='Stop Loss', alpha=0.8)
        
        if signal.tp_prices and len(signal.tp_prices) > 0:
            # Plot first TP
            ax.axhline(y=signal.tp_prices[0], color='green', linestyle='--', linewidth=2, label='Take Profit', alpha=0.8)
    
    def _plot_volume(self, ax, df: pd.DataFrame):
        """Plot volume bars"""
        colors = [self.COLORS['candle_up'] if row['close'] >= row['open'] else self.COLORS['candle_down'] 
                  for _, row in df.iterrows()]
        ax.bar(range(len(df)), df['volume'], color=colors, alpha=0.5, width=0.8)
        ax.set_ylabel('Volume', fontsize=10, color=self.COLORS['text'])
        ax.grid(True, alpha=0.3, color=self.COLORS['grid'])
    
    def _apply_styling(self, ax_price, ax_volume, df: pd.DataFrame):
        """Apply professional styling"""
        ax_price.set_ylabel('Price', fontsize=12, fontweight='bold', color=self.COLORS['text'])
        ax_price.grid(True, alpha=0.3, color=self.COLORS['grid'], linestyle='--')
        ax_price.set_xlim(-1, len(df))
        
        # Remove duplicate labels in legend
        handles, labels = ax_price.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax_price.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=9, framealpha=0.9)
        
        ax_volume.set_xlabel('Candles', fontsize=10, color=self.COLORS['text'])
    
    def _add_info_box(self, ax, signal):
        """Add signal information box"""
        info_text = f"Signal: {signal.signal_type.value}\n"
        info_text += f"Confidence: {signal.confidence:.1f}%\n"
        info_text += f"Bias: {signal.bias.value}"
        
        ax.text(
            0.02, 0.98, info_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            family='monospace'
        )


def generate_chart(df: pd.DataFrame, signal, symbol: str, timeframe: str) -> bytes:
    """Convenience function to generate chart"""
    generator = ChartGenerator()
    return generator.generate(df, signal, symbol, timeframe)
