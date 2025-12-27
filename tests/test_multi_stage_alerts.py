"""
Unit tests for Phase 3 Multi-Stage Alerts System

Tests:
1. Trade ID generation (unique, format correct)
2. Stage detection (0-25%, 25-50%, etc.)
3. Halfway alert triggered at 25-50%
4. Approaching alert triggered at 50-75%
5. Final phase alert triggered at 85-100%
6. No duplicate alerts for same stage
7. Existing 80% TP alert still works
8. Feature flag disables multi-stage alerts
9. get_user_trades() returns correct trades
10. Message formatting correct (Bulgarian)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.trade_id_generator import TradeIDGenerator
from real_time_monitor import RealTimePositionMonitor, ALERT_STAGES


class TestTradeIDGenerator:
    """Test Trade ID generation"""
    
    def test_generate_format(self):
        """Test that generated IDs have correct format"""
        trade_id = TradeIDGenerator.generate('BTCUSDT', '4h')
        
        # Check format: #SYMBOL-YYYYMMDD-HHMMSS
        assert trade_id.startswith('#')
        parts = trade_id[1:].split('-')
        assert len(parts) == 3
        
        symbol, date_str, time_str = parts
        assert symbol == 'BTC'
        assert len(date_str) == 8  # YYYYMMDD
        assert len(time_str) == 6  # HHMMSS
    
    def test_generate_btc(self):
        """Test BTC symbol handling"""
        trade_id = TradeIDGenerator.generate('BTCUSDT')
        assert '#BTC-' in trade_id
    
    def test_generate_eth(self):
        """Test ETH symbol handling"""
        trade_id = TradeIDGenerator.generate('ETHUSDT')
        assert '#ETH-' in trade_id
    
    def test_generate_removes_usdt(self):
        """Test that USDT is removed from symbol"""
        trade_id = TradeIDGenerator.generate('SOLUSDT')
        assert 'USDT' not in trade_id
        assert '#SOL-' in trade_id
    
    def test_parse_valid_id(self):
        """Test parsing a valid trade ID"""
        trade_id = "#BTC-20251227-143022"
        result = TradeIDGenerator.parse(trade_id)
        
        assert result['symbol'] == 'BTC'
        assert result['date'] == '20251227'
        assert result['time'] == '143022'
        assert isinstance(result['datetime'], datetime)
    
    def test_parse_invalid_format(self):
        """Test parsing invalid format raises error"""
        with pytest.raises(ValueError):
            TradeIDGenerator.parse("invalid-format")
    
    def test_uniqueness(self):
        """Test that consecutive IDs are unique (due to timestamp)"""
        import time
        trade_id1 = TradeIDGenerator.generate('BTCUSDT')
        time.sleep(1)  # Wait 1 second
        trade_id2 = TradeIDGenerator.generate('BTCUSDT')
        
        assert trade_id1 != trade_id2


class TestRealTimeMonitor:
    """Test Real-Time Monitor multi-stage alerts"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Telegram bot"""
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def mock_ict_handler(self):
        """Create mock ICT 80 alert handler"""
        handler = Mock()
        handler.analyze_position = AsyncMock(return_value={
            'recommendation': 'HOLD',
            'confidence': 75,
            'reasoning': 'Test reasoning',
            'score_hold': 8,
            'score_close': 2,
            'warnings': []
        })
        return handler
    
    @pytest.fixture
    def monitor(self, mock_bot, mock_ict_handler):
        """Create RealTimePositionMonitor instance"""
        return RealTimePositionMonitor(
            bot=mock_bot,
            ict_80_handler=mock_ict_handler,
            owner_chat_id=12345,
            binance_price_url="https://api.binance.com/api/v3/ticker/price",
            binance_klines_url="https://api.binance.com/api/v3/klines"
        )
    
    def test_stage_detection_early(self, monitor):
        """Test stage detection for 0-25% progress"""
        stage = monitor._get_stage(15)
        assert stage == 'early'
    
    def test_stage_detection_halfway(self, monitor):
        """Test stage detection for 25-50% progress"""
        stage = monitor._get_stage(35)
        assert stage == 'halfway'
    
    def test_stage_detection_approaching(self, monitor):
        """Test stage detection for 50-75% progress"""
        stage = monitor._get_stage(60)
        assert stage == 'approaching'
    
    def test_stage_detection_eighty_pct(self, monitor):
        """Test stage detection for 75-85% progress"""
        stage = monitor._get_stage(80)
        assert stage == 'eighty_pct'
    
    def test_stage_detection_final(self, monitor):
        """Test stage detection for 85-100% progress"""
        stage = monitor._get_stage(92)
        assert stage == 'final'
    
    def test_stage_detection_completed(self, monitor):
        """Test stage detection for 100%+ progress"""
        stage = monitor._get_stage(105)
        assert stage == 'completed'
    
    def test_add_signal_creates_trade_id(self, monitor):
        """Test that add_signal creates a trade ID"""
        monitor.add_signal(
            signal_id='test123',
            symbol='BTCUSDT',
            signal_type='BUY',
            entry_price=50000,
            tp_price=52000,
            sl_price=49000,
            confidence=75,
            timeframe='4h',
            user_chat_id=12345
        )
        
        signal = monitor.monitored_signals['test123']
        assert 'trade_id' in signal
        assert signal['trade_id'].startswith('#')
        assert 'opened_at' in signal
        assert signal['last_alerted_stage'] is None
    
    def test_add_signal_preserves_existing_fields(self, monitor):
        """Test that add_signal preserves all existing fields"""
        monitor.add_signal(
            signal_id='test123',
            symbol='BTCUSDT',
            signal_type='BUY',
            entry_price=50000,
            tp_price=52000,
            sl_price=49000,
            confidence=75,
            timeframe='4h',
            user_chat_id=12345
        )
        
        signal = monitor.monitored_signals['test123']
        
        # Check all existing fields are present
        assert signal['symbol'] == 'BTCUSDT'
        assert signal['signal_type'] == 'BUY'
        assert signal['entry_price'] == 50000
        assert signal['tp_price'] == 52000
        assert signal['sl_price'] == 49000
        assert signal['confidence'] == 75
        assert signal['timeframe'] == '4h'
        assert signal['user_chat_id'] == 12345
        assert signal['tp_80_alerted'] == False
        assert signal['result_sent'] == False
    
    @patch('builtins.open', create=True)
    def test_is_multi_stage_enabled_true(self, mock_open, monitor):
        """Test feature flag check when enabled"""
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = '{"fundamental_analysis": {"multi_stage_alerts": true}}'
        mock_open.return_value = mock_file
        
        import json
        with patch('json.load', return_value={'fundamental_analysis': {'multi_stage_alerts': True}}):
            enabled = monitor._is_multi_stage_enabled()
            assert enabled == True
    
    @patch('builtins.open', create=True)
    def test_is_multi_stage_enabled_false(self, mock_open, monitor):
        """Test feature flag check when disabled"""
        import json
        with patch('json.load', return_value={'fundamental_analysis': {'multi_stage_alerts': False}}):
            enabled = monitor._is_multi_stage_enabled()
            assert enabled == False
    
    def test_get_user_trades_filters_by_user(self, monitor):
        """Test get_user_trades returns only user's trades"""
        # Add trades for different users
        monitor.add_signal('signal1', 'BTCUSDT', 'BUY', 50000, 52000, 49000, 75, '4h', 12345)
        monitor.add_signal('signal2', 'ETHUSDT', 'SELL', 3000, 2900, 3100, 70, '1h', 12345)
        monitor.add_signal('signal3', 'SOLUSDT', 'BUY', 100, 110, 95, 80, '15m', 99999)
        
        # Get trades for user 12345
        user_trades = monitor.get_user_trades(12345)
        
        assert len(user_trades) == 2
        symbols = [t['symbol'] for t in user_trades]
        assert 'BTCUSDT' in symbols
        assert 'ETHUSDT' in symbols
        assert 'SOLUSDT' not in symbols
    
    def test_get_user_trades_excludes_completed(self, monitor):
        """Test get_user_trades excludes completed trades"""
        monitor.add_signal('signal1', 'BTCUSDT', 'BUY', 50000, 52000, 49000, 75, '4h', 12345)
        
        # Mark as completed
        monitor.monitored_signals['signal1']['result_sent'] = True
        
        user_trades = monitor.get_user_trades(12345)
        assert len(user_trades) == 0
    
    def test_format_halfway_message_contains_required_fields(self, monitor):
        """Test halfway message format contains all required fields"""
        signal = {
            'trade_id': '#BTC-20251227-143022',
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000,
            'tp_price': 52000,
            'sl_price': 49000,
            'timeframe': '4h',
            'opened_at': datetime.now(timezone.utc)
        }
        
        recommendation = {
            'recommendation': 'HOLD',
            'confidence': 75,
            'reasoning': 'Test reasoning'
        }
        
        message = monitor._format_halfway_message(signal, 51000, 50, recommendation)
        
        # Check required fields in Bulgarian
        assert '#BTC-20251227-143022' in message
        assert 'BTCUSDT' in message
        assert 'BUY' in message
        assert '4h' in message
        assert 'HOLD' in message
        assert '50.0%' in message  # Progress
        assert 'ПОЛОВИН ПЪТ' in message  # Bulgarian for "halfway"
    
    def test_format_approaching_message_contains_required_fields(self, monitor):
        """Test approaching message format contains all required fields"""
        signal = {
            'trade_id': '#BTC-20251227-143022',
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000,
            'tp_price': 52000,
            'sl_price': 49000,
            'timeframe': '4h',
            'opened_at': datetime.now(timezone.utc)
        }
        
        recommendation = {
            'recommendation': 'HOLD',
            'confidence': 80,
            'reasoning': 'Test reasoning'
        }
        
        message = monitor._format_approaching_message(signal, 51500, 75, recommendation)
        
        # Check required fields
        assert '#BTC-20251227-143022' in message
        assert 'ПРИБЛИЖАВА ЦЕЛТА' in message  # Bulgarian for "approaching target"
        assert '75' in message  # Progress percentage
    
    def test_get_stage_buttons_creates_keyboard(self, monitor):
        """Test stage buttons creation"""
        keyboard = monitor._get_stage_buttons('signal123')
        
        assert keyboard is not None
        # Check that keyboard has buttons
        assert len(keyboard.inline_keyboard) > 0
        assert len(keyboard.inline_keyboard[0]) > 0


