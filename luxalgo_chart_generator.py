"""
LuxAlgo Chart Generator - TradingView Style
Professional chart generation with all LuxAlgo indicators combined
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def generate_luxalgo_chart(
    df: pd.DataFrame,
    symbol: str,
    signal: str,
    current_price: float,
    tp_price: float,
    sl_price: float,
    timeframe: str,
    sr_data: dict = None,
    ict_data: dict = None
) -> BytesIO:
    """
    Generate professional TradingView-style chart with LuxAlgo indicators
    
    Shows:
    - S/R zones (LuxAlgo MTF)
    - Order Blocks (ICT)
    - Fair Value Gaps (ICT)
    - MSS/BOS markers (ICT)
    - BSL/SSL liquidity (both)
    - Swing points (both)
    - Entry/TP/SL levels
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Trading pair symbol
        signal: BUY/SELL
        current_price: Current price
        tp_price: Take profit target
        sl_price: Stop loss
        timeframe: Timeframe string
        sr_data: Support/Resistance data from LuxAlgo MTF
        ict_data: ICT Concepts data
    
    Returns:
        BytesIO buffer with chart image
    """
    try:
        # Take last 100 candles for TradingView-like view
        df = df.tail(100).reset_index(drop=True)
        
        if len(df) < 10:
            logger.warning(f"Insufficient data: {len(df)} candles")
            return None
        
        # Create figure - 16:9 format, dark theme
        fig = plt.figure(figsize=(20, 11), facecolor='#0d1117')
        
        # 2 panels: Main chart (80%), Volume (20%)
        gs = fig.add_gridspec(2, 1, height_ratios=[8, 2], hspace=0.05)
        
        # Main chart
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor('#161b22')
        
        # Volume panel
        ax_vol = fig.add_subplot(gs[1], sharex=ax1)
        ax_vol.set_facecolor('#161b22')
        
        # Subtle grid
        ax1.grid(True, alpha=0.1, linestyle=':', linewidth=0.4, color='#30363d')
        ax_vol.grid(True, alpha=0.1, linestyle=':', linewidth=0.4, color='#30363d')
        
        # === CANDLESTICKS - Realistic style ===
        for idx, row in df.iterrows():
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            
            # Wicks
            ax1.plot([idx, idx], [row['low'], row['high']], 
                    color=color, linewidth=0.6, alpha=0.9)
            
            # Body
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            ax1.add_patch(plt.Rectangle(
                (idx - 0.25, bottom), 0.5, height,
                facecolor=color, edgecolor=color, 
                linewidth=0.8, alpha=1.0
            ))
        
        # === VOLUME BARS ===
        for idx, row in df.iterrows():
            vol_color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            ax_vol.bar(idx, row['volume'], color=vol_color, alpha=0.6, width=0.8)
        
        # === S/R ZONES (LuxAlgo MTF) ===
        if sr_data:
            # Support zones - soft green
            for zone in sr_data.get('support_zones', [])[:5]:
                left = max(0, zone.left - len(df) + 100)
                right = min(len(df), zone.right - len(df) + 100 + 1)
                
                if right > 0 and left < len(df):
                    # Zone rectangle
                    width = right - left
                    ax1.add_patch(plt.Rectangle(
                        (left, zone.bottom), width, zone.top - zone.bottom,
                        facecolor='#81c784', alpha=0.12, 
                        edgecolor='#388e3c', linewidth=1, zorder=2
                    ))
                    
                    # Support line
                    ax1.plot([left, right], [zone.bottom, zone.bottom],
                            color='#388e3c', linewidth=1.5, alpha=0.7, zorder=3)
                    
                    # Label
                    ax1.text(right + 0.5, zone.bottom, 'S',
                            fontsize=7, color='#388e3c', weight='bold',
                            bbox=dict(boxstyle='circle,pad=0.2', 
                                    facecolor='#0d1117', alpha=0.8,
                                    edgecolor='#388e3c', linewidth=1))
            
            # Resistance zones - soft red
            for zone in sr_data.get('resistance_zones', [])[:5]:
                left = max(0, zone.left - len(df) + 100)
                right = min(len(df), zone.right - len(df) + 100 + 1)
                
                if right > 0 and left < len(df):
                    width = right - left
                    ax1.add_patch(plt.Rectangle(
                        (left, zone.bottom), width, zone.top - zone.bottom,
                        facecolor='#e57373', alpha=0.12,
                        edgecolor='#c62828', linewidth=1, zorder=2
                    ))
                    
                    # Resistance line
                    ax1.plot([left, right], [zone.top, zone.top],
                            color='#c62828', linewidth=1.5, alpha=0.7, zorder=3)
                    
                    # Label
                    ax1.text(right + 0.5, zone.top, 'R',
                            fontsize=7, color='#c62828', weight='bold',
                            bbox=dict(boxstyle='circle,pad=0.2',
                                    facecolor='#0d1117', alpha=0.8,
                                    edgecolor='#c62828', linewidth=1))
            
            # === SIGNALS (Breakouts, Tests, Retests) ===
            for sig in sr_data.get('signals', [])[-10:]:
                sig_idx = sig.bar_index - (len(df) - 100)
                if 0 <= sig_idx < len(df):
                    sig_type = sig.type
                    sig_dir = sig.direction
                    
                    if sig_type == 'breakout':
                        if sig_dir == 'bullish':
                            marker = '▲\nB'
                            color = '#26a69a'
                            y_pos = df.loc[sig_idx, 'low'] * 0.997
                            style = 'label_up'
                        else:
                            marker = 'B\n▼'
                            color = '#ef5350'
                            y_pos = df.loc[sig_idx, 'high'] * 1.003
                            style = 'label_down'
                        
                        ax1.text(sig_idx, y_pos, marker,
                                fontsize=8, color='white', weight='bold',
                                ha='center', va='bottom' if sig_dir == 'bullish' else 'top',
                                bbox=dict(boxstyle='round,pad=0.3',
                                        facecolor=color, alpha=0.9,
                                        edgecolor='white', linewidth=1))
                    
                    elif sig_type == 'retest':
                        marker = 'R'
                        color = '#ffd54f' if sig_dir == 'bullish' else '#ba68c8'
                        y_pos = df.loc[sig_idx, 'low'] if sig_dir == 'bullish' else df.loc[sig_idx, 'high']
                        
                        ax1.text(sig_idx, y_pos, marker,
                                fontsize=7, color=color, weight='bold',
                                ha='center', va='bottom' if sig_dir == 'bullish' else 'top')
                    
                    elif sig_type == 'test':
                        marker = 'T'
                        color = '#42a5f5' if sig_dir == 'bullish' else '#e040fb'
                        y_pos = df.loc[sig_idx, 'low'] if sig_dir == 'bullish' else df.loc[sig_idx, 'high']
                        
                        ax1.text(sig_idx, y_pos, marker,
                                fontsize=7, color=color, weight='bold',
                                ha='center', va='bottom' if sig_dir == 'bullish' else 'top')
        
        # === ORDER BLOCKS (ICT) ===
        if ict_data:
            for ob in ict_data.get('order_blocks', []):
                ob_idx = ob.start_idx - (len(df) - 100)
                
                if 0 <= ob_idx < len(df):
                    if ob.is_bullish:
                        color = '#81c784'
                        edge = '#388e3c'
                        label = '+OB'
                    else:
                        color = '#e57373'
                        edge = '#c62828'
                        label = '-OB'
                    
                    # OB rectangle
                    ax1.add_patch(plt.Rectangle(
                        (ob_idx - 0.4, ob.bottom), 0.8, ob.top - ob.bottom,
                        facecolor=color, alpha=0.25,
                        edgecolor=edge, linewidth=1.5, zorder=4
                    ))
                    
                    # Label
                    ax1.text(ob_idx, ob.top if ob.is_bullish else ob.bottom,
                            label, fontsize=6, color=edge, weight='bold',
                            ha='center', va='bottom' if ob.is_bullish else 'top')
            
            # === FAIR VALUE GAPS - ONLY SIGNIFICANT ONES ===
            # Filter only non-mitigated FVG with minimum size
            significant_fvgs = [fvg for fvg in ict_data.get('fvgs', []) 
                               if not fvg.mitigated and 
                               (fvg.top - fvg.bottom) / fvg.bottom >= 0.003]  # Min 0.3% size
            
            for fvg in significant_fvgs[-10:]:
                fvg_idx_start = fvg.start_idx - (len(df) - 100)
                fvg_idx_end = min(fvg.end_idx - (len(df) - 100), len(df))
                
                if fvg_idx_end > 0 and fvg_idx_start < len(df):
                    if fvg.is_bullish:
                        color = '#66bb6a'
                        label = 'FVG+'
                    else:
                        color = '#ef5350'
                        label = 'FVG-'
                    
                    # FVG zone - more visible
                    ax1.plot([fvg_idx_start, fvg_idx_end], 
                            [fvg.top, fvg.top],
                            color=color, linestyle=':', linewidth=1.5, alpha=0.7)
                    ax1.plot([fvg_idx_start, fvg_idx_end], 
                            [fvg.bottom, fvg.bottom],
                            color=color, linestyle=':', linewidth=1.5, alpha=0.7)
                    
                    # Shaded area
                    ax1.fill_between([fvg_idx_start, fvg_idx_end],
                                    fvg.bottom, fvg.top,
                                    color=color, alpha=0.12, zorder=2)
                    
                    # Label only for recent FVG
                    if fvg_idx_end >= len(df) - 30:
                        mid_price = (fvg.top + fvg.bottom) / 2
                        ax1.text(fvg_idx_end + 0.5, mid_price, label,
                                fontsize=7, color=color, weight='bold',
                                bbox=dict(boxstyle='round,pad=0.2',
                                        facecolor='#0d1117', alpha=0.8))
            
            # === MARKET STRUCTURE (MSS/BOS) ===
            for struct in ict_data.get('structures', [])[-5:]:
                struct_idx = struct.index - (len(df) - 100)
                
                if 0 <= struct_idx < len(df):
                    label_text = struct.type  # MSS or BOS
                    
                    if struct.direction == 'bullish':
                        color = '#26a69a'
                        y_pos = struct.price * 1.005
                        va = 'bottom'
                    else:
                        color = '#ef5350'
                        y_pos = struct.price * 0.995
                        va = 'top'
                    
                    # Draw line at structure level
                    ax1.axhline(y=struct.price, 
                               color=color, linestyle=':', 
                               linewidth=1, alpha=0.5,
                               xmin=max(0, (struct_idx - 5) / len(df)),
                               xmax=min(1, (struct_idx + 5) / len(df)))
                    
                    # Label
                    ax1.text(struct_idx, y_pos, label_text,
                            fontsize=8, color='white', weight='bold',
                            ha='center', va=va,
                            bbox=dict(boxstyle='round,pad=0.3',
                                    facecolor=color, alpha=0.9,
                                    edgecolor='white', linewidth=1.5))
            
            # === LIQUIDITY LEVELS (BSL/SSL) - ENHANCED ===
            for liq in ict_data.get('liquidity_levels', [])[-8:]:
                liq_idx = liq.index - (len(df) - 100)
                
                if liq_idx >= 0:
                    if liq.is_buy_side:
                        color = '#ff6b00'  # Bright orange
                        label = 'BSL'
                        marker_symbol = '▲'
                    else:
                        color = '#00bcd4'  # Bright cyan
                        label = 'SSL'
                        marker_symbol = '▼'
                    
                    # Liquidity line - thicker and more visible
                    ax1.axhline(y=liq.price,
                               color=color, linestyle='--', 
                               linewidth=1.8, alpha=0.8,
                               xmin=max(0, liq_idx / len(df)),
                               xmax=1, zorder=6)
                    
                    # Label with marker
                    ax1.text(len(df) - 1, liq.price, f'{marker_symbol} {label}',
                            fontsize=7, color='white', weight='bold',
                            ha='left', va='center',
                            bbox=dict(boxstyle='round,pad=0.3',
                                    facecolor=color, alpha=0.95,
                                    edgecolor='white', linewidth=1.2))
                    
                    # Swept marker - larger and more visible
                    if liq.swept and liq_idx < len(df):
                        ax1.scatter(liq_idx, liq.price,
                                  marker='X', s=120, color=color, 
                                  linewidth=2.5, zorder=10,
                                  edgecolors='white')
            
            # === SWING POINTS ===
            for swing in ict_data.get('swing_highs', []):
                s_idx = swing.index - (len(df) - 100)
                if 0 <= s_idx < len(df):
                    ax1.scatter(s_idx, swing.price,
                               marker='v', s=40, color='#ef5350',
                               alpha=0.7, zorder=5)
            
            for swing in ict_data.get('swing_lows', []):
                s_idx = swing.index - (len(df) - 100)
                if 0 <= s_idx < len(df):
                    ax1.scatter(s_idx, swing.price,
                               marker='^', s=40, color='#26a69a',
                               alpha=0.7, zorder=5)
            
            # === PREMIUM/DISCOUNT ZONES ===
            prem_disc = ict_data.get('premium_discount')
            if prem_disc:
                # Equilibrium (50%)
                ax1.axhline(y=prem_disc.equilibrium,
                           color='#ffd54f', linestyle='-',
                           linewidth=1, alpha=0.5, zorder=1)
                ax1.text(2, prem_disc.equilibrium, 'EQ',
                        fontsize=6, color='#ffd54f')
                
                # Premium zone (above EQ)
                ax1.axhspan(prem_disc.equilibrium, prem_disc.premium_start,
                           color='#ef5350', alpha=0.04, zorder=1)
                
                # Discount zone (below EQ)
                ax1.axhspan(prem_disc.discount_end, prem_disc.equilibrium,
                           color='#26a69a', alpha=0.04, zorder=1)
        
        # === ENTRY/TP/SL MARKERS ===
        # Current price / Entry
        ax1.axhline(y=current_price, color='#1e88e5', 
                   linestyle='-', linewidth=2, alpha=0.8, zorder=6)
        ax1.text(len(df) * 0.15, current_price, 
                f'  ENTRY ${current_price:.2f}',
                fontsize=8, color='white', weight='bold',
                va='center',
                bbox=dict(boxstyle='round,pad=0.4',
                         facecolor='#1976d2', alpha=0.9,
                         edgecolor='white', linewidth=1.5))
        
        # Take Profit
        tp_pct = ((tp_price - current_price) / current_price) * 100
        ax1.axhline(y=tp_price, color='#388e3c',
                   linestyle='--', linewidth=2, alpha=0.8, zorder=6)
        ax1.text(len(df) * 0.15, tp_price,
                f'  TP ${tp_price:.2f} ({tp_pct:+.1f}%)',
                fontsize=8, color='white', weight='bold',
                va='center',
                bbox=dict(boxstyle='round,pad=0.4',
                         facecolor='#2e7d32', alpha=0.9,
                         edgecolor='white', linewidth=1.5))
        
        # Stop Loss
        sl_pct = ((sl_price - current_price) / current_price) * 100
        ax1.axhline(y=sl_price, color='#c62828',
                   linestyle='--', linewidth=2, alpha=0.8, zorder=6)
        ax1.text(len(df) * 0.15, sl_price,
                f'  SL ${sl_price:.2f} ({sl_pct:.1f}%)',
                fontsize=8, color='white', weight='bold',
                va='center',
                bbox=dict(boxstyle='round,pad=0.4',
                         facecolor='#c62828', alpha=0.9,
                         edgecolor='white', linewidth=1.5))
        
        # Signal marker
        signal_x = len(df) - 8
        signal_y = current_price
        
        if signal == 'BUY':
            ax1.text(signal_x, signal_y, '▲ BUY',
                    fontsize=10, color='white', weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5',
                             facecolor='#388e3c', alpha=0.9,
                             edgecolor='white', linewidth=1.5))
        elif signal == 'SELL':
            ax1.text(signal_x, signal_y, '▼ SELL',
                    fontsize=10, color='white', weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5',
                             facecolor='#c62828', alpha=0.9,
                             edgecolor='white', linewidth=1.5))
        
        # Watermark
        ax1.text(len(df) / 2, 
                (ax1.get_ylim()[0] + ax1.get_ylim()[1]) / 2,
                'LuxAlgo + ICT Bot',
                fontsize=18, color='#30363d', alpha=0.2,
                ha='center', va='center', rotation=0, weight='bold')
        
        # Styling
        ax1.tick_params(axis='x', colors='#8b949e', labelsize=8)
        ax1.tick_params(axis='y', colors='#8b949e', labelsize=9)
        ax_vol.tick_params(axis='x', colors='#8b949e', labelsize=8)
        ax_vol.tick_params(axis='y', colors='#8b949e', labelsize=7)
        
        for spine in ['bottom', 'top', 'left', 'right']:
            ax1.spines[spine].set_color('#30363d')
            ax_vol.spines[spine].set_color('#30363d')
        
        ax1.set_title(
            f'{symbol} - {timeframe.upper()} - LuxAlgo MTF + ICT Concepts - '
            f'{datetime.now().strftime("%Y-%m-%d %H:%M")}',
            fontsize=11, weight='normal', color='#c9d1d9'
        )
        ax1.set_ylabel('Price (USDT)', fontsize=9, color='#8b949e')
        ax_vol.set_ylabel('Volume', fontsize=8, color='#8b949e')
        
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.tight_layout()
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        logger.info(f"✅ Chart generated successfully for {symbol}")
        return buf
        
    except Exception as e:
        logger.error(f"Error generating LuxAlgo chart: {e}")
        import traceback
        traceback.print_exc()
        return None
