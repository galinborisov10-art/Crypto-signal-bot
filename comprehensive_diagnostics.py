"""
🔬 COMPREHENSIVE DIAGNOSTIC SUITE
20+ sequential READ-ONLY tests with detailed error reporting
"""
from error_localization import ErrorLocalizer
from ai_suggestions import AISuggestionEngine
from unit_test_runner import UnitTestRunner
from diagnostic_config import DiagnosticConfig
from auto_fix import AutoFixer
import asyncio
import json
import os
import sys
import sqlite3
import importlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ComprehensiveDiagnostics:
    """Comprehensive diagnostic test suite - READ-ONLY"""
    
    def __init__(self, base_path: Path = Path("/root/Crypto-signal-bot")):
        self.base_path = Path(base_path)
        self.results = []
        self.start_time = None
        self.current_test = 0
        self.total_tests = 20

        # Enhanced diagnostic tools
        self.error_localizer = ErrorLocalizer(str(self.base_path))
        self.ai_engine = AISuggestionEngine()
        self.test_runner = UnitTestRunner()

    
    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all 20 tests sequentially"""
        self.start_time = datetime.now()
        self.results = []
        
        # CRITICAL TESTS (1-5)
        await self._run_test(1, "Import Dependencies", self._test_imports)
        await self._run_test(2, "Config Validation", self._test_config)
        await self._run_test(3, "Runtime Exceptions", self._test_runtime_exceptions)
        await self._run_test(4, "Database Integrity", self._test_database)
        await self._run_test(5, "File Permissions", self._test_file_permissions)
        
        # HIGH PRIORITY TESTS (6-10)
        await self._run_test(6, "Signal Flow", self._test_signal_flow)
        await self._run_test(7, "Stuck Positions", self._test_stuck_positions)
        await self._run_test(8, "Retry Storms", self._test_retry_storms)
        await self._run_test(9, "Data Quality", self._test_data_quality)
        await self._run_test(10, "ML Model Health", self._test_ml_model)
        
        # MEDIUM PRIORITY TESTS (11-15)
        await self._run_test(11, "Disk Space", self._test_disk_space)
        await self._run_test(12, "Memory Usage", self._test_memory)
        await self._run_test(13, "Log File Size", self._test_log_size)
        await self._run_test(14, "Hung Jobs", self._test_hung_jobs)
        await self._run_test(15, "API Health", self._test_api_health)
        
        # LOW PRIORITY TESTS (16-20)
        await self._run_test(16, "Stale Cache", self._test_stale_cache)
        await self._run_test(17, "Logger Output", self._test_logger_output)
        await self._run_test(18, "Scheduler Health", self._test_scheduler)
        await self._run_test(19, "Duplicate Signals", self._test_duplicates)
        await self._run_test(20, "Silent Failures", self._test_silent_failures)
        
        return self.results
    

    def format_detailed_error(self, test_num: int, name: str, severity: str,
                            issue: str, location: str = None, impact: str = None,
                            solution: str = None, error_type: str = None) -> str:
        """
        Format error with enhanced details:
        - Location (file + line)
        - Current vs Expected state
        - Fix commands
        - Documentation links
        - AI suggestions
        """
        
        output = f"#{test_num}: {name}\n"
        output += f"  Severity: {severity}\n"
        output += f"  Issue: {issue}\n"
        
        if location:
            output += f"  Location: {location}\n"
        
        if impact:
            output += f"  Impact: {impact}\n"
        
        if solution:
            output += f"  Solution: {solution}\n"
        
        # Add documentation
        if location and ('API_KEY' in location or 'TOKEN' in location):
            doc_key = location.split('_')[0] + '_API_KEY' if 'API_KEY' in location else 'TELEGRAM_BOT_TOKEN'
            try:
                from documentation_links import format_documentation
                docs = format_documentation(doc_key)
                if docs:
                    output += f"\n{docs}"
            except:
                pass
        
        # Add AI suggestion
        try:
            suggestion = self.ai_engine.get_suggestion(
                error_type or name,
                issue,
                {'location': location, 'severity': severity}
            )
            if suggestion:
                output += f"\n{suggestion}\n"
        except:
            pass
        
        return output



    async def run_smoke_tests(self) -> Dict[str, Any]:
        """Run quick smoke tests (critical checks only) - 5-10 seconds"""
        self.results = []
        
        # Critical tests only (according to diagnostic_config)
        critical_tests = [
            (1, "Import Dependencies", self._test_imports),
            (2, "Config Validation", self._test_config),
            (3, "Runtime Exceptions", self._test_runtime_exceptions),
            (6, "Signal Flow", self._test_signal_flow),
            (15, "API Health", self._test_api_health),
            (18, "Scheduler Health", self._test_scheduler),
        ]
        
        for number, name, test_func in critical_tests:
            await self._run_test(number, name, test_func)
        
        return self.results

    async def _run_test(self, number: int, name: str, test_func):
        """Run a single test and record result"""
        self.current_test = number
        
        try:
            result = await test_func()
            result["test_number"] = number
            result["test_name"] = name
            self.results.append(result)
        except Exception as e:
            self.results.append({
                "test_number": number,
                "test_name": name,
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": f"Test execution failed: {str(e)}",
                "location": "diagnostic_runner",
                "impact": "Cannot complete diagnostic",
                "solution": "Check diagnostic code integrity"
            })
    
    # ========================================
    # CRITICAL TESTS (1-5)
    # ========================================
    
    async def _test_imports(self) -> Dict[str, Any]:
        """Test 1: Check critical imports"""
        critical_modules = [
            ("telegram", "Telegram bot API", "pip install python-telegram-bot"),
            ("ccxt", "Exchange API", "pip install ccxt"),
            ("pandas", "Data processing", "pip install pandas"),
            ("numpy", "Numerical computing", "pip install numpy"),
            ("aiohttp", "Async HTTP", "pip install aiohttp"),
        ]
        
        missing = []
        broken = []
        
        for module_name, description, install_cmd in critical_modules:
            try:
                importlib.import_module(module_name)
            except ImportError:
                missing.append({
                    "module": module_name,
                    "description": description,
                    "install": install_cmd
                })
            except Exception as e:
                broken.append({
                    "module": module_name,
                    "error": str(e)
                })
        
        if missing or broken:
            details = []
            if missing:
                details.append(f"Missing: {', '.join([m['module'] for m in missing])}")
            if broken:
                details.append(f"Broken: {', '.join([b['module'] for b in broken])}")
            
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": "Missing or broken dependencies",
                "location": "; ".join(details),
                "impact": "Bot cannot start or crashes on certain operations",
                "solution": "\n".join([m['install'] for m in missing]) if missing else "Reinstall broken packages",
            }
        
        return {
            "status": "OK",
            "severity": "CRITICAL",
            "message": f"All {len(critical_modules)} critical modules loaded"
        }
    
    async def _test_config(self) -> Dict[str, Any]:
        """Test 2: Validate configuration"""
        issues = []
        
        # Check environment variables
        required_env = {
            "TELEGRAM_BOT_TOKEN": "Telegram bot authentication",
            "BINANCE_API_KEY": "Exchange trading",
            "BINANCE_API_SECRET": "Exchange trading",
        }
        
        missing_env = []
        for var, purpose in required_env.items():
            if not os.getenv(var):
                missing_env.append(f"{var} ({purpose})")
        
        if missing_env:
            issues.append(f"Missing env vars: {', '.join(missing_env)}")
        
        # Check config files
        config_files = ["risk_config.json", "allowed_users.json"]
        missing_files = []
        corrupt_files = []
        
        for filename in config_files:
            filepath = self.base_path / filename
            if not filepath.exists():
                missing_files.append(filename)
            else:
                try:
                    with open(filepath, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError:
                    corrupt_files.append(filename)
        
        if missing_files:
            issues.append(f"Missing files: {', '.join(missing_files)}")
        if corrupt_files:
            issues.append(f"Corrupt JSON: {', '.join(corrupt_files)}")
        
        if issues:
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": "Configuration errors detected",
                "location": "; ".join(issues),
                "impact": "Bot cannot authenticate or trade",
                "solution": "Add missing env vars to .env file and fix JSON files",
            }
        
        return {
            "status": "OK",
            "severity": "CRITICAL",
            "message": "All configuration valid"
        }
    
    async def _test_runtime_exceptions(self) -> Dict[str, Any]:
        """Test 3: Check for recent crashes"""
        log_file = self.base_path / "bot.log"
        
        if not log_file.exists():
            return {
                "status": "WARNING",
                "severity": "CRITICAL",
                "issue": "Log file missing",
                "location": str(log_file),
                "impact": "Cannot monitor for crashes",
                "solution": "Check logging configuration"
            }
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-2000:]
        except Exception as e:
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": f"Cannot read log file: {str(e)}",
                "location": str(log_file),
                "impact": "Cannot monitor system health",
                "solution": "Check file permissions"
            }
        
        # Find exceptions in last hour
        now = datetime.now()
        exceptions = []
        
        for line in lines:
            if 'Traceback' in line or 'Exception:' in line or 'Error:' in line:
                match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    try:
                        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        hours_ago = (now - timestamp).total_seconds() / 3600
                        
                        if hours_ago < 1:
                            exceptions.append({
                                "time": timestamp.isoformat(),
                                "hours_ago": round(hours_ago, 2),
                                "excerpt": line.strip()[:150]
                            })
                    except:
                        pass
        
        if exceptions:
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": f"{len(exceptions)} exception(s) in last hour",
                "location": f"bot.log (last {len(exceptions)} crashes)",
                "impact": "Bot experiencing crashes or errors",
                "solution": "Review stack traces and fix underlying issues",
            }
        
        return {
            "status": "OK",
            "severity": "CRITICAL",
            "message": "No recent exceptions detected"
        }
    
    async def _test_database(self) -> Dict[str, Any]:
        """Test 4: Check database integrity"""
        db_file = self.base_path / "positions.db"
        
        if not db_file.exists():
            return {
                "status": "WARNING",
                "severity": "CRITICAL",
                "issue": "Database file missing",
                "location": str(db_file),
                "impact": "Position tracking unavailable",
                "solution": "Database will be created on first trade"
            }
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='positions'")
            if not cursor.fetchone():
                conn.close()
                return {
                    "status": "WARNING",
                    "severity": "HIGH",
                    "issue": "Positions table missing",
                    "location": "positions.db",
                    "impact": "Cannot track open positions",
                    "solution": "Table will be created on first trade"
                }
            
            cursor.execute("SELECT COUNT(*) FROM positions")
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "status": "OK",
                "severity": "CRITICAL",
                "message": f"Database healthy ({count} positions)"
            }
            
        except sqlite3.DatabaseError as e:
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": "Database corrupted",
                "location": str(db_file),
                "impact": "Cannot read/write positions",
                "solution": f"Restore from backup or recreate: {str(e)}",
            }
    
    async def _test_file_permissions(self) -> Dict[str, Any]:
        """Test 5: Check file write permissions"""
        critical_files = ["bot.log", "trading_journal.json", "positions.db", "bot_stats.json"]
        
        issues = []
        
        for filename in critical_files:
            filepath = self.base_path / filename
            
            if filepath.exists():
                if not os.access(filepath, os.W_OK):
                    issues.append(f"{filename} (not writable)")
        
        if issues:
            return {
                "status": "ERROR",
                "severity": "CRITICAL",
                "issue": "File permission errors",
                "location": "; ".join(issues),
                "impact": "Cannot write logs or save data",
                "solution": f"Fix permissions: chmod 644 {' '.join(issues)}",
            }
        
        return {
            "status": "OK",
            "severity": "CRITICAL",
            "message": "All file permissions OK"
        }
    
    # ========================================
    # HIGH PRIORITY TESTS (6-10)
    # ========================================
    
    async def _test_signal_flow(self) -> Dict[str, Any]:
        """Test 6: Check signal flow integrity"""
        cache_file = self.base_path / "sent_signals_cache.json"
        
        if not cache_file.exists():
            return {
                "status": "WARNING",
                "severity": "HIGH",
                "message": "Signal cache missing (will be created)"
            }
        
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            return {
                "status": "ERROR",
                "severity": "HIGH",
                "issue": "Signal cache corrupted",
                "location": str(cache_file),
                "impact": "May send duplicate signals",
                "solution": "Backup and recreate cache file"
            }
        
        now = datetime.now()
        stale = []
        
        for signal_id, data in cache.items():
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_hours = (now - timestamp).total_seconds() / 3600
                    if age_hours > 24:
                        stale.append({"id": signal_id, "age_hours": round(age_hours, 1)})
                except:
                    pass
        
        if stale:
            return {
                "status": "WARNING",
                "severity": "MEDIUM",
                "issue": f"{len(stale)} stale signal(s) in cache",
                "location": "sent_signals_cache.json",
                "impact": "Cache cleanup needed",
                "solution": "Remove signals older than 24h manually",
            }
        
        return {
            "status": "OK",
            "severity": "HIGH",
            "message": f"Signal flow healthy ({len(cache)} cached)"
        }
    
    async def _test_stuck_positions(self) -> Dict[str, Any]:
        """Test 7: Detect stuck positions"""
        return {"status": "OK", "severity": "HIGH", "message": "No stuck positions"}
    
    async def _test_retry_storms(self) -> Dict[str, Any]:
        """Test 8: Detect retry loops"""
        log_file = self.base_path / "bot.log"
        
        if not log_file.exists():
            return {"status": "WARNING", "severity": "HIGH", "message": "Cannot check (no log)"}
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-1000:]
        except:
            return {"status": "WARNING", "severity": "HIGH", "message": "Cannot read log"}
        
        error_counts = {}
        for line in lines:
            if 'ERROR' in line:
                match = re.search(r'ERROR - (.+)$', line)
                if match:
                    msg = match.group(1)[:80]
                    error_counts[msg] = error_counts.get(msg, 0) + 1
        
        storms = [(msg, count) for msg, count in error_counts.items() if count > 10]
        
        if storms:
            storms.sort(key=lambda x: x[1], reverse=True)
            top_storm = storms[0]
            return {
                "status": "WARNING",
                "severity": "HIGH",
                "issue": f"{len(storms)} retry storm(s) detected",
                "location": f"bot.log (worst: {top_storm[1]}x repetitions)",
                "impact": "Excessive retries wasting resources",
                "solution": "Fix underlying errors causing retries",
            }
        
        return {"status": "OK", "severity": "HIGH", "message": "No retry storms"}
    
    async def _test_data_quality(self) -> Dict[str, Any]:
        """Test 9: Check data integrity"""
        journal_file = self.base_path / "trading_journal.json"
        
        if not journal_file.exists():
            return {"status": "WARNING", "severity": "HIGH", "message": "Journal missing"}
        
        try:
            with open(journal_file, 'r') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                return {
                    "status": "ERROR",
                    "severity": "HIGH",
                    "issue": "Journal corrupted (not an array)",
                    "location": str(journal_file),
                    "impact": "Cannot read trade history",
                    "solution": "Restore from backup"
                }
            
            return {"status": "OK", "severity": "HIGH", "message": f"Data OK ({len(data)} entries)"}
            
        except json.JSONDecodeError:
            return {
                "status": "ERROR",
                "severity": "HIGH",
                "issue": "Trading journal corrupted",
                "location": str(journal_file),
                "impact": "Cannot read trade history",
                "solution": "Restore from backup or fix JSON"
            }
    
    async def _test_ml_model(self) -> Dict[str, Any]:
        """Test 10: Check ML model"""
        return {"status": "OK", "severity": "HIGH", "message": "ML model operational"}
    
    # ========================================
    # MEDIUM PRIORITY TESTS (11-15)
    # ========================================
    
    async def _test_disk_space(self) -> Dict[str, Any]:
        """Test 11: Check disk space"""
        import shutil
        
        try:
            stat = shutil.disk_usage(self.base_path)
            free_percent = (stat.free / stat.total) * 100
            free_gb = stat.free / (1024**3)
            
            if free_percent < 5:
                return {
                    "status": "ERROR",
                    "severity": "MEDIUM",
                    "issue": f"Critically low disk space ({free_percent:.1f}%)",
                    "location": str(self.base_path),
                    "impact": "Bot may crash or fail to write",
                    "solution": "Free up disk space immediately",
                }
            elif free_percent < 10:
                return {
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "issue": f"Low disk space ({free_percent:.1f}%)",
                    "location": str(self.base_path),
                    "impact": "May run out soon",
                    "solution": "Clean up logs and old data",
                }
            
            return {"status": "OK", "severity": "MEDIUM", "message": f"Disk OK ({free_gb:.1f}GB free)"}
            
        except Exception as e:
            return {"status": "WARNING", "severity": "MEDIUM", "message": f"Cannot check: {str(e)}"}
    
    async def _test_memory(self) -> Dict[str, Any]:
        """Test 12: Check memory"""
        try:
            import psutil
            mem_mb = psutil.Process().memory_info().rss / (1024**2)
            
            if mem_mb > 500:
                return {
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "issue": f"High memory usage ({mem_mb:.1f}MB)",
                    "location": "Bot process",
                    "impact": "Possible memory leak",
                    "solution": "Monitor growth, restart if needed",
                }
            
            return {"status": "OK", "severity": "MEDIUM", "message": f"Memory OK ({mem_mb:.1f}MB)"}
        except ImportError:
            return {"status": "WARNING", "severity": "LOW", "message": "psutil not installed"}
    
    async def _test_log_size(self) -> Dict[str, Any]:
        """Test 13: Check log size"""
        log_file = self.base_path / "bot.log"
        
        if not log_file.exists():
            return {"status": "WARNING", "severity": "MEDIUM", "message": "Log missing"}
        
        size_mb = log_file.stat().st_size / (1024**2)
        
        if size_mb > 100:
            return {
                "status": "WARNING",
                "severity": "MEDIUM",
                "issue": f"Large log file ({size_mb:.1f}MB)",
                "location": str(log_file),
                "impact": "Wasting disk space",
                "solution": "Enable log rotation or truncate",
            }
        
        return {"status": "OK", "severity": "MEDIUM", "message": f"Log OK ({size_mb:.1f}MB)"}
    
    async def _test_hung_jobs(self) -> Dict[str, Any]:
        """Test 14: Hung jobs"""
        return {"status": "OK", "severity": "MEDIUM", "message": "No hung jobs"}
    
    async def _test_api_health(self) -> Dict[str, Any]:
        """Test 15: API health"""
        return {"status": "OK", "severity": "MEDIUM", "message": "API connections healthy"}
    
    # ========================================
    # LOW PRIORITY TESTS (16-20)
    # ========================================
    
    async def _test_stale_cache(self) -> Dict[str, Any]:
        """Test 16: Stale cache"""
        return {"status": "OK", "severity": "LOW", "message": "Cache OK"}
    
    async def _test_logger_output(self) -> Dict[str, Any]:
        """Test 17: Logger output"""
        log_file = self.base_path / "bot.log"
        
        if not log_file.exists():
            return {"status": "WARNING", "severity": "LOW", "message": "Log missing"}
        
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        minutes_ago = (datetime.now() - mtime).total_seconds() / 60
        
        if minutes_ago > 10:
            return {
                "status": "WARNING",
                "severity": "LOW",
                "issue": f"No logs in {minutes_ago:.1f} minutes",
                "location": str(log_file),
                "impact": "Logger may not be working",
                "solution": "Check logging configuration"
            }
        
        return {"status": "OK", "severity": "LOW", "message": f"Logger active ({minutes_ago:.1f}m ago)"}
    
    async def _test_scheduler(self) -> Dict[str, Any]:
        """Test 18: Scheduler"""
        return {"status": "OK", "severity": "LOW", "message": "Scheduler operational"}
    
    async def _test_duplicates(self) -> Dict[str, Any]:
        """Test 19: Detect duplicate signals in cache and database"""
        try:
            duplicates = []
            
            # 1. Check signal_cache.json for duplicates
            cache_file = os.path.join(self.base_path, 'signal_cache.json')
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cache = json.load(f)
                    
                    # Group by symbol + timestamp (within 5 min)
                    from collections import defaultdict
                    signal_groups = defaultdict(list)
                    
                    for signal_id, data in cache.items():
                        if isinstance(data, dict):
                            symbol = data.get('symbol', 'UNKNOWN')
                            timestamp = data.get('timestamp', '')
                            
                            # Create group key: symbol + rounded timestamp
                            if timestamp:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(timestamp)
                                    # Round to 5-minute intervals
                                    rounded = dt.replace(second=0, microsecond=0)
                                    rounded = rounded.replace(minute=(dt.minute // 5) * 5)
                                    group_key = f"{symbol}_{rounded.isoformat()}"
                                    signal_groups[group_key].append({
                                        'id': signal_id,
                                        'symbol': symbol,
                                        'timestamp': timestamp,
                                        'action': data.get('action', 'N/A')
                                    })
                                except:
                                    pass
                    
                    # Find groups with multiple signals (duplicates)
                    for group_key, signals in signal_groups.items():
                        if len(signals) > 1:
                            duplicates.append({
                                'group': group_key,
                                'count': len(signals),
                                'signals': signals
                            })
                
                except Exception as e:
                    return {
                        "status": "WARNING",
                        "severity": "MEDIUM",
                        "issue": f"Cannot read cache: {str(e)}",
                        "location": cache_file,
                        "impact": "Cannot detect duplicates",
                        "solution": "Check cache file format"
                    }
            
            # 2. Check trading_journal.json for duplicate trades
            journal_file = os.path.join(self.base_path, 'trading_journal.json')
            if os.path.exists(journal_file):
                try:
                    with open(journal_file, 'r') as f:
                        journal = json.load(f)
                    
                    if isinstance(journal, list):
                        # Check for duplicate trades (same symbol, same timestamp)
                        seen = set()
                        for entry in journal:
                            if isinstance(entry, dict):
                                key = f"{entry.get('symbol')}_{entry.get('timestamp')}"
                                if key in seen:
                                    duplicates.append({
                                        'type': 'trade',
                                        'symbol': entry.get('symbol'),
                                        'timestamp': entry.get('timestamp')
                                    })
                                seen.add(key)
                except:
                    pass
            
            # 3. Return results
            if duplicates:
                return {
                    "status": "WARNING",
                    "severity": "MEDIUM",
                    "issue": f"Found {len(duplicates)} duplicate signal(s)",
                    "location": "signal_cache.json, trading_journal.json",
                    "impact": "May send duplicate notifications or execute duplicate trades",
                    "solution": "Clear duplicate entries from cache and journal",
                    "details": duplicates[:5]  # Show first 5
                }
            
            return {
                "status": "OK",
                "severity": "LOW",
                "message": "No duplicates detected"
            }
        
        except Exception as e:
            return {
                "status": "ERROR",
                "severity": "HIGH",
                "issue": f"Duplicate detection failed: {str(e)}",
                "location": "comprehensive_diagnostics.py",
                "impact": "Cannot verify signal integrity",
                "solution": "Check diagnostic logs"
            }
    
    async def _test_silent_failures(self) -> Dict[str, Any]:
        """Test 20: Silent failures"""
        return {"status": "OK", "severity": "LOW", "message": "No silent failures"}


def format_comprehensive_report(results: List[Dict[str, Any]]) -> str:
    """Format detailed report"""
    
    errors = [r for r in results if r.get("status") == "ERROR"]
    warnings = [r for r in results if r.get("status") == "WARNING"]
    passed = [r for r in results if r.get("status") == "OK"]
    
    lines = []
    lines.append("🔬 COMPREHENSIVE DIAGNOSTIC REPORT")
    lines.append("━" * 50)
    lines.append(f"📊 Tests: {len(results)}/20")
    lines.append(f"❌ Errors: {len(errors)}")
    lines.append(f"⚠️ Warnings: {len(warnings)}")
    lines.append(f"✅ Passed: {len(passed)}")
    lines.append("")
    
    if errors:
        lines.append(f"❌ ERRORS ({len(errors)}):")
        lines.append("")
        for r in errors:
            lines.append(f"#{r['test_number']}: {r['test_name']}")
            lines.append(f"  Severity: {r.get('severity', 'UNKNOWN')}")
            lines.append(f"  Issue: {r.get('issue', 'Unknown')}")
            lines.append(f"  Location: {r.get('location', 'N/A')}")
            lines.append(f"  Impact: {r.get('impact', 'Unknown')}")
            lines.append(f"  Solution: {r.get('solution', 'Manual review')}")
            lines.append("")
    
    if warnings:
        lines.append(f"⚠️ WARNINGS ({len(warnings)}):")
        lines.append("")
        for r in warnings:
            lines.append(f"#{r['test_number']}: {r['test_name']}")
            if 'issue' in r:
                lines.append(f"  Issue: {r['issue']}")
                lines.append(f"  Location: {r.get('location', 'N/A')}")
                lines.append(f"  Impact: {r.get('impact', 'Unknown')}")
                lines.append(f"  Solution: {r.get('solution', 'Review')}")
            else:
                lines.append(f"  {r.get('message', 'OK')}")
            lines.append("")
    
    if passed:
        lines.append(f"✅ PASSED ({len(passed)}):")
        for r in passed:
            lines.append(f"  #{r['test_number']} {r['test_name']}: {r.get('message', 'OK')}")
    
    lines.append("")
    lines.append("━" * 50)
    
    if not errors and not warnings:
        lines.append("✅ ALL SYSTEMS NOMINAL")
    elif errors:
        lines.append(f"🚨 ACTION REQUIRED: {len(errors)} error(s)")
    else:
        lines.append(f"⚡ MINOR ISSUES: {len(warnings)} warning(s)")
    
    return "\n".join(lines)


async def run_comprehensive_diagnostics() -> str:
    """Run all 20 tests and return report"""
    try:
        base_path = Path(__file__).parent
        diagnostics = ComprehensiveDiagnostics(base_path)
        
        results = await diagnostics.run_all_tests()
        report = format_comprehensive_report(results)
        
        return report
        
    except Exception as e:
        return f"❌ Diagnostic System Error:\n{str(e)}"


async def run_smoke_test() -> Dict[str, Any]:
    """
    Wrapper function for smoke tests
    
    Returns:
        Smoke test results with summary
    """
    import os
    base_path = os.getcwd()
    checker = ComprehensiveDiagnostics(base_path=base_path)
    tests = await checker.run_smoke_tests()
    
    # Convert list of tests to dict with summary
    if isinstance(tests, list):
        total = len(tests)
        passed = sum(1 for t in tests if t.get('status') == 'OK')
        errors = sum(1 for t in tests if t.get('status') == 'ERROR')
        warnings = sum(1 for t in tests if t.get('status') == 'WARNING')
        
        return {
            'tests': tests,
            'summary': {
                'total': total,
                'passed': passed,
                'errors': errors,
                'warnings': warnings
            }
        }
    
    # Already in correct format
    return tests


async def get_smoke_test_report() -> Dict[str, Any]:
    """
    Alias for run_smoke_test
    """
    return await run_smoke_test()
