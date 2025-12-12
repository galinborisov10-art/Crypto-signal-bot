"""
📊 GRAPH ENGINE - ICT Visualization System
Generates interactive charts with ICT elements marked

Visualizes:
- 🟡 Whale Order Blocks (Yellow)
- 🔵 IBSL - Buy-Side Liquidity (Blue)
- 🔴 ISSL - Sell-Side Liquidity (Red)
- 🟢 Smart Money Zones - Order Blocks (Green)
- 🟠 Fair Value Gaps (Orange)
- 📍 Entry/Exit points
- 📈 Multi-timeframe alignment indicators
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ICTGraphEngine:
    """
    Interactive Chart Generator with ICT Concepts
    Creates professional trading charts with all ICT elements marked
    """
    
    def __init__(self, theme: str = 'dark'):
        """
        Initialize Graph Engine
        
        Args:
            theme: 'dark' or 'light'
        """
        self.theme = theme
        self.colors = self._get_color_scheme()
        
    def _get_color_scheme(self) -> Dict[str, str]:
        """Get color scheme based on theme"""
        if self.theme == 'dark':
            return {
                'bg': '#0e1621',
                'grid': '#1e2937',
                'text': '#e5e7eb',
                'candle_up': '#10b981',
                'candle_down': '#ef4444',
                'whale': '#fbbf24',  # Yellow
                'ibsl': '#3b82f6',   # Blue
                'issl': '#ef4444',   # Red
                'ob': '#10b981',     # Green
                'fvg': '#f97316',    # Orange
                'entry': '#8b5cf6',  # Purple
                'sl': '#dc2626',
                'tp': '#059669'
            }
        else:
            return {
                'bg': '#ffffff',
                'grid': '#f3f4f6',
                'text': '#1f2937',
                'candle_up': '#10b981',
                'candle_down': '#ef4444',
                'whale': '#fbbf24',
                'ibsl': '#3b82f6',
                'issl': '#ef4444',
                'ob': '#10b981',
                'fvg': '#f97316',
                'entry': '#8b5cf6',
                'sl': '#dc2626',
                'tp': '#059669'
            }
    
    def create_ict_chart(
        self,
        df: pd.DataFrame,
        whale_blocks: List[Dict] = None,
        liquidity_pools: Dict[str, List] = None,
        order_blocks: List[Dict] = None,
        fvgs: List[Dict] = None,
        signal: Optional[Dict] = None,
        title: str = "ICT Analysis Chart",
        show_volume: bool = True
    ) -> go.Figure:
        """
        Create comprehensive ICT chart
        
        Args:
            df: OHLCV dataframe
            whale_blocks: Whale order blocks
            liquidity_pools: Dict with IBSL and ISSL pools
            order_blocks: Smart money order blocks
            fvgs: Fair value gaps
            signal: Trading signal with entry/sl/tp
            title: Chart title
            show_volume: Show volume subplot
            
        Returns:
            Plotly figure object
        """
        logger.info(f"Creating ICT chart: {title}")
        
        # Create subplots
        if show_volume:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.7, 0.3],
                subplot_titles=(title, 'Volume')
            )
        else:
            fig = go.Figure()
        
        # Add candlesticks
        self._add_candlesticks(fig, df, row=1)
        
        # Add Whale Order Blocks (🟡 Yellow)
        if whale_blocks:
            self._add_whale_blocks(fig, whale_blocks, row=1)
        
        # Add Internal Liquidity Pools
        if liquidity_pools:
            # IBSL (🔵 Blue)
            if 'IBSL' in liquidity_pools:
                self._add_ibsl_zones(fig, liquidity_pools['IBSL'], row=1)
            # ISSL (🔴 Red)
            if 'ISSL' in liquidity_pools:
                self._add_issl_zones(fig, liquidity_pools['ISSL'], row=1)
        
        # Add Smart Money Order Blocks (🟢 Green)
        if order_blocks:
            self._add_order_blocks(fig, order_blocks, row=1)
        
        # Add Fair Value Gaps (🟠 Orange)
        if fvgs:
            self._add_fvgs(fig, fvgs, row=1)
        
        # Add Trading Signal (Entry/SL/TP)
        if signal:
            self._add_signal_markers(fig, signal, df, row=1)
        
        # Add Volume
        if show_volume and 'volume' in df.columns:
            self._add_volume(fig, df, row=2)
        
        # Update layout
        self._update_layout(fig, title, show_volume)
        
        logger.info("Chart created successfully")
        return fig
    
    def _add_candlesticks(self, fig: go.Figure, df: pd.DataFrame, row: int):
        """Add candlestick chart"""
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color=self.colors['candle_up'],
                decreasing_line_color=self.colors['candle_down'],
                showlegend=False
            ),
            row=row, col=1
        )
    
    def _add_whale_blocks(self, fig: go.Figure, whale_blocks: List[Dict], row: int):
        """Add Whale Order Blocks (🟡 Yellow zones)"""
        for wb in whale_blocks:
            # Draw rectangle
            fig.add_shape(
                type="rect",
                x0=wb.get('start_time', wb.get('timestamp')),
                x1=wb.get('end_time', df.index[-1] if hasattr(df, 'index') else datetime.now()),
                y0=wb['zone_low'],
                y1=wb['zone_high'],
                fillcolor=self.colors['whale'],
                opacity=0.2,
                line=dict(color=self.colors['whale'], width=1),
                layer='below',
                row=row, col=1
            )
            
            # Add annotation
            fig.add_annotation(
                x=wb.get('timestamp'),
                y=wb['price_level'],
                text=f"🐋 Whale Block<br>Confidence: {wb.get('confidence', 0)}%",
                showarrow=True,
                arrowhead=2,
                arrowcolor=self.colors['whale'],
                bgcolor=self.colors['whale'],
                opacity=0.8,
                font=dict(size=10, color='black'),
                row=row, col=1
            )
    
    def _add_ibsl_zones(self, fig: go.Figure, ibsl_pools: List[Dict], row: int):
        """Add Internal Buy-Side Liquidity zones (🔵 Blue)"""
        for pool in ibsl_pools:
            if pool.get('still_active', True):
                # Draw horizontal line
                fig.add_shape(
                    type="line",
                    x0=pool.get('first_touch'),
                    x1=pool.get('last_touch'),
                    y0=pool['price_level'],
                    y1=pool['price_level'],
                    line=dict(
                        color=self.colors['ibsl'],
                        width=2,
                        dash='dash'
                    ),
                    row=row, col=1
                )
                
                # Add annotation
                fig.add_annotation(
                    x=pool.get('last_touch'),
                    y=pool['price_level'],
                    text=f"💧 IBSL<br>Strength: {pool.get('strength', 0)}%<br>Sweep: {pool.get('sweep_probability', 0):.0f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=self.colors['ibsl'],
                    bgcolor=self.colors['ibsl'],
                    opacity=0.8,
                    font=dict(size=9, color='white'),
                    ax=30,
                    ay=-30,
                    row=row, col=1
                )
    
    def _add_issl_zones(self, fig: go.Figure, issl_pools: List[Dict], row: int):
        """Add Internal Sell-Side Liquidity zones (🔴 Red)"""
        for pool in issl_pools:
            if pool.get('still_active', True):
                # Draw horizontal line
                fig.add_shape(
                    type="line",
                    x0=pool.get('first_touch'),
                    x1=pool.get('last_touch'),
                    y0=pool['price_level'],
                    y1=pool['price_level'],
                    line=dict(
                        color=self.colors['issl'],
                        width=2,
                        dash='dash'
                    ),
                    row=row, col=1
                )
                
                # Add annotation
                fig.add_annotation(
                    x=pool.get('last_touch'),
                    y=pool['price_level'],
                    text=f"💧 ISSL<br>Strength: {pool.get('strength', 0)}%<br>Sweep: {pool.get('sweep_probability', 0):.0f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=self.colors['issl'],
                    bgcolor=self.colors['issl'],
                    opacity=0.8,
                    font=dict(size=9, color='white'),
                    ax=30,
                    ay=30,
                    row=row, col=1
                )
    
    def _add_order_blocks(self, fig: go.Figure, order_blocks: List[Dict], row: int):
        """Add Smart Money Order Blocks (🟢 Green zones)"""
        for ob in order_blocks:
            if not ob.get('mitigated', False):
                color = self.colors['ob'] if ob['direction'] == 'bullish' else self.colors['issl']
                
                # Draw rectangle
                fig.add_shape(
                    type="rect",
                    x0=ob.get('formed_at', ob.get('timestamp')),
                    x1=ob.get('end_time', datetime.now()),
                    y0=ob['price_low'],
                    y1=ob['price_high'],
                    fillcolor=color,
                    opacity=0.15,
                    line=dict(color=color, width=1),
                    layer='below',
                    row=row, col=1
                )
                
                # Add annotation
                direction_emoji = "🟢" if ob['direction'] == 'bullish' else "🔴"
                fig.add_annotation(
                    x=ob.get('timestamp'),
                    y=(ob['price_low'] + ob['price_high']) / 2,
                    text=f"{direction_emoji} {ob['zone_type']}<br>Strength: {ob.get('strength', 0)}%",
                    showarrow=False,
                    bgcolor=color,
                    opacity=0.7,
                    font=dict(size=8, color='white'),
                    row=row, col=1
                )
    
    def _add_fvgs(self, fig: go.Figure, fvgs: List[Dict], row: int):
        """Add Fair Value Gaps (🟠 Orange zones)"""
        for fvg in fvgs:
            if not fvg.get('filled', False):
                # Draw rectangle
                fig.add_shape(
                    type="rect",
                    x0=fvg.get('start_time', fvg.get('timestamp')),
                    x1=fvg.get('end_time', datetime.now()),
                    y0=fvg['gap_low'],
                    y1=fvg['gap_high'],
                    fillcolor=self.colors['fvg'],
                    opacity=0.1,
                    line=dict(color=self.colors['fvg'], width=1, dash='dot'),
                    layer='below',
                    row=row, col=1
                )
                
                # Add annotation
                fig.add_annotation(
                    x=fvg.get('timestamp'),
                    y=(fvg['gap_low'] + fvg['gap_high']) / 2,
                    text=f"🌊 FVG",
                    showarrow=False,
                    bgcolor=self.colors['fvg'],
                    opacity=0.6,
                    font=dict(size=8, color='white'),
                    row=row, col=1
                )
    
    def _add_signal_markers(self, fig: go.Figure, signal: Dict, df: pd.DataFrame, row: int):
        """Add trading signal markers (Entry/SL/TP)"""
        entry_time = signal.get('timestamp', df.index[-1])
        entry_price = signal['entry_price']
        
        # Entry point
        fig.add_trace(
            go.Scatter(
                x=[entry_time],
                y=[entry_price],
                mode='markers+text',
                marker=dict(
                    size=15,
                    color=self.colors['entry'],
                    symbol='star',
                    line=dict(color='white', width=2)
                ),
                text=['ENTRY'],
                textposition='top center',
                textfont=dict(size=12, color=self.colors['entry']),
                name='Entry',
                showlegend=True
            ),
            row=row, col=1
        )
        
        # Stop Loss line
        fig.add_shape(
            type="line",
            x0=df.index[0],
            x1=df.index[-1],
            y0=signal['sl_price'],
            y1=signal['sl_price'],
            line=dict(
                color=self.colors['sl'],
                width=2,
                dash='dash'
            ),
            row=row, col=1
        )
        
        fig.add_annotation(
            x=df.index[-1],
            y=signal['sl_price'],
            text=f"🛑 SL: {signal['sl_price']:.2f}",
            showarrow=False,
            bgcolor=self.colors['sl'],
            font=dict(size=10, color='white'),
            xanchor='left',
            row=row, col=1
        )
        
        # Take Profit lines
        tp_prices = signal.get('tp_price', [])
        if not isinstance(tp_prices, list):
            tp_prices = [tp_prices]
        
        for i, tp in enumerate(tp_prices, 1):
            fig.add_shape(
                type="line",
                x0=df.index[0],
                x1=df.index[-1],
                y0=tp,
                y1=tp,
                line=dict(
                    color=self.colors['tp'],
                    width=2,
                    dash='dot'
                ),
                row=row, col=1
            )
            
            fig.add_annotation(
                x=df.index[-1],
                y=tp,
                text=f"🎯 TP{i}: {tp:.2f}",
                showarrow=False,
                bgcolor=self.colors['tp'],
                font=dict(size=10, color='white'),
                xanchor='left',
                row=row, col=1
            )
    
    def _add_volume(self, fig: go.Figure, df: pd.DataFrame, row: int):
        """Add volume bars"""
        colors = [
            self.colors['candle_up'] if close > open_ else self.colors['candle_down']
            for close, open_ in zip(df['close'], df['open'])
        ]
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                marker_color=colors,
                name='Volume',
                showlegend=False
            ),
            row=row, col=1
        )
    
    def _update_layout(self, fig: go.Figure, title: str, show_volume: bool):
        """Update chart layout"""
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=20, color=self.colors['text'])
            ),
            plot_bgcolor=self.colors['bg'],
            paper_bgcolor=self.colors['bg'],
            font=dict(color=self.colors['text']),
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=800 if show_volume else 600
        )
        
        # Update axes
        fig.update_xaxes(
            gridcolor=self.colors['grid'],
            showgrid=True,
            zeroline=False
        )
        
        fig.update_yaxes(
            gridcolor=self.colors['grid'],
            showgrid=True,
            zeroline=False
        )
    
    def create_mtf_dashboard(
        self,
        df_1d: pd.DataFrame,
        df_4h: pd.DataFrame,
        df_1h: pd.DataFrame,
        analysis: Dict[str, Any],
        title: str = "Multi-Timeframe ICT Dashboard"
    ) -> go.Figure:
        """
        Create multi-timeframe dashboard with 1D, 4H, 1H charts
        
        Args:
            df_1d: 1D OHLCV data
            df_4h: 4H OHLCV data
            df_1h: 1H OHLCV data
            analysis: Complete MTF analysis results
            title: Dashboard title
            
        Returns:
            Plotly figure with 3 subplots
        """
        logger.info("Creating MTF dashboard")
        
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=False,
            vertical_spacing=0.05,
            subplot_titles=('1D - HTF Bias', '4H - MTF Structure', '1H - LTF Entry'),
            row_heights=[0.33, 0.33, 0.34]
        )
        
        # Add 1D chart
        self._add_candlesticks(fig, df_1d, row=1)
        
        # Add 4H chart
        self._add_candlesticks(fig, df_4h, row=2)
        
        # Add 1H chart with full ICT markup
        self._add_candlesticks(fig, df_1h, row=3)
        
        # Add ICT elements to 1H
        if 'order_blocks' in analysis:
            for ob in analysis['order_blocks']:
                self._add_order_blocks(fig, [ob], row=3)
        
        if 'signal' in analysis:
            self._add_signal_markers(fig, analysis['signal'], df_1h, row=3)
        
        # Update layout
        fig.update_layout(
            title=dict(text=title, font=dict(size=24, color=self.colors['text'])),
            plot_bgcolor=self.colors['bg'],
            paper_bgcolor=self.colors['bg'],
            font=dict(color=self.colors['text']),
            height=1200,
            showlegend=True
        )
        
        fig.update_xaxes(gridcolor=self.colors['grid'], showgrid=True)
        fig.update_yaxes(gridcolor=self.colors['grid'], showgrid=True)
        
        logger.info("MTF dashboard created")
        return fig
    
    def save_chart(self, fig: go.Figure, filename: str, format: str = 'html'):
        """
        Save chart to file
        
        Args:
            fig: Plotly figure
            filename: Output filename
            format: 'html', 'png', 'jpeg', 'svg'
        """
        try:
            if format == 'html':
                fig.write_html(filename)
            else:
                fig.write_image(filename, format=format)
            
            logger.info(f"Chart saved: {filename}")
        except Exception as e:
            logger.error(f"Failed to save chart: {e}")


# Example usage
if __name__ == "__main__":
    print("ICT Graph Engine initialized!")
    print("Ready to generate professional trading charts")
    print("Total lines: 500+")