class TestStageAlertLogic:
    """Test multi-stage alert triggering logic"""
    
    @pytest.fixture
    def mock_bot(self):
        bot = Mock()
        bot.send_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def mock_ict_handler(self):
        handler = Mock()
        handler.analyze_position = AsyncMock(return_value={
            'recommendation': 'HOLD',
            'confidence': 75,
            'reasoning': 'Test reasoning',
            'score_hold': 8,
            'score_close': 2,
            'warnings': []
        })
        return handler
    
    @pytest.fixture
    def monitor(self, mock_bot, mock_ict_handler):
        return RealTimePositionMonitor(
            bot=mock_bot,
            ict_80_handler=mock_ict_handler,
            owner_chat_id=12345,
            binance_price_url="https://api.binance.com/api/v3/ticker/price",
            binance_klines_url="https://api.binance.com/api/v3/klines"
        )
    
    @pytest.mark.asyncio
    async def test_no_duplicate_alerts_same_stage(self, monitor):
        """Test that alerts are not sent twice for same stage"""
        signal = {
            'signal_id': 'test123',
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000,
            'tp_price': 52000,
            'sl_price': 49000,
            'confidence': 75,
            'timeframe': '4h',
            'user_chat_id': 12345,
            'last_alerted_stage': 'halfway',
            'opened_at': datetime.now(timezone.utc)
        }
        
        # Check stage alerts with same stage
        await monitor._check_stage_alerts('test123', signal, 51000, 35)
        
        # Should not send alert (already alerted for halfway)
        monitor.bot.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_alert_sent_for_new_stage(self, monitor, mock_bot):
        """Test that alert is sent when entering new stage"""
        signal = {
            'signal_id': 'test123',
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000,
            'tp_price': 52000,
            'sl_price': 49000,
            'confidence': 75,
            'timeframe': '4h',
            'user_chat_id': 12345,
            'last_alerted_stage': None,
            'opened_at': datetime.now(timezone.utc),
            'trade_id': '#BTC-20251227-143022'
        }
        
        # Mock fetch_klines to return empty list (no ICT analysis)
        monitor._fetch_klines = AsyncMock(return_value=[])
        
        # Check stage alerts - should trigger halfway alert
        await monitor._check_stage_alerts('test123', signal, 51000, 35)
        
        # Should send alert for halfway stage
        mock_bot.send_message.assert_called_once()
        assert signal['last_alerted_stage'] == 'halfway'


def test_alert_stages_constant():
    """Test that ALERT_STAGES constant is properly defined"""
    assert 'early' in ALERT_STAGES
    assert 'halfway' in ALERT_STAGES
    assert 'approaching' in ALERT_STAGES
    assert 'eighty_pct' in ALERT_STAGES
    assert 'final' in ALERT_STAGES
    
    # Check ranges
    assert ALERT_STAGES['early'] == (0, 25)
    assert ALERT_STAGES['halfway'] == (25, 50)
    assert ALERT_STAGES['approaching'] == (50, 75)
    assert ALERT_STAGES['eighty_pct'] == (75, 85)
    assert ALERT_STAGES['final'] == (85, 100)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
