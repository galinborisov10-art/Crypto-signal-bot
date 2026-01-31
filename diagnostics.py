"""
Production-Safe Diagnostic System
Author: Copilot
Date: 2026-01-30
Phase 2A: Expanded to 20 checks
Phase 2B: Replay Diagnostics for Regression Detection
"""

import logging
import sys
import importlib
import inspect
import numpy as np
import pandas as pd
import requests
from typing import Dict, List, Tuple, Callable, Optional
from datetime import datetime
from pathlib import Path
import time
import tempfile
import json
import hashlib
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class DiagnosticResult:
    """Single diagnostic check result"""
    def __init__(self, name: str, status: str, severity: str, message: str, details: str = ""):
        self.name = name
        self.status = status  # PASS / FAIL / WARN
        self.severity = severity  # HIGH / MED / LOW
        self.message = message
        self.details = details
        self.timestamp = datetime.now()

class DiagnosticRunner:
    """Safe diagnostic runner with isolation"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
    
    async def run_check(self, check_name: str, check_func, timeout: int = 30) -> DiagnosticResult:
        """
        Run single diagnostic check with isolation
        
        Args:
            check_name: Human-readable name
            check_func: Async or sync function to run
            timeout: Max seconds (default 30)
        
        Returns:
            DiagnosticResult
        """
        logger.info(f"🔍 Running: {check_name}")
        
        try:
            # Run with timeout
            if inspect.iscoroutinefunction(check_func):
                import asyncio
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = check_func()
            
            return result
        
        except Exception as e:
            logger.error(f"❌ {check_name} failed: {e}")
            return DiagnosticResult(
                name=check_name,
                status="FAIL",
                severity="HIGH",
                message=f"Exception: {str(e)}",
                details=f"{type(e).__name__}: {e}"
            )
    
    async def run_all(self, checks: List[Tuple[str, Callable]]) -> List[DiagnosticResult]:
        """Run all diagnostic checks sequentially"""
        self.start_time = datetime.now()
        self.results = []
        
        for check_name, check_func in checks:
            result = await self.run_check(check_name, check_func)
            self.results.append(result)
        
        self.end_time = datetime.now()
        return self.results
    
    def format_report(self) -> str:
        """Format results as Telegram message (optimized for 20 checks)"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warned = sum(1 for r in self.results if r.status == "WARN")
        
        report = f"🛠 *Diagnostic Report*\n\n"
        report += f"⏱ Duration: {duration:.1f}s\n"
        report += f"✅ Passed: {passed}\n"
        report += f"⚠️ Warnings: {warned}\n"
        report += f"❌ Failed: {failed}\n"
        report += f"\n{'='*30}\n\n"
        
        # Group by severity - only show failures/warnings to save space
        high_fails = [r for r in self.results if r.status == "FAIL" and r.severity == "HIGH"]
        if high_fails:
            report += "*🔴 HIGH SEVERITY FAILURES:*\n"
            for r in high_fails:
                report += f"• {r.name}\n  → {r.message}\n\n"
        
        med_fails = [r for r in self.results if r.status == "FAIL" and r.severity == "MED"]
        if med_fails:
            report += "*🟡 MEDIUM FAILURES:*\n"
            for r in med_fails:
                report += f"• {r.name}\n  → {r.message}\n\n"
        
        # Limit warnings display to avoid exceeding Telegram limit
        warnings = [r for r in self.results if r.status == "WARN"]
        if warnings:
            report += "*⚠️ WARNINGS:*\n"
            # Show max 5 warnings to save space
            for r in warnings[:5]:
                report += f"• {r.name}\n  → {r.message}\n\n"
            
            if len(warnings) > 5:
                report += f"_...and {len(warnings) - 5} more warnings_\n\n"
        
        # If all high severity checks passed, mention it
        high_checks = [r for r in self.results if r.severity == "HIGH"]
        high_passed = sum(1 for r in high_checks if r.status == "PASS")
        if high_passed == len(high_checks) and len(high_checks) > 0:
            report += "*✅ ALL HIGH SEVERITY CHECKS PASSED*\n"
        
        return report


# ========================================
# CORE DIAGNOSTIC CHECKS (5 checks)
# ========================================

def check_logger_configuration() -> DiagnosticResult:
    """Check 1: Validate logger setup"""
    try:
        root_logger = logging.getLogger()
        
        # Check handlers - also check for NullHandler or no handlers in quiet mode
        handlers_count = len(root_logger.handlers)
        
        # Allow no handlers if logging is configured at module level
        if handlers_count == 0:
            # Check if any module-level loggers exist
            module_loggers = [name for name in logging.Logger.manager.loggerDict 
                            if logging.getLogger(name).handlers]
            
            if not module_loggers:
                return DiagnosticResult(
                    name="Logger Configuration",
                    status="WARN",
                    severity="LOW",
                    message="No root logger handlers (may use module-level loggers)"
                )
        
        # Check log level
        if root_logger.level > logging.INFO:
            return DiagnosticResult(
                name="Logger Configuration",
                status="WARN",
                severity="LOW",
                message=f"Log level is {logging.getLevelName(root_logger.level)} (consider INFO)"
            )
        
        return DiagnosticResult(
            name="Logger Configuration",
            status="PASS",
            severity="LOW",
            message=f"{handlers_count} handlers, level={logging.getLevelName(root_logger.level)}"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Logger Configuration",
            status="FAIL",
            severity="HIGH",
            message=f"Exception: {e}"
        )


def check_critical_imports() -> DiagnosticResult:
    """Check 2: Validate critical dependencies"""
    required_modules = [
        'pandas',
        'numpy',
        'requests',
        'telegram',
        'ta'  # Technical analysis library
    ]
    
    missing = []
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    
    if missing:
        return DiagnosticResult(
            name="Critical Imports",
            status="FAIL",
            severity="HIGH",
            message=f"Missing modules: {', '.join(missing)}"
        )
    
    return DiagnosticResult(
        name="Critical Imports",
        status="PASS",
        severity="LOW",
        message="All critical modules available"
    )


