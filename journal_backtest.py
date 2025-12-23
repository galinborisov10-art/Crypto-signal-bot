"""
🔍 JOURNAL BACKTEST ENGINE - READ-ONLY MODE
============================================

CRITICAL RULES FOR THIS FILE:
1. ✅ READ-ONLY ACCESS to trading_journal.json
2. ❌ ZERO MODIFICATIONS to ML/ICT logic
3. ❌ ZERO WRITES to existing data files
4. ✅ ONLY ANALYZE and REPORT results

FORBIDDEN OPERATIONS:
- Writing to trading_journal.json
- Modifying ML models
- Changing ICT parameters
- Altering signal generation logic
- Updating any existing configuration

ALLOWED OPERATIONS:
- Reading from trading_journal.json
- Computing statistics (win rate, P/L, etc.)
- Generating reports
- Comparing ML vs Classical performance
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JournalBacktestEngine:
    """
    Backtest engine that ONLY reads historical trade data
    and provides statistical analysis.

    FORBIDDEN OPERATIONS:
    - Writing to trading_journal.json
    - Modifying ML models
    - Changing ICT parameters
    - Altering signal generation logic
    - Updating any existing configuration

    ALLOWED OPERATIONS:
    - Reading from trading_journal.json
    - Computing statistics (win rate, P/L, etc.)
    - Generating reports
    - Comparing ML vs Classical performance
    """

    def __init__(self, journal_path: Optional[str] = None):
        """
        Initialize backtest engine in READ-ONLY mode

        Args:
            journal_path: Path to trading_journal.json (optional, auto-detects if None)
        """
        # Auto-detect base path (Codespace vs Server)
        if os.path.exists('/root/Crypto-signal-bot'):
            base_path = '/root/Crypto-signal-bot'
        else:
            base_path = '/workspaces/Crypto-signal-bot'

        # Set journal path
        if journal_path is None:
            self.journal_path = os.path.join(base_path, 'trading_journal.json')
        else:
            self.journal_path = journal_path

        logger.info("🔍 Backtest engine initialized (READ-ONLY mode)")
        logger.info("📁 Journal path: %s", self.journal_path)

    def run_backtest(
        self,
        days: int = 30,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze historical trades from journal (READ-ONLY)

        Args:
            days: Number of days to analyze (default: 30)
            symbol: Filter by specific symbol (optional, e.g., 'BTCUSDT')
            timeframe: Filter by specific timeframe (optional, e.g., '1h', '4h')

        Returns:
            Dict with comprehensive backtest results including:
            - overall: Overall win rate, total P/L, profit factor
            - ml_vs_classical: ML vs Classical comparison
            - by_symbol: Per-symbol breakdown
            - by_timeframe: Per-timeframe breakdown
            - top_performers: Best performing symbols
            - worst_performers: Worst performing symbols
            - summary: Human-readable summary

        MUST NOT:
        - Modify journal data
        - Retrain ML models
        - Change ICT parameters
        - Alter signal confidence
        """
        logger.info(f"🔍 Starting backtest analysis: {days} days, symbol={symbol}, timeframe={timeframe}")

        try:
            # Load trades (READ-ONLY)
            trades = self._load_trades(days, symbol, timeframe)

            if not trades:
                return {
                    'error': 'No trades found matching criteria',
                    'days': days,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'total_trades': 0
                }

            # Calculate comprehensive statistics
            overall_stats = self._calculate_stats(trades)

            # Compare ML vs Classical performance
            ml_comparison = self._compare_ml_vs_classical(trades)

            # Breakdown by symbol
            symbol_breakdown = self._breakdown_by_symbol(trades)

            # Breakdown by timeframe
            timeframe_breakdown = self._breakdown_by_timeframe(trades)

            # Identify top and worst performers
            top_performers, worst_performers = self._identify_performers(symbol_breakdown)

            # Build comprehensive results
            results = {
                'success': True,
                'days': days,
                'symbol_filter': symbol,
                'timeframe_filter': timeframe,
                'total_trades': len(trades),
                'overall': overall_stats,
                'ml_vs_classical': ml_comparison,
                'by_symbol': symbol_breakdown,
                'by_timeframe': timeframe_breakdown,
                'top_performers': top_performers,
                'worst_performers': worst_performers,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✅ Backtest analysis complete: {len(trades)} trades analyzed")
            return results

        except FileNotFoundError:
            logger.error(f"❌ Trading journal not found: {self.journal_path}")
            return {
                'error': f'Trading journal not found at {self.journal_path}',
                'hint': 'Journal will be created automatically when trades are recorded'
            }
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in trading journal: {e}")
            return {
                'error': 'Trading journal contains invalid JSON',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"❌ Backtest analysis error: {e}", exc_info=True)
            return {
                'error': f'Backtest analysis failed: {str(e)}',
                'type': type(e).__name__
            }

    def _load_trades(
        self,
        days: int,
        symbol: Optional[str],
        timeframe: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Load trades from journal (READ-ONLY) - NEVER write

        Args:
            days: Number of days to look back
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter

        Returns:
            List of trade dictionaries matching criteria

        Raises:
            FileNotFoundError: If journal file doesn't exist

        CRITICAL: This function ONLY reads, NEVER writes
        """
        # Check if journal exists
        if not os.path.exists(self.journal_path):
            logger.warning(f"⚠️ Trading journal not found: {self.journal_path}")
            raise FileNotFoundError(f"Trading journal not found: {self.journal_path}")

        # Load journal (READ-ONLY)
        with open(self.journal_path, 'r', encoding='utf-8') as f:
            journal = json.load(f)

        # Extract trades
        all_trades = journal.get('trades', [])

        if not all_trades:
            logger.warning("⚠️ No trades found in journal")
            return []

        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Filter trades
        filtered_trades = []
        for trade in all_trades:
            # Parse timestamp
            try:
                trade_time = datetime.fromisoformat(trade.get('timestamp', '').replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Skip trades with invalid timestamps
                continue

            # Check if within date range
            if trade_time < cutoff_date:
                continue

            # Apply symbol filter
            if symbol and trade.get('symbol', '').upper() != symbol.upper():
                continue

            # Apply timeframe filter
            if timeframe and trade.get('timeframe', '').lower() != timeframe.lower():
                continue

            # Only include completed trades (with outcomes)
            if trade.get('outcome') in ['WIN', 'LOSS', 'SUCCESS', 'FAILED']:
                filtered_trades.append(trade)

        logger.info(f"📊 Loaded {len(filtered_trades)} trades (from {len(all_trades)} total)")
        return filtered_trades

    def _calculate_stats(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics from trades

        Args:
            trades: List of trade dictionaries

        Returns:
            Dict with overall statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0
            }

        # Count wins and losses
        wins = 0
        losses = 0
        total_pnl = 0.0
        win_amounts = []
        loss_amounts = []

        for trade in trades:
            outcome = trade.get('outcome', '').upper()
            pnl = trade.get('profit_loss_pct', 0.0)

            # Normalize outcomes
            if outcome in ['WIN', 'SUCCESS']:
                wins += 1
                total_pnl += pnl
                win_amounts.append(pnl)
            elif outcome in ['LOSS', 'FAILED']:
                losses += 1
                total_pnl += pnl  # pnl should be negative for losses
                loss_amounts.append(abs(pnl))  # Store as positive for avg calculation

        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        # Calculate averages
        avg_win = sum(win_amounts) / len(win_amounts) if win_amounts else 0.0
        avg_loss = sum(loss_amounts) / len(loss_amounts) if loss_amounts else 0.0

        # Calculate profit factor (total wins / total losses)
        total_wins = sum(win_amounts)
        total_losses = sum(loss_amounts)
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0

        # Find largest win/loss
        largest_win = max(win_amounts) if win_amounts else 0.0
        largest_loss = max(loss_amounts) if loss_amounts else 0.0

        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2)
        }

    def _compare_ml_vs_classical(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare ML-assisted trades vs Classical trades

        Identify ML trades by checking:
        - trade['conditions']['ml_mode'] == True
        - OR trade metadata indicating ML was used

        Args:
            trades: List of trade dictionaries

        Returns:
            Dict with ML vs Classical performance comparison
        """
        ml_trades = []
        classical_trades = []

        for trade in trades:
            conditions = trade.get('conditions', {})

            # Check if ML mode was used
            is_ml = (
                conditions.get('ml_mode') is True or
                conditions.get('ml_enabled') is True or
                trade.get('ml_mode') is True or
                trade.get('ml_enabled') is True
            )

            if is_ml:
                ml_trades.append(trade)
            else:
                classical_trades.append(trade)

        # Calculate stats for both
        ml_stats = self._calculate_stats(ml_trades)
        classical_stats = self._calculate_stats(classical_trades)

        # Calculate delta
        win_rate_delta = ml_stats['win_rate'] - classical_stats['win_rate']
        pnl_delta = ml_stats['total_pnl'] - classical_stats['total_pnl']

        return {
            'ml': ml_stats,
            'classical': classical_stats,
            'delta': {
                'win_rate': round(win_rate_delta, 2),
                'total_pnl': round(pnl_delta, 2)
            },
            'insight': self._generate_ml_insight(ml_stats, classical_stats)
        }

    def _generate_ml_insight(
        self,
        ml_stats: Dict[str, Any],
        classical_stats: Dict[str, Any]
    ) -> str:
        """
        Generate actionable insight from ML vs Classical comparison

        Args:
            ml_stats: ML statistics
            classical_stats: Classical statistics

        Returns:
            Human-readable insight string
        """
        if ml_stats['total_trades'] == 0:
            return "No ML trades recorded yet. ML mode needs to be enabled."

        if classical_stats['total_trades'] == 0:
            return "All trades used ML mode."

        win_rate_delta = ml_stats['win_rate'] - classical_stats['win_rate']

        if win_rate_delta > 5:
            return f"✅ ML mode outperforms by {win_rate_delta:.1f}% - RECOMMENDED"
        elif win_rate_delta > 0:
            return f"👍 ML mode slightly better by {win_rate_delta:.1f}%"
        elif win_rate_delta > -5:
            return f"⚠️ ML mode slightly worse by {abs(win_rate_delta):.1f}%"
        else:
            return f"❌ Classical mode outperforms by {abs(win_rate_delta):.1f}%"

    def _breakdown_by_symbol(self, trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Break down performance by symbol

        Args:
            trades: List of trade dictionaries

        Returns:
            Dict mapping symbol to its statistics
        """
        symbol_trades = {}

        # Group trades by symbol
        for trade in trades:
            symbol = trade.get('symbol', 'UNKNOWN').upper()
            if symbol not in symbol_trades:
                symbol_trades[symbol] = []
            symbol_trades[symbol].append(trade)

        # Calculate stats for each symbol
        breakdown = {}
        for symbol, sym_trades in symbol_trades.items():
            breakdown[symbol] = self._calculate_stats(sym_trades)

        return breakdown

    def _breakdown_by_timeframe(self, trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Break down performance by timeframe

        Args:
            trades: List of trade dictionaries

        Returns:
            Dict mapping timeframe to its statistics
        """
        timeframe_trades = {}

        # Group trades by timeframe
        for trade in trades:
            timeframe = trade.get('timeframe', 'UNKNOWN').lower()
            if timeframe not in timeframe_trades:
                timeframe_trades[timeframe] = []
            timeframe_trades[timeframe].append(trade)

        # Calculate stats for each timeframe
        breakdown = {}
        for timeframe, tf_trades in timeframe_trades.items():
            breakdown[timeframe] = self._calculate_stats(tf_trades)

        return breakdown

    def _identify_performers(
        self,
        symbol_breakdown: Dict[str, Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Identify top and worst performing symbols

        Args:
            symbol_breakdown: Symbol-wise statistics

        Returns:
            Tuple of (top_performers, worst_performers) lists
        """
        # Convert to list and sort by win rate
        performers = []
        for symbol, stats in symbol_breakdown.items():
            if stats['total_trades'] >= 3:  # Minimum 3 trades for significance
                performers.append({
                    'symbol': symbol,
                    'win_rate': stats['win_rate'],
                    'total_pnl': stats['total_pnl'],
                    'total_trades': stats['total_trades']
                })

        # Sort by win rate
        performers.sort(key=lambda x: x['win_rate'], reverse=True)

        # Get top 3 and worst 3
        top_performers = performers[:3] if len(performers) >= 3 else performers
        worst_performers = performers[-3:] if len(performers) >= 3 else []
        worst_performers.reverse()  # Show worst first

        return top_performers, worst_performers


# Singleton pattern for easy access
_backtest_engine_instance = None


def get_backtest_engine(journal_path: Optional[str] = None) -> JournalBacktestEngine:
    """
    Get singleton instance of JournalBacktestEngine

    Args:
        journal_path: Optional path to trading journal

    Returns:
        JournalBacktestEngine instance
    """
    global _backtest_engine_instance
    if _backtest_engine_instance is None:
        _backtest_engine_instance = JournalBacktestEngine(journal_path)
    return _backtest_engine_instance
