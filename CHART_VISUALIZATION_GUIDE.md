# 📊 ICT Chart Visualization System

## Overview

The ICT Chart Visualization System provides professional, color-coded charts for ICT (Inner Circle Trader) signals with all zones, levels, and indicators clearly displayed.

## Features

### 🎨 Visual Elements

1. **OHLC Candlestick Chart**
   - Green candles: Bullish (close > open)
   - Red candles: Bearish (close < open)
   - High-low wicks for price range

2. **ICT Zones (Color-Coded)**
   - 🐋 **Whale Order Blocks**: Green (bullish) / Red (bearish)
     - Solid borders, 15% alpha fill
     - Extended to chart edge if active
   
   - 💥 **Breaker Blocks**: Blue (bullish) / Orange (bearish)
     - Dashed borders, 12% alpha fill
     - Indicates failed support/resistance
   
   - 🎯 **Mitigation Blocks**: Teal (bullish) / Purple (bearish)
     - Dotted borders, 10% alpha fill
     - Shows retest zones
   
   - ⚡ **SIBI/SSIB Zones**: Yellow (SIBI) / Dark Gray (SSIB)
     - Solid borders, 20% alpha fill
     - Institutional order flow indicators
   
   - 📊 **Fair Value Gaps (FVG)**: Light Green (bullish) / Light Red (bearish)
     - No border, 30% alpha fill
     - Price imbalance areas
   
   - 💧 **Liquidity Zones**: Dark Teal (buy) / Dark Red (sell)
     - Dash-dot horizontal lines
     - Buy/Sell side liquidity levels

3. **Entry/Exit Levels**
   - **Entry**: Blue solid horizontal line
   - **Stop Loss**: Red dashed horizontal line
   - **Take Profit**: Green dashed horizontal line

4. **Volume Subplot**
   - Bar chart below main price chart
   - Green bars: Volume on up candles
   - Red bars: Volume on down candles

5. **Signal Info Box**
   - Top-left corner
   - Shows: Signal type, Confidence %, Bias
   - Wheat-colored background

6. **Legend**
   - Automatic deduplication
   - Upper-left placement
   - Shows all active zone types

## Usage

### Command Syntax

```
/ict <SYMBOL> <TIMEFRAME>
```

Examples:
```
/ict BTC 4H     # Bitcoin 4-hour chart
/ict ETH 1H     # Ethereum 1-hour chart
/ict SOL 1D     # Solana daily chart
```

### Output

The bot sends two messages:
1. **Text Analysis**: Detailed signal information in Markdown format
2. **Chart Image**: PNG visualization with all ICT zones

If chart generation fails, only text analysis is sent with a warning message.

## Configuration

Edit `config/feature_flags.json`:

```json
{
  "use_chart_visualization": true,    // Enable/disable charts
  "chart_style": "professional",      // Style: professional or dark
  "chart_dpi": 100,                   // Chart resolution (DPI)
  "max_zones_per_chart": 10,          // Limit zones displayed
  "include_volume_subplot": true,     // Show/hide volume
  "cache_charts": false               // Cache generated charts
}
```

## Technical Details

### Performance

- **Generation Time**: < 1 second (typically 0.7-0.8s)
- **Chart Size**: 75-100 KB (PNG format)
- **Resolution**: 1400x1000 pixels (14x10 inches @ 100 DPI)
- **Memory Usage**: ~5-10 MB during generation

### Dependencies

- `matplotlib>=3.7.0` - Chart generation
- `pillow>=10.0.0` - Image processing (via matplotlib)
- `numpy>=1.24.0` - Numerical operations
- `pandas>=2.3.0` - Data handling

### Architecture

**Files:**
- `chart_generator.py` - Main chart generation logic
- `chart_annotator.py` - Labels and annotations (optional)
- `visualization_config.py` - Configuration constants
- `config/feature_flags.json` - Runtime feature flags

