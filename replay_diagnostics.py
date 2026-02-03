"""
🔄 REPLAY DIAGNOSTICS - Signal Flow & Stuck Detection
Tracks: created → sent → logged → executed
Detects: stuck positions, retry storms, hung jobs
"""

import json
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ReplayDiagnostics:
    """Diagnose signal flow and detect stuck/hung states"""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.journal_file = self.base_path / "trading_journal.json"
        self.cache_file = self.base_path / "sent_signals_cache.json"
        self.positions_db = self.base_path / "positions.db"
        self.log_file = self.base_path / "bot.log"
        
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all replay diagnostics"""
        results = {
            "signal_flow": await self.check_signal_flow(),
            "stuck_positions": await self.detect_stuck_positions(),
            "retry_storms": await self.detect_retry_storms(),
            "hung_jobs": await self.detect_hung_jobs(),
            "runtime_exceptions": await self.check_runtime_exceptions(),
            "duplicate_signals": await self.check_duplicate_signals(),
        }
        return results
    
    async def check_signal_flow(self) -> Dict[str, Any]:
        """Track signal lifecycle: created → sent → logged → executed"""
        try:
            # Load sent signals cache
            if not self.cache_file.exists():
                return {"status": "WARNING", "reason": "No cache file"}
            
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            
            # Check for stale signals (>24h old)
            stale_signals = []
            now = datetime.now()
            
            for signal_id, data in cache.items():
                timestamp = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                age_hours = (now - timestamp).total_seconds() / 3600
                
                if age_hours > 24:
                    stale_signals.append({
                        "id": signal_id,
                        "age_hours": round(age_hours, 1),
                        "timestamp": data.get('timestamp'),
                    })
            
            if stale_signals:
                return {
                    "status": "WARNING",
                    "stale_count": len(stale_signals),
                    "oldest": max(s['age_hours'] for s in stale_signals),
                    "signals": stale_signals[:5],  # Show first 5
                    "reason": f"{len(stale_signals)} stale signals in cache (>24h old)",
                }
            
            return {
                "status": "OK",
                "cache_size": len(cache),
                "reason": "Signal flow normal",
            }
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    async def detect_stuck_positions(self) -> Dict[str, Any]:
        """Detect positions stuck in processing"""
        try:
            # Check positions.db
            if not self.positions_db.exists():
                return {"status": "WARNING", "reason": "No positions.db"}
            
            conn = sqlite3.connect(self.positions_db)
            cursor = conn.cursor()
            
            # Try to find stuck positions
            try:
                cursor.execute("""
                    SELECT symbol, status, entry_time 
                    FROM positions 
                    WHERE status NOT IN ('closed', 'cancelled')
                    ORDER BY entry_time DESC
                    LIMIT 20
                """)
                rows = cursor.fetchall()
                
                if not rows:
                    conn.close()
                    return {"status": "OK", "reason": "No open positions"}
                
                # Check for positions stuck >24h
                stuck = []
                now = datetime.now()
                
                for symbol, status, entry_time in rows:
                    entry_dt = datetime.fromisoformat(entry_time)
                    age_hours = (now - entry_dt).total_seconds() / 3600
                    
                    if age_hours > 24:
                        stuck.append({
                            "symbol": symbol,
                            "status": status,
                            "age_hours": round(age_hours, 1),
                            "entry_time": entry_time,
                        })
                
                conn.close()
                
                if stuck:
                    return {
                        "status": "WARNING",
                        "stuck_count": len(stuck),
                        "positions": stuck,
                        "reason": f"{len(stuck)} positions stuck >24h",
                    }
                
                return {"status": "OK", "open_positions": len(rows)}
                
            except sqlite3.OperationalError as e:
                conn.close()
                if "no such table" in str(e):
                    return {"status": "WARNING", "reason": "positions table missing"}
                raise
                
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    async def detect_retry_storms(self) -> Dict[str, Any]:
        """Detect infinite retry loops"""
        try:
            if not self.log_file.exists():
                return {"status": "WARNING", "reason": "No log file"}
            
            # Read last 1000 lines
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[-1000:]
            
            # Count repeated error patterns
            error_counts = {}
            
            for line in lines:
                if 'ERROR' in line or 'Exception' in line:
                    # Extract error message (simplified)
                    match = re.search(r'ERROR - (.+)$', line)
                    if match:
                        error_msg = match.group(1)[:100]  # First 100 chars
                        error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
            
            # Find retry storms (same error >10 times)
            storms = []
            for msg, count in error_counts.items():
                if count > 10:
                    storms.append({"message": msg, "count": count})
            
            if storms:
                # Sort by count
                storms.sort(key=lambda x: x['count'], reverse=True)
                return {
                    "status": "WARNING",
                    "storm_count": len(storms),
                    "storms": storms[:3],  # Top 3
                    "reason": f"{len(storms)} retry storms detected",
                }
            
            return {"status": "OK", "reason": "No retry storms"}
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    async def detect_hung_jobs(self) -> Dict[str, Any]:
        """Detect jobs that haven't run in expected interval"""
        try:
            if not self.log_file.exists():
                return {"status": "WARNING", "reason": "No log file"}
            
            # Check for scheduled job logs
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[-5000:]  # Last 5000 lines
            
            # Track last run times
            job_last_run = {}
            
            for line in lines:
                # Look for job execution patterns
                if 'auto_signal_job' in line:
                    match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if match:
                        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        job_last_run['auto_signal_job'] = timestamp
            
            # Check if jobs are hung (>6h since last run)
            hung_jobs = []
            now = datetime.now()
            
            for job_name, last_run in job_last_run.items():
                hours_since = (now - last_run).total_seconds() / 3600
                if hours_since > 6:
                    hung_jobs.append({
                        "job": job_name,
                        "hours_since_run": round(hours_since, 1),
                        "last_run": last_run.isoformat(),
                    })
            
            if hung_jobs:
                return {
                    "status": "WARNING",
                    "hung_count": len(hung_jobs),
                    "jobs": hung_jobs,
                    "reason": f"{len(hung_jobs)} jobs haven't run in >6h",
                }
            
            return {"status": "OK", "jobs_tracked": len(job_last_run)}
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    async def check_runtime_exceptions(self) -> Dict[str, Any]:
        """Check for recent runtime exceptions"""
        try:
            if not self.log_file.exists():
                return {"status": "WARNING", "reason": "No log file"}
            
            # Read last 2000 lines
            with open(self.log_file, 'r') as f:
                lines = f.readlines()[-2000:]
            
            # Find exceptions in last hour
            now = datetime.now()
            recent_exceptions = []
            
            for line in lines:
                if 'Traceback' in line or 'Exception' in line:
                    # Try to extract timestamp
                    match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if match:
                        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        hours_ago = (now - timestamp).total_seconds() / 3600
                        
                        if hours_ago < 1:  # Last hour
                            recent_exceptions.append({
                                "time": timestamp.isoformat(),
                                "hours_ago": round(hours_ago, 2),
                                "excerpt": line.strip()[:150],
                            })
            
            if recent_exceptions:
                return {
                    "status": "WARNING",
                    "exception_count": len(recent_exceptions),
                    "exceptions": recent_exceptions[:5],
                    "reason": f"{len(recent_exceptions)} exceptions in last hour",
                }
            
            return {"status": "OK", "reason": "No recent exceptions"}
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}
    
    async def check_duplicate_signals(self) -> Dict[str, Any]:
        """Check for duplicate signals sent within short timeframe"""
        try:
            if not self.cache_file.exists():
                return {"status": "WARNING", "reason": "No cache file"}
            
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            
            # Group signals by symbol+action
            signal_groups = {}
            
            for signal_id, data in cache.items():
                # Extract symbol and action from ID (e.g., "BTCUSDT_BUY_4h")
                parts = signal_id.split('_')
                if len(parts) >= 2:
                    key = f"{parts[0]}_{parts[1]}"  # symbol_action
                    
                    if key not in signal_groups:
                        signal_groups[key] = []
                    
                    signal_groups[key].append({
                        "id": signal_id,
                        "timestamp": data.get('timestamp'),
                        "price": data.get('entry_price'),
                    })
            
            # Find duplicates (same symbol+action with multiple entries)
            duplicates = []
            for key, signals in signal_groups.items():
                if len(signals) > 1:
                    duplicates.append({
                        "symbol_action": key,
                        "count": len(signals),
                        "signals": signals,
                    })
            
            if duplicates:
                return {
                    "status": "WARNING",
                    "duplicate_groups": len(duplicates),
                    "duplicates": duplicates[:3],
                    "reason": f"{len(duplicates)} potential duplicate signals",
                }
            
            return {"status": "OK", "reason": "No duplicates detected"}
            
        except Exception as e:
            return {"status": "ERROR", "reason": str(e)}


