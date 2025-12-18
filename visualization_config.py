"""
Visualization Configuration
Settings for chart generation and styling.
"""

# Chart dimensions
CHART_WIDTH = 14
CHART_HEIGHT = 10
CHART_DPI = 100

# Color schemes
COLOR_SCHEMES = {
    'professional': {
        'background': '#FFFFFF',
        'grid': '#E0E0E0',
        'text': '#2C3E50',
        'candle_up': '#26A69A',
        'candle_down': '#EF5350',
        'whale_bullish': '#2ECC71',
        'whale_bearish': '#E74C3C',
        'breaker_bullish': '#3498DB',
        'breaker_bearish': '#E67E22',
        'mitigation_bullish': '#1ABC9C',
        'mitigation_bearish': '#9B59B6',
        'sibi': '#F39C12',
        'ssib': '#34495E',
        'fvg_bullish': '#2ECC71',
        'fvg_bearish': '#E74C3C',
        'liquidity_buy': '#16A085',
        'liquidity_sell': '#C0392B'
    },
    'dark': {
        'background': '#1E1E1E',
        'grid': '#3E3E3E',
        'text': '#FFFFFF',
        'candle_up': '#4CAF50',
        'candle_down': '#F44336',
        'whale_bullish': '#66BB6A',
        'whale_bearish': '#EF5350',
        'breaker_bullish': '#42A5F5',
        'breaker_bearish': '#FF7043',
        'mitigation_bullish': '#26C6DA',
        'mitigation_bearish': '#AB47BC',
        'sibi': '#FFCA28',
        'ssib': '#78909C',
        'fvg_bullish': '#66BB6A',
        'fvg_bearish': '#EF5350',
        'liquidity_buy': '#00897B',
        'liquidity_sell': '#D32F2F'
    }
}

# Annotation settings
ANNOTATION_FONT_SIZE = 8
LABEL_FONT_SIZE = 9
TITLE_FONT_SIZE = 16

# Zone display limits
MAX_WHALE_BLOCKS_DISPLAY = 3
MAX_BREAKER_BLOCKS_DISPLAY = 2
MAX_MITIGATION_BLOCKS_DISPLAY = 2
MAX_SIBI_SSIB_DISPLAY = 2
MAX_FVG_DISPLAY = 5