**Classes:**
- `ChartGenerator` - Main chart generation class
  - `generate()` - Generate complete chart
  - `_plot_candlesticks()` - Draw OHLC candles
  - `_plot_whale_blocks()` - Draw whale zones
  - `_plot_breaker_blocks()` - Draw breaker zones
  - `_plot_mitigation_blocks()` - Draw mitigation zones
  - `_plot_sibi_ssib_zones()` - Draw SIBI/SSIB zones
  - `_plot_fvg_zones()` - Draw FVG zones
  - `_plot_liquidity_zones()` - Draw liquidity lines
  - `_plot_entry_exit()` - Draw entry/SL/TP levels
  - `_plot_volume()` - Draw volume subplot
  - `_apply_styling()` - Apply professional styling
  - `_add_info_box()` - Add signal info box

### Error Handling

The system includes graceful error handling:

1. **Missing Dependencies**: Falls back to text-only output
2. **Chart Generation Errors**: Sends text with error warning
3. **Invalid Data**: Logs error and returns None
4. **Telegram Upload Errors**: Retries with error message

### Color Scheme

```python
COLORS = {
    'whale_bullish': '#2ECC71',      # Green
    'whale_bearish': '#E74C3C',      # Red
    'breaker_bullish': '#3498DB',    # Blue
    'breaker_bearish': '#E67E22',    # Orange
    'mitigation_bullish': '#1ABC9C', # Teal
    'mitigation_bearish': '#9B59B6', # Purple
    'sibi': '#F39C12',               # Yellow
    'ssib': '#34495E',               # Dark gray
    'fvg_bullish': '#2ECC71',        # Green (with alpha)
    'fvg_bearish': '#E74C3C',        # Red (with alpha)
    'liquidity_buy': '#16A085',      # Dark teal
    'liquidity_sell': '#C0392B',     # Dark red
    'candle_up': '#26A69A',          # Teal
    'candle_down': '#EF5350'         # Red
}
```

## Testing

Run tests to verify functionality:

```bash
# Basic functionality test
python3 /tmp/test_chart_generation.py

# Performance test
python3 /tmp/test_performance.py

# Integration test
python3 /tmp/test_integration.py

# Fallback test
python3 /tmp/test_fallback.py
```

Expected results:
- ✅ Chart generation in < 1 second
- ✅ Chart size 75-100 KB
- ✅ All zone types render correctly
- ✅ Graceful fallback on errors

## Troubleshooting

### Chart not generating

1. Check if matplotlib is installed:
   ```bash
   pip3 show matplotlib
   ```

2. Verify feature flag is enabled:
   ```bash
   cat config/feature_flags.json | grep use_chart_visualization
   ```

3. Check logs for errors:
   ```bash
   tail -f bot.log | grep -i "chart"
   ```

### Charts look wrong

1. Verify data format:
   - DataFrame must have: timestamp, open, high, low, close, volume
   - All price columns should be float type
   - Timestamp should be datetime type

2. Check signal structure:
   - Signal must have all required ICT zone lists
   - Zones should have correct field names (price_low, price_high, etc.)

3. Try regenerating with debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Performance issues

1. Reduce chart DPI in config:
   ```json
   "chart_dpi": 75
   ```

2. Limit number of candles:
   ```python
   df = df.tail(100)  # Last 100 candles only
   ```

3. Enable chart caching:
   ```json
   "cache_charts": true
   ```

## Future Enhancements

- [ ] Dark mode color scheme implementation
- [ ] Custom color themes
- [ ] Interactive charts (plotly integration)
- [ ] Chart annotation system integration
- [ ] Multi-panel layouts (HTF + LTF)
- [ ] Chart caching system
- [ ] Export to different formats (SVG, PDF)
- [ ] Mobile-optimized layouts

## Support

For issues or questions:
- Open an issue on GitHub
- Check bot logs: `bot.log`
- Review feature flags: `config/feature_flags.json`

---

**Version:** 1.0  
**Last Updated:** December 18, 2025  
**Tested:** Python 3.12, matplotlib 3.10.7