async def format_replay_report(results: Dict[str, Any]) -> str:
    """Format replay diagnostics into readable report"""
    
    lines = []
    lines.append("🔄 REPLAY DIAGNOSTICS REPORT")
    lines.append("━" * 50)
    
    for check_name, result in results.items():
        status = result.get('status', 'UNKNOWN')
        reason = result.get('reason', 'No details')
        
        emoji = "✅" if status == "OK" else "⚠️" if status == "WARNING" else "❌"
        
        lines.append(f"\n{emoji} {check_name.replace('_', ' ').title()}")
        lines.append(f"   Status: {status}")
        lines.append(f"   {reason}")
        
        # Add details based on check type
        if check_name == "stuck_positions" and result.get('positions'):
            lines.append(f"   Stuck positions:")
            for pos in result['positions'][:3]:
                lines.append(f"     • {pos['symbol']} ({pos['age_hours']}h old)")
        
        elif check_name == "retry_storms" and result.get('storms'):
            lines.append(f"   Top storms:")
            for storm in result['storms']:
                lines.append(f"     • {storm['count']}x: {storm['message'][:60]}...")
        
        elif check_name == "hung_jobs" and result.get('jobs'):
            lines.append(f"   Hung jobs:")
            for job in result['jobs']:
                lines.append(f"     • {job['job']} ({job['hours_since_run']}h ago)")
    
    lines.append("\n" + "━" * 50)
    return "\n".join(lines)