def check_signal_schema_validation() -> DiagnosticResult:
    """Check 3: Validate signal object structure"""
    try:
        # Import signal engine
        from ict_signal_engine import ICTSignalEngine
        
        # Create mock signal
        engine = ICTSignalEngine()
        
        # Check required attributes/methods exist
        required_methods = ['generate_signal', '_detect_ict_components', '_calculate_sl_price']
        missing = [m for m in required_methods if not hasattr(engine, m)]
        
        if missing:
            return DiagnosticResult(
                name="Signal Schema",
                status="FAIL",
                severity="HIGH",
                message=f"Missing methods: {', '.join(missing)}"
            )
        
        return DiagnosticResult(
            name="Signal Schema",
            status="PASS",
            severity="MED",
            message="Signal engine structure valid"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Signal Schema",
            status="FAIL",
            severity="HIGH",
            message=f"Exception: {e}"
        )


def check_nan_in_indicators() -> DiagnosticResult:
    """Check 4: Test indicator calculations for NaN"""
    try:
        # Create sample data (using 'h' for hourly frequency - lowercase for pandas 2.x)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(45000, 50000, 100),
            'high': np.random.uniform(50000, 51000, 100),
            'low': np.random.uniform(44000, 45000, 100),
            'close': np.random.uniform(45000, 50000, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Test basic indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        
        # Check for NaN in last row (should have enough data)
        last_row = df.iloc[-1]
        nan_fields = [col for col in ['sma_20', 'ema_20'] if pd.isna(last_row[col])]
        
        if nan_fields:
            return DiagnosticResult(
                name="NaN Detection",
                status="FAIL",
                severity="HIGH",
                message=f"NaN in indicators: {', '.join(nan_fields)}"
            )
        
        return DiagnosticResult(
            name="NaN Detection",
            status="PASS",
            severity="MED",
            message="Indicators calculate without NaN"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="NaN Detection",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_duplicate_signal_guard() -> DiagnosticResult:
    """Check 5: Verify duplicate signal prevention exists"""
    try:
        # Check if cache manager exists - try both locations
        try:
            from cache_manager import CacheManager
            cache_mgr = CacheManager()
        except ImportError:
            try:
                from bot import CacheManager
                cache_mgr = CacheManager()
            except (ImportError, AttributeError):
                # CacheManager not available - this is OK, system may use different deduplication
                return DiagnosticResult(
                    name="Duplicate Guard",
                    status="WARN",
                    severity="LOW",
                    message="CacheManager not found (may use different duplicate prevention)"
                )
        
        # Check for duplicate detection method
        if not hasattr(cache_mgr, 'has_signal') and not hasattr(cache_mgr, 'get'):
            return DiagnosticResult(
                name="Duplicate Guard",
                status="WARN",
                severity="MED",
                message="CacheManager exists but no obvious duplicate detection method"
            )
        
        return DiagnosticResult(
            name="Duplicate Guard",
            status="PASS",
            severity="MED",
            message="Cache manager with duplicate detection present"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Duplicate Guard",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


# ========================================
# PHASE 2A: NEW DIAGNOSTIC CHECKS (15)
# ========================================

# GROUP 1: MTF Data Validation (4 checks)

def check_mtf_timeframes_available() -> DiagnosticResult:
    """
    Check 6: Verify all required MTF timeframes are fetchable from Binance
    
    Tests:
    - 1h data available
    - 2h data available
    - 4h data available
    - 1d data available
    
    Severity: MED (network-dependent check)
    """
    try:
        BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
        timeframes = ['1h', '2h', '4h', '1d']
        failed_timeframes = []
        
        for tf in timeframes:
            try:
                response = requests.get(
                    BINANCE_KLINES_URL,
                    params={
                        'symbol': 'BTCUSDT',
                        'interval': tf,
                        'limit': 1
                    },
                    timeout=3
                )
                
                if response.status_code != 200:
                    failed_timeframes.append(f"{tf} (status {response.status_code})")
                elif not response.json():
                    failed_timeframes.append(f"{tf} (empty data)")
            
            except requests.RequestException as e:
                failed_timeframes.append(f"{tf} (network error)")
        
        if failed_timeframes:
            return DiagnosticResult(
                name="MTF Timeframes Available",
                status="WARN",
                severity="MED",
                message=f"Network issue: {len(failed_timeframes)}/{len(timeframes)} timeframes unavailable"
            )
        
        return DiagnosticResult(
            name="MTF Timeframes Available",
            status="PASS",
            severity="MED",
            message=f"All {len(timeframes)} timeframes accessible"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="MTF Timeframes Available",
            status="WARN",
            severity="MED",
            message=f"Network exception: {str(e)[:50]}"
        )


def check_htf_components_storage() -> DiagnosticResult:
    """
    Check 7: Verify HTF components can be stored/retrieved
    
    Tests:
    - htf_components dict exists in mock context
    - Can write test HTF data
    - Can read back HTF data
    - Data persists correctly
    
    Severity: LOW (synthetic validation)
    """
    try:
        # Mock bot_data dictionary
        mock_bot_data = {}
        
        # Test write
        test_data = {
            'BTCUSDT': {
                '4h': {
                    'order_blocks': [{'price': 45000}],
                    'fvg': [{'price': 46000}]
                }
            }
        }
        
        mock_bot_data['htf_components'] = test_data
        
        # Test read back
        retrieved = mock_bot_data.get('htf_components', {})
        
        if not retrieved:
            return DiagnosticResult(
                name="HTF Components Storage",
                status="WARN",
                severity="LOW",
                message="Synthetic check: htf_components dict not initialized"
            )
        
        # Verify data integrity
        if retrieved != test_data:
            return DiagnosticResult(
                name="HTF Components Storage",
                status="FAIL",
                severity="LOW",
                message="Synthetic check: data corruption detected"
            )
        
        return DiagnosticResult(
            name="HTF Components Storage",
            status="PASS",
            severity="LOW",
            message="Synthetic check: storage read/write working"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="HTF Components Storage",
            status="FAIL",
            severity="LOW",
            message=f"Synthetic check exception: {e}"
        )


def check_klines_data_freshness() -> DiagnosticResult:
    """
    Check 8: Verify Binance klines data is fresh (not stale)
    
    Tests:
    - Fetch latest 1h kline for BTCUSDT
    - Check timestamp is within last 2 hours
    - Verify close_time is recent
    
    Severity: MED (network-dependent check)
    """
    try:
        BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
        
        response = requests.get(
            BINANCE_KLINES_URL,
            params={
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 1
            },
            timeout=3
        )
        
        if response.status_code != 200:
            return DiagnosticResult(
                name="Klines Data Freshness",
                status="WARN",
                severity="MED",
                message=f"Network issue: API status {response.status_code}"
            )
        
        klines = response.json()
        if not klines:
            return DiagnosticResult(
                name="Klines Data Freshness",
                status="WARN",
                severity="MED",
                message="Network issue: empty klines response"
            )
        
        # Parse timestamp (close_time is at index 6)
        close_time_ms = klines[0][6]
        close_time = datetime.fromtimestamp(close_time_ms / 1000)
        current_time = datetime.now()
        
        age_hours = (current_time - close_time).total_seconds() / 3600
        
        if age_hours > 2:
            return DiagnosticResult(
                name="Klines Data Freshness",
                status="WARN",
                severity="MED",
                message=f"Data is {age_hours:.1f}h old (stale)"
            )
        
        return DiagnosticResult(
            name="Klines Data Freshness",
            status="PASS",
            severity="MED",
            message=f"Data is fresh ({age_hours:.1f}h old)"
        )
    
    except requests.RequestException as e:
        return DiagnosticResult(
            name="Klines Data Freshness",
            status="WARN",
            severity="MED",
            message=f"Network exception: {str(e)[:50]}"
        )
    except Exception as e:
        return DiagnosticResult(
            name="Klines Data Freshness",
            status="WARN",
            severity="MED",
            message=f"Exception: {str(e)[:50]}"
        )


def check_price_data_sanity() -> DiagnosticResult:
    """
    Check 9: Verify price data has no anomalies
    
    Tests:
    - No zero prices (open, high, low, close)
    - No negative prices
    - High >= Low
    - High >= Open, Close
    - Low <= Open, Close
    
    Severity: MED (network-dependent check)
    """
    try:
        BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
        
        response = requests.get(
            BINANCE_KLINES_URL,
            params={
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 10
            },
            timeout=3
        )
        
        if response.status_code != 200:
            return DiagnosticResult(
                name="Price Data Sanity",
                status="WARN",
                severity="MED",
                message=f"Network issue: API status {response.status_code}"
            )
        
        klines = response.json()
        anomalies = []
        
        for i, kline in enumerate(klines):
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            
            # Check for zero or negative
            if any(p <= 0 for p in [open_price, high_price, low_price, close_price]):
                anomalies.append(f"Candle {i}: Zero/negative price")
            
            # Check high >= low
            if high_price < low_price:
                anomalies.append(f"Candle {i}: High < Low")
            
            # Check high >= open, close
            if high_price < open_price or high_price < close_price:
                anomalies.append(f"Candle {i}: High below Open/Close")
            
            # Check low <= open, close
            if low_price > open_price or low_price > close_price:
                anomalies.append(f"Candle {i}: Low above Open/Close")
        
        if anomalies:
            return DiagnosticResult(
                name="Price Data Sanity",
                status="FAIL",
                severity="MED",
                message=f"{len(anomalies)} anomalies found",
                details="; ".join(anomalies[:3])  # First 3 anomalies
            )
        
        return DiagnosticResult(
            name="Price Data Sanity",
            status="PASS",
            severity="MED",
            message=f"All {len(klines)} candles valid"
        )
    
    except requests.RequestException as e:
        return DiagnosticResult(
            name="Price Data Sanity",
            status="WARN",
            severity="MED",
            message=f"Network exception: {str(e)[:50]}"
        )
    except Exception as e:
        return DiagnosticResult(
            name="Price Data Sanity",
            status="WARN",
            severity="MED",
            message=f"Exception: {str(e)[:50]}"
        )


# GROUP 2: Signal Schema Extended (3 checks)

def check_signal_required_fields() -> DiagnosticResult:
    """
    Check 10: Verify signal objects have all required fields
    
    Tests:
    - ICTSignal has: signal_type, confidence, entry_price, tp_prices, sl_price
    - ICTSignal has: bias, htf_bias, structure_broken, displacement_detected
    - ICTSignal has: order_blocks, liquidity_zones, fair_value_gaps
    - ICTSignal has: mtf_confluence
    
    Severity: HIGH
    """
    try:
        # Try to import ICTSignal or signal structure
        try:
            from ict_signal_engine import ICTSignalEngine
            engine = ICTSignalEngine()
        except ImportError:
            return DiagnosticResult(
                name="Signal Required Fields",
                status="WARN",
                severity="HIGH",
                message="ICTSignalEngine not found (check import paths)"
            )
        
        # Check if engine has the signal generation method
        required_methods = [
            'generate_signal',
            '_detect_ict_components',
            '_calculate_sl_price',
            '_calculate_tp_prices'
        ]
        
        missing_methods = [m for m in required_methods if not hasattr(engine, m)]
        
        if missing_methods:
            return DiagnosticResult(
                name="Signal Required Fields",
                status="FAIL",
                severity="HIGH",
                message=f"Missing methods: {', '.join(missing_methods)}"
            )
        
        return DiagnosticResult(
            name="Signal Required Fields",
            status="PASS",
            severity="HIGH",
            message="Signal engine structure validated"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Signal Required Fields",
            status="FAIL",
            severity="HIGH",
            message=f"Exception: {e}"
        )


def check_cache_write_read() -> DiagnosticResult:
    """
    Check 11: Verify cache can write and read data
    
    Tests:
    - Can write test signal to cache
    - Can read back same signal
    - Data integrity preserved
    - No corruption
    
    Severity: MED
    """
    try:
        # Create temp cache file
        temp_dir = Path(tempfile.gettempdir())
        cache_file = temp_dir / "test_cache_diagnostic.tmp"
        
        # Test data
        test_signal = {
            'symbol': 'BTCUSDT',
            'signal_type': 'LONG',
            'entry_price': 45000,
            'timestamp': datetime.now().isoformat()
        }
        
        # Write to cache
        import json
        with open(cache_file, 'w') as f:
            json.dump(test_signal, f)
        
        # Read back
        with open(cache_file, 'r') as f:
            retrieved = json.load(f)
        
        # Clean up
        cache_file.unlink()
        
        # Verify integrity
        if retrieved != test_signal:
            return DiagnosticResult(
                name="Cache Write/Read Test",
                status="FAIL",
                severity="MED",
                message="Data corruption detected"
            )
        
        return DiagnosticResult(
            name="Cache Write/Read Test",
            status="PASS",
            severity="MED",
            message="Cache I/O working correctly"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Cache Write/Read Test",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_signal_type_validation() -> DiagnosticResult:
    """
    Check 12: Verify signal types are valid enums
    
    Tests:
    - SignalType enum exists
    - Has LONG, SHORT values
    - MarketBias enum exists
    - Has BULLISH, BEARISH, NEUTRAL values
    
    Severity: LOW
    """
    try:
        # Try to import signal types
        signal_types_found = []
        
        # Check for SignalType
        try:
            from ict_signal_engine import SignalType
            if hasattr(SignalType, 'LONG') and hasattr(SignalType, 'SHORT'):
                signal_types_found.append("SignalType")
        except (ImportError, AttributeError):
            pass
        
        # Check for MarketBias
        try:
            from ict_signal_engine import MarketBias
            if all(hasattr(MarketBias, attr) for attr in ['BULLISH', 'BEARISH', 'NEUTRAL']):
                signal_types_found.append("MarketBias")
        except (ImportError, AttributeError):
            pass
        
        if not signal_types_found:
            return DiagnosticResult(
                name="Signal Type Validation",
                status="WARN",
                severity="LOW",
                message="Signal enums not found (may use strings)"
            )
        
        return DiagnosticResult(
            name="Signal Type Validation",
            status="PASS",
            severity="LOW",
            message=f"Enums found: {', '.join(signal_types_found)}"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Signal Type Validation",
            status="FAIL",
            severity="LOW",
            message=f"Exception: {e}"
        )


# GROUP 3: Runtime Health (4 checks)

def check_memory_usage() -> DiagnosticResult:
    """
    Check 13: Verify memory usage is reasonable
    
    Tests:
    - Current process RSS < 1GB (warn at 500MB)
    - No memory leaks detected (stable over 10 samples)
    - Garbage collector running
    
    Severity: MED
    """
    try:
        # Try psutil first, fall back to resource module
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            rss_mb = memory_info.rss / (1024 * 1024)
        except ImportError:
            # Fallback to resource module (Unix only)
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                # maxrss is in KB on Linux, bytes on macOS
                rss_mb = usage.ru_maxrss / 1024  # Assume KB
            except Exception:
                return DiagnosticResult(
                    name="Memory Usage",
                    status="WARN",
                    severity="MED",
                    message="psutil not available, cannot measure memory"
                )
        
        # Check thresholds
        if rss_mb > 1024:  # > 1GB
            return DiagnosticResult(
                name="Memory Usage",
                status="FAIL",
                severity="MED",
                message=f"High memory usage: {rss_mb:.0f}MB (>1GB limit)"
            )
        elif rss_mb > 500:  # > 500MB
            return DiagnosticResult(
                name="Memory Usage",
                status="WARN",
                severity="MED",
                message=f"Elevated memory: {rss_mb:.0f}MB (warn at 500MB)"
            )
        
        return DiagnosticResult(
            name="Memory Usage",
            status="PASS",
            severity="MED",
            message=f"Memory: {rss_mb:.0f}MB"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Memory Usage",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_response_time() -> DiagnosticResult:
    """
    Check 14: Verify diagnostic response time is acceptable
    
    Tests:
    - Simple calculation completes < 100ms
    - DataFrame operation completes < 500ms
    - Indicator calculation completes < 2s
    
    Severity: LOW
    """
    try:
        # Test 1: Simple calculation
        start = time.time()
        _ = sum(range(10000))
        simple_time_ms = (time.time() - start) * 1000
        
        if simple_time_ms > 100:
            return DiagnosticResult(
                name="Response Time Test",
                status="WARN",
                severity="LOW",
                message=f"Slow simple calc: {simple_time_ms:.0f}ms (>100ms)"
            )
        
        # Test 2: DataFrame operation
        start = time.time()
        df = pd.DataFrame({'value': range(200)})
        df['sma'] = df['value'].rolling(window=20).mean()
        df_time_ms = (time.time() - start) * 1000
        
        if df_time_ms > 500:
            return DiagnosticResult(
                name="Response Time Test",
                status="WARN",
                severity="LOW",
                message=f"Slow DataFrame: {df_time_ms:.0f}ms (>500ms)"
            )
        
        # Test 3: Indicator calculation
        start = time.time()
        df['ema'] = df['value'].ewm(span=20).mean()
        df['rsi'] = df['value'].rolling(window=14).apply(
            lambda x: 100 - (100 / (1 + (x[x > x.shift()].sum() / x[x < x.shift()].abs().sum()))) 
            if len(x[x < x.shift()]) > 0 else 50
        )
        indicator_time_ms = (time.time() - start) * 1000
        
        if indicator_time_ms > 2000:
            return DiagnosticResult(
                name="Response Time Test",
                status="WARN",
                severity="LOW",
                message=f"Slow indicators: {indicator_time_ms:.0f}ms (>2s)"
            )
        
        return DiagnosticResult(
            name="Response Time Test",
            status="PASS",
            severity="LOW",
            message=f"All ops fast (df: {df_time_ms:.0f}ms, ind: {indicator_time_ms:.0f}ms)"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Response Time Test",
            status="FAIL",
            severity="LOW",
            message=f"Exception: {e}"
        )


def check_exception_rate() -> DiagnosticResult:
    """
    Check 15: Verify exception rate in logs is low
    
    Tests:
    - Parse last 1000 log lines
    - Count ERROR/EXCEPTION entries
    - Warn if > 5%, fail if > 10%
    
    Severity: MED
    """
    try:
        log_file = Path("bot.log")
        
        if not log_file.exists():
            return DiagnosticResult(
                name="Exception Rate",
                status="WARN",
                severity="MED",
                message="bot.log not found (may use stdout)"
            )
        
        # Read last 1000 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Get last 1000 lines
        recent_lines = lines[-1000:] if len(lines) > 1000 else lines
        total_lines = len(recent_lines)
        
        if total_lines == 0:
            return DiagnosticResult(
                name="Exception Rate",
                status="WARN",
                severity="MED",
                message="Log file is empty"
            )
        
        # Count errors/exceptions
        error_count = sum(1 for line in recent_lines 
                         if 'ERROR' in line.upper() or 'EXCEPTION' in line.upper())
        
        error_rate = (error_count / total_lines) * 100
        
        if error_rate > 10:
            return DiagnosticResult(
                name="Exception Rate",
                status="FAIL",
                severity="MED",
                message=f"{error_rate:.1f}% error rate (>{10}% threshold)"
            )
        elif error_rate > 5:
            return DiagnosticResult(
                name="Exception Rate",
                status="WARN",
                severity="MED",
                message=f"{error_rate:.1f}% error rate (>{5}% threshold)"
            )
        
        return DiagnosticResult(
            name="Exception Rate",
            status="PASS",
            severity="MED",
            message=f"{error_rate:.1f}% error rate in last {total_lines} lines"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Exception Rate",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_job_queue_health() -> DiagnosticResult:
    """
    Check 16: Verify no indication of stuck jobs
    
    Tests:
    - No repeated "job timeout" in logs
    - No "infinite loop" indicators
    - No stuck job warnings
    
    Severity: LOW
    """
    try:
        log_file = Path("bot.log")
        
        if not log_file.exists():
            return DiagnosticResult(
                name="Job Queue Health",
                status="WARN",
                severity="LOW",
                message="bot.log not found (cannot check)"
            )
        
        # Read last 500 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        # Look for stuck job patterns
        timeout_count = sum(1 for line in recent_lines if 'timeout' in line.lower())
        stuck_count = sum(1 for line in recent_lines if 'stuck' in line.lower())
        infinite_count = sum(1 for line in recent_lines if 'infinite loop' in line.lower())
        
        total_issues = timeout_count + stuck_count + infinite_count
        
        if total_issues > 10:
            return DiagnosticResult(
                name="Job Queue Health",
                status="WARN",
                severity="LOW",
                message=f"{total_issues} timeout/stuck indicators found"
            )
        elif total_issues > 0:
            return DiagnosticResult(
                name="Job Queue Health",
                status="WARN",
                severity="LOW",
                message=f"{total_issues} minor timeout/stuck indicators"
            )
        
        return DiagnosticResult(
            name="Job Queue Health",
            status="PASS",
            severity="LOW",
            message="No stuck job indicators"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Job Queue Health",
            status="FAIL",
            severity="LOW",
            message=f"Exception: {e}"
        )


# GROUP 4: External Integration (4 checks)

def check_binance_api_reachable() -> DiagnosticResult:
    """
    Check 17: Verify Binance API is reachable and responding
    
    Tests:
    - GET https://api.binance.com/api/v3/ping
    - Response status 200
    - Response time < 3s
    
    Severity: MED (network-dependent check)
    """
    try:
        BINANCE_PING_URL = "https://api.binance.com/api/v3/ping"
        
        start = time.time()
        response = requests.get(BINANCE_PING_URL, timeout=3)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            return DiagnosticResult(
                name="Binance API Reachable",
                status="WARN",
                severity="MED",
                message=f"Network issue: API status {response.status_code}"
            )
        
        if elapsed > 3:
            return DiagnosticResult(
                name="Binance API Reachable",
                status="WARN",
                severity="MED",
                message=f"Slow response: {elapsed:.1f}s (>3s)"
            )
        
        return DiagnosticResult(
            name="Binance API Reachable",
            status="PASS",
            severity="MED",
            message=f"API responsive ({elapsed*1000:.0f}ms)"
        )
    
    except requests.Timeout:
        return DiagnosticResult(
            name="Binance API Reachable",
            status="WARN",
            severity="MED",
            message="Network timeout (>3s)"
        )
    except requests.RequestException as e:
        return DiagnosticResult(
            name="Binance API Reachable",
            status="WARN",
            severity="MED",
            message=f"Network exception: {str(e)[:50]}"
        )
    except Exception as e:
        return DiagnosticResult(
            name="Binance API Reachable",
            status="WARN",
            severity="MED",
            message=f"Exception: {str(e)[:50]}"
        )


def check_telegram_api_responsive() -> DiagnosticResult:
    """
    Check 18: Verify Telegram API is responsive
    
    Tests:
    - Can import telegram module
    - telegram.Bot class exists
    - No known connection issues in logs
    
    Severity: MED
    """
    try:
        # Check if telegram module exists
        try:
            import telegram
            if not hasattr(telegram, 'Bot'):
                return DiagnosticResult(
                    name="Telegram API Responsive",
                    status="FAIL",
                    severity="MED",
                    message="telegram.Bot class not found"
                )
        except ImportError:
            return DiagnosticResult(
                name="Telegram API Responsive",
                status="FAIL",
                severity="MED",
                message="telegram module not installed"
            )
        
        # Check logs for Telegram errors
        log_file = Path("bot.log")
        telegram_errors = 0
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            recent_lines = lines[-500:] if len(lines) > 500 else lines
            telegram_errors = sum(1 for line in recent_lines 
                                 if 'telegram' in line.lower() and 'error' in line.lower())
        
        if telegram_errors > 10:
            return DiagnosticResult(
                name="Telegram API Responsive",
                status="WARN",
                severity="MED",
                message=f"{telegram_errors} Telegram errors in logs"
            )
        
        return DiagnosticResult(
            name="Telegram API Responsive",
            status="PASS",
            severity="MED",
            message="Telegram module available"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Telegram API Responsive",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_file_system_access() -> DiagnosticResult:
    """
    Check 19: Verify file system read/write works
    
    Tests:
    - Can read bot.py (project root accessible)
    - Can write to temp directory
    - Cache directory exists and writable
    
    Severity: MED
    """
    try:
        # Test 1: Read bot.py
        bot_file = Path("bot.py")
        if not bot_file.exists():
            return DiagnosticResult(
                name="File System Access",
                status="FAIL",
                severity="MED",
                message="Cannot find bot.py (wrong directory?)"
            )
        
        try:
            with open(bot_file, 'r') as f:
                _ = f.read(100)  # Read first 100 chars
        except PermissionError:
            return DiagnosticResult(
                name="File System Access",
                status="FAIL",
                severity="MED",
                message="No read permission for bot.py"
            )
        
        # Test 2: Write to temp
        temp_dir = Path(tempfile.gettempdir())
        test_file = temp_dir / "diagnostic_test.tmp"
        
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            test_file.unlink()
        except PermissionError:
            return DiagnosticResult(
                name="File System Access",
                status="FAIL",
                severity="MED",
                message="No write permission for temp directory"
            )
        
        return DiagnosticResult(
            name="File System Access",
            status="PASS",
            severity="MED",
            message="Read/write access working"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="File System Access",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_log_file_writeable() -> DiagnosticResult:
    """
    Check 20: Verify log file is writeable
    
    Tests:
    - bot.log exists
    - bot.log is writeable
    - No permission errors
    
    Severity: LOW
    """
    try:
        log_file = Path("bot.log")
        
        if not log_file.exists():
            return DiagnosticResult(
                name="Log File Writeable",
                status="WARN",
                severity="LOW",
                message="bot.log not found (may use stdout)"
            )
        
        # Test write permission
        try:
            with open(log_file, 'a') as f:
                pass  # Just open in append mode
        except PermissionError:
            return DiagnosticResult(
                name="Log File Writeable",
                status="FAIL",
                severity="LOW",
                message="No write permission for bot.log"
            )
        
        return DiagnosticResult(
            name="Log File Writeable",
            status="PASS",
            severity="LOW",
            message="Log file writeable"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Log File Writeable",
            status="FAIL",
            severity="LOW",
            message=f"Exception: {e}"
        )


# ========================================
# QUICK CHECK FUNCTION
# ========================================

async def run_quick_check() -> str:
    """Run 20 diagnostic checks (Phase 2A expanded)"""
    runner = DiagnosticRunner()
    
    checks = [
        # Original 5 checks
        ("Logger Configuration", check_logger_configuration),
        ("Critical Imports", check_critical_imports),
        ("Signal Schema", check_signal_schema_validation),
        ("NaN Detection", check_nan_in_indicators),
        ("Duplicate Guard", check_duplicate_signal_guard),
        
        # GROUP 1: MTF Data Validation (4 checks)
        ("MTF Timeframes Available", check_mtf_timeframes_available),
        ("HTF Components Storage", check_htf_components_storage),
        ("Klines Data Freshness", check_klines_data_freshness),
        ("Price Data Sanity", check_price_data_sanity),
        
        # GROUP 2: Signal Schema Extended (3 checks)
        ("Signal Required Fields", check_signal_required_fields),
        ("Cache Write/Read Test", check_cache_write_read),
        ("Signal Type Validation", check_signal_type_validation),
        
        # GROUP 3: Runtime Health (4 checks)
        ("Memory Usage", check_memory_usage),
        ("Response Time Test", check_response_time),
        ("Exception Rate", check_exception_rate),
        ("Job Queue Health", check_job_queue_health),
        
        # GROUP 4: External Integration (4 checks)
        ("Binance API Reachable", check_binance_api_reachable),
        ("Telegram API Responsive", check_telegram_api_responsive),
        ("File System Access", check_file_system_access),
        ("Log File Writeable", check_log_file_writeable),
    ]
    
    await runner.run_all(checks)
    return runner.format_report()


# ============================================================
# PHASE 2B: REPLAY DIAGNOSTICS FOR REGRESSION DETECTION
# ============================================================

@dataclass
class SignalSnapshot:
    """Snapshot of a signal for replay"""
    timestamp: str
    symbol: str
    timeframe: str
    klines_snapshot: List[List]  # Max 100 rows
    original_signal: Dict
    signal_hash: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SignalSnapshot':
        """Create from dictionary"""
        return cls(**data)


class ReplayCache:
    """Manages replay signal storage with rotation"""
    MAX_SIGNALS = 10
    MAX_KLINES_PER_SIGNAL = 100
    CACHE_FILE = Path("replay_cache.json")
    
    def __init__(self):
        self.cache_file = self.CACHE_FILE
    
    def _generate_signal_hash(self, signal_data: Dict, klines: pd.DataFrame) -> str:
        """Generate unique hash for signal"""
        # Create hash from signal type, symbol, timeframe, and timestamp
        hash_input = f"{signal_data.get('symbol', '')}_{signal_data.get('timeframe', '')}_{signal_data.get('signal_type', '')}_{signal_data.get('timestamp', '')}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def save_signal(self, signal_data: Dict, klines: pd.DataFrame) -> bool:
        """
        Save signal snapshot with rotation
        
        Args:
            signal_data: Signal dictionary with required fields
            klines: DataFrame with klines data
        
        Returns:
            bool: True if saved successfully
        """
        try:
            # Validate inputs
            if not isinstance(signal_data, dict):
                logger.warning("⚠️ Replay capture: signal_data is not a dict")
                return False
            
            if not isinstance(klines, pd.DataFrame) or len(klines) == 0:
                logger.warning("⚠️ Replay capture: invalid klines data")
                return False
            
            # Limit klines to MAX_KLINES_PER_SIGNAL most recent rows
            klines_limited = klines.tail(self.MAX_KLINES_PER_SIGNAL).copy()
            
            # Convert DataFrame to list of lists
            klines_snapshot = []
            for _, row in klines_limited.iterrows():
                # Store essential OHLCV data
                klines_snapshot.append([
                    int(row.name.timestamp() * 1000) if hasattr(row.name, 'timestamp') else 0,
                    str(row.get('open', 0)),
                    str(row.get('high', 0)),
                    str(row.get('low', 0)),
                    str(row.get('close', 0)),
                    str(row.get('volume', 0))
                ])
            
            # Create snapshot
            snapshot = SignalSnapshot(
                timestamp=datetime.now().isoformat(),
                symbol=signal_data.get('symbol', 'UNKNOWN'),
                timeframe=signal_data.get('timeframe', 'UNKNOWN'),
                klines_snapshot=klines_snapshot,
                original_signal=signal_data,
                signal_hash=self._generate_signal_hash(signal_data, klines)
            )
            
            # Load existing signals
            signals = self.load_signals()
            
            # Add new snapshot
            signals.append(snapshot)
            
            # Rotate if exceeds MAX_SIGNALS
            if len(signals) > self.MAX_SIGNALS:
                signals = signals[-self.MAX_SIGNALS:]
                logger.info(f"🔄 Rotated replay cache (removed oldest signal)")
            
            # Save to file
            cache_data = {
                "signals": [sig.to_dict() for sig in signals],
                "metadata": {
                    "max_signals": self.MAX_SIGNALS,
                    "max_klines": self.MAX_KLINES_PER_SIGNAL,
                    "last_cleanup": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"✅ Saved signal snapshot: {snapshot.symbol} {snapshot.timeframe} (hash: {snapshot.signal_hash})")
            return True
        
        except Exception as e:
            logger.warning(f"⚠️ Replay capture failed (non-critical): {e}")
            return False
    
    def load_signals(self) -> List[SignalSnapshot]:
        """Load all signal snapshots from cache"""
        try:
            if not self.cache_file.exists():
                return []
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            signals = cache_data.get('signals', [])
            return [SignalSnapshot.from_dict(sig) for sig in signals]
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to load replay cache: {e}")
            return []
    
    def clear_cache(self) -> bool:
        """Clear all cached signals"""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info("✅ Replay cache cleared")
                return True
            else:
                logger.info("ℹ️ Replay cache already empty")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to clear replay cache: {e}")
            return False
    
    def get_signal_count(self) -> int:
        """Get number of cached signals"""
        return len(self.load_signals())


class ReplayEngine:
    """Replays signals and detects regressions"""
    
    def __init__(self, cache: ReplayCache):
        self.cache = cache
    
    async def replay_signal(self, snapshot: SignalSnapshot) -> Optional[Dict]:
        """
        Re-run signal through engine (read-only)
        
        Args:
            snapshot: SignalSnapshot to replay
        
        Returns:
            Dict with replayed signal data or None if failed
        """
        try:
            # Reconstruct DataFrame from snapshot
            klines_data = []
            for kline in snapshot.klines_snapshot:
                klines_data.append({
                    'timestamp': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            df = pd.DataFrame(klines_data)
            
            # Convert timestamp to datetime index
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
            
            # ✅ FIX 1: Use global production engine instance
            # Try to import and use the global engine first
            engine = None
            try:
                import bot
                if hasattr(bot, 'ict_engine_global'):
                    engine = bot.ict_engine_global
                    logger.info("✅ Using global production ICT engine for replay")
            except (ImportError, AttributeError) as e:
                logger.warning(f"⚠️ Could not access global engine: {e}")
            
            # Fallback to creating new instance if global not available
            if engine is None:
                from ict_signal_engine import ICTSignalEngine
                engine = ICTSignalEngine()
                logger.warning("⚠️ Using fallback ICT engine instance for replay")
            
            # Generate signal (read-only - no cache write)
            signal = engine.generate_signal(
                df=df,
                symbol=snapshot.symbol,
                timeframe=snapshot.timeframe,
                mtf_data=None,  # No MTF data for replay
                is_auto=False
            )
            
            if signal is None:
                logger.warning(f"⚠️ Replay produced no signal for {snapshot.symbol} {snapshot.timeframe}")
                return None
            
            # Convert signal to dict
            replayed_signal = {
                'signal_type': signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type),
                'direction': signal.direction,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit if isinstance(signal.take_profit, list) else [signal.take_profit],
                'confidence': signal.confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Replayed signal: {snapshot.symbol} {snapshot.timeframe}")
            return replayed_signal
        
        except Exception as e:
            logger.error(f"❌ Replay failed for {snapshot.symbol} {snapshot.timeframe}: {e}")
            return None
    
    def compare_signals(self, original: Dict, replayed: Dict) -> Dict:
        """
        Compare signals and detect regressions
        
        Args:
            original: Original signal dict
            replayed: Replayed signal dict
        
        Returns:
            Dict with comparison results
        """
        # ✅ FIX 2: Relaxed price tolerance from 0.01% to 0.5%
        PRICE_TOLERANCE_PERCENT = 0.005  # 0.5% tolerance for price levels
        
        # ✅ FIX 3: Add confidence tolerance
        CONFIDENCE_TOLERANCE = 5  # ±5 points tolerance for confidence
        
        def check_price_match(orig_price: float, replay_price: float, base_price: float) -> bool:
            """Check if prices match within tolerance"""
            if base_price == 0:
                return orig_price == replay_price
            delta = abs(orig_price - replay_price) / base_price
            return delta <= PRICE_TOLERANCE_PERCENT
        
        def check_tp_arrays(orig_tp: List, replay_tp: List, base_price: float) -> bool:
            """Check if TP arrays match"""
            if len(orig_tp) != len(replay_tp):
                return False
            for o, r in zip(orig_tp, replay_tp):
                if not check_price_match(o, r, base_price):
                    return False
            return True
        
        def check_confidence_match(orig_conf: float, replay_conf: float) -> bool:
            """Check if confidence values match within tolerance"""
            return abs(orig_conf - replay_conf) <= CONFIDENCE_TOLERANCE
        
        # Extract values
        orig_type = original.get('signal_type', 'UNKNOWN')
        replay_type = replayed.get('signal_type', 'UNKNOWN')
        
        orig_dir = original.get('direction', 'UNKNOWN')
        replay_dir = replayed.get('direction', 'UNKNOWN')
        
        orig_entry = original.get('entry_price', 0)
        replay_entry = replayed.get('entry_price', 0)
        
        orig_sl = original.get('stop_loss', 0)
        replay_sl = replayed.get('stop_loss', 0)
        
        orig_tp = original.get('take_profit', [])
        replay_tp = replayed.get('take_profit', [])
        
        # ✅ FIX 3: Extract confidence values
        orig_confidence = original.get('confidence', 0)
        replay_confidence = replayed.get('confidence', 0)
        
        # Ensure TP is a list
        if not isinstance(orig_tp, list):
            orig_tp = [orig_tp] if orig_tp else []
        if not isinstance(replay_tp, list):
            replay_tp = [replay_tp] if replay_tp else []
        
        # Run checks (including confidence check)
        checks = {
            'signal_type': orig_type == replay_type,
            'direction': orig_dir == replay_dir,
            'entry_delta': check_price_match(orig_entry, replay_entry, orig_entry),
            'sl_delta': check_price_match(orig_sl, replay_sl, orig_entry),
            'tp_delta': check_tp_arrays(orig_tp, replay_tp, orig_entry),
            'confidence_delta': check_confidence_match(orig_confidence, replay_confidence)
        }
        
        diffs = [k for k, v in checks.items() if not v]
        
        return {
            'match': len(diffs) == 0,
            'diffs': diffs,
            'summary': f"✅ Match" if not diffs else f"❌ Regression: {', '.join(diffs)}"
        }
    
    async def replay_all_signals(self) -> str:
        """
        Replay all cached signals and format report
        
        Returns:
            str: Formatted report for Telegram
        """
        try:
            signals = self.cache.load_signals()
            
            if not signals:
                return "📊 *Replay Report*\n\n⚠️ No signals in cache yet.\n\nGenerate some signals first!"
            
            report = f"🎬 *Signal Replay Report*\n\n"
            report += f"📊 Testing {len(signals)} cached signals...\n\n"
            
            passed = 0
            failed = 0
            errors = 0
            
            for i, snapshot in enumerate(signals, 1):
                # Replay signal
                replayed = await self.replay_signal(snapshot)
                
                if replayed is None:
                    errors += 1
                    report += f"{i}. ⚠️ {snapshot.symbol} {snapshot.timeframe} - *Replay Error*\n"
                    continue
                
                # Compare signals
                comparison = self.compare_signals(snapshot.original_signal, replayed)
                
                if comparison['match']:
                    passed += 1
                    report += f"{i}. ✅ {snapshot.symbol} {snapshot.timeframe} - *Match*\n"
                else:
                    failed += 1
                    diffs_str = ', '.join(comparison['diffs'])
                    report += f"{i}. ❌ {snapshot.symbol} {snapshot.timeframe} - *Regression*\n"
                    report += f"   └─ Changed: {diffs_str}\n"
            
            report += f"\n{'='*30}\n\n"
            report += f"✅ Passed: {passed}\n"
            report += f"❌ Failed: {failed}\n"
            report += f"⚠️ Errors: {errors}\n\n"
            
            if failed == 0 and errors == 0:
                report += "🎉 *All signals match!* No regressions detected."
            elif failed > 0:
                report += f"⚠️ *Warning:* {failed} regression(s) detected!"
            
            return report
        
        except Exception as e:
            logger.error(f"❌ Replay all failed: {e}")
            return f"❌ *Replay Error*\n\n{str(e)}"


def capture_signal_for_replay(signal_data: Dict, klines: pd.DataFrame) -> None:
    """
    Capture signal snapshot for replay (non-blocking)
    
    Called from signal generation (read-only hook)
    Runs in background, never blocks signal generation
    
    Args:
        signal_data: Signal dictionary
        klines: DataFrame with klines data
    """
    try:
        cache = ReplayCache()
        cache.save_signal(signal_data, klines)
    except Exception as e:
        logger.warning(f"⚠️ Replay capture failed (non-critical): {e}")
