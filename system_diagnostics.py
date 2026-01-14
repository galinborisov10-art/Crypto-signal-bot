#!/usr/bin/env python3
"""
🏥 System Health Monitoring with Root Cause Analysis
Provides intelligent diagnostics for all bot components with actionable fixes
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


# ==================== LOG PARSING UTILITIES ====================

def grep_logs(pattern: str, hours: int = 6, base_path: str = None) -> List[str]:
    """
    Grep logs for pattern in last N hours
    
    Args:
        pattern: String pattern to search for
        hours: Look back N hours
        base_path: Base path for bot files
    
    Returns:
        List of matching log lines
    """
    try:
        if base_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        log_file = f'{base_path}/bot.log'
        
        if not os.path.exists(log_file):
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        matching_lines = []
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            # Read last 10k lines for performance
            lines = f.readlines()
            for line in lines[-10000:]:
                try:
                    # Parse timestamp (format: 2026-01-14 10:45:43,746)
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        
                        if log_time > cutoff_time and pattern in line:
                            matching_lines.append(line.strip())
                except Exception:
                    # If timestamp parsing fails, check pattern anyway (better safe than sorry)
                    if pattern in line:
                        matching_lines.append(line.strip())
        
        return matching_lines
    except Exception as e:
        logger.error(f"❌ Error grepping logs: {e}")
        return []


def load_journal_safe(base_path: str = None) -> Optional[Dict]:
    """
    Safely load trading journal
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        Journal dict or None if failed
    """
    try:
        if base_path is None:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        journal_file = f'{base_path}/trading_journal.json'
        
        if not os.path.exists(journal_file):
            return None
        
        with open(journal_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"❌ Error loading journal: {e}")
        return None


# ==================== TRADING JOURNAL DIAGNOSTICS ====================

async def diagnose_journal_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Deep diagnosis of trading journal problems
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found with root cause analysis
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    journal_file = f'{base_path}/trading_journal.json'
    
    # ==================== CHECK 1: FILE EXISTENCE ====================
    if not os.path.exists(journal_file):
        issues.append({
            'problem': 'Journal file missing',
            'root_cause': 'File was deleted or never created',
            'evidence': f'File not found at: {journal_file}',
            'fix': 'Bot will auto-create on next signal. If persists, check BASE_PATH detection.',
            'commands': [
                f'ls -lah {journal_file}',
                f'grep "BASE_PATH" {base_path}/bot.log | tail -n 5'
            ]
        })
        return issues
    
    # ==================== CHECK 2: FILE PERMISSIONS ====================
    try:
        file_stat = os.stat(journal_file)
        permissions = oct(file_stat.st_mode)[-3:]
        
        if permissions not in ['644', '664', '666']:
            issues.append({
                'problem': f'Incorrect file permissions: {permissions}',
                'root_cause': 'File permissions were changed manually or by system',
                'evidence': f'Expected: 644, Found: {permissions}',
                'fix': f'Fix permissions with: chmod 644 {journal_file}',
                'commands': [f'ls -lah {journal_file}']
            })
    except Exception as e:
        issues.append({
            'problem': 'Cannot check file permissions',
            'root_cause': str(e),
            'evidence': f'os.stat() failed on {journal_file}',
            'fix': 'Check if file is accessible and not corrupted',
            'commands': [f'ls -lah {journal_file}']
        })
    
    # ==================== CHECK 3: LAST UPDATE TIME ====================
    journal = load_journal_safe(base_path)
    if journal and 'trades' in journal and len(journal['trades']) > 0:
        try:
            last_trade = journal['trades'][-1]
            last_trade_time = datetime.fromisoformat(last_trade['timestamp'])
            hours_lag = (datetime.now() - last_trade_time).total_seconds() / 3600
            
            if hours_lag > 6:
                # Deep dive: WHY no updates?
                
                # Sub-check 3a: Auto-signals running?
                auto_signal_logs = grep_logs('auto_signal_job', hours=6, base_path=base_path)
                
                if not auto_signal_logs:
                    issues.append({
                        'problem': f'Journal not updated for {hours_lag:.1f}h',
                        'root_cause': 'Auto-signal jobs are NOT running',
                        'evidence': 'No auto_signal_job logs in last 6 hours',
                        'fix': 'Scheduler may have crashed. Check scheduler status.',
                        'commands': [
                            f'grep "auto_signal_job" {base_path}/bot.log | tail -n 20',
                            f'grep "APScheduler" {base_path}/bot.log | tail -n 10'
                        ]
                    })
                else:
                    # Sub-check 3b: Signals generated but not logged?
                    signal_complete_logs = grep_logs('ICT Signal COMPLETE', hours=6, base_path=base_path)
                    journal_logged_logs = grep_logs('Trade.*logged', hours=6, base_path=base_path)
                    
                    if signal_complete_logs and not journal_logged_logs:
                        # Signals generated but NOT logged - find error
                        journal_errors = grep_logs('ERROR.*journal', hours=6, base_path=base_path)
                        
                        if journal_errors:
                            # Found the error!
                            latest_error = journal_errors[-1]
                            
                            # Parse error to find root cause
                            if 'AttributeError' in latest_error:
                                attr_match = re.search(r"'(\w+)' object has no attribute '(\w+)'", latest_error)
                                if attr_match:
                                    obj_name = attr_match.group(1)
                                    attr_name = attr_match.group(2)
                                    
                                    issues.append({
                                        'problem': 'Journal logging fails with AttributeError',
                                        'root_cause': f'{obj_name} object missing attribute: {attr_name}',
                                        'evidence': latest_error,
                                        'fix': f'Code tries to access {obj_name}.{attr_name} which does not exist. Check ICTSignal class definition.',
                                        'code_location': 'bot.py lines ~9900-10200 (auto_signal_job)',
                                        'commands': [
                                            f'grep -n "{attr_name}" {base_path}/bot.py | head -n 10',
                                            f'grep -n "class {obj_name}" {base_path}/*.py'
                                        ]
                                    })
                            
                            elif 'PermissionError' in latest_error:
                                issues.append({
                                    'problem': 'Journal logging fails with PermissionError',
                                    'root_cause': 'Bot lacks write permissions to journal file',
                                    'evidence': latest_error,
                                    'fix': f'Fix permissions: sudo chown $USER:$USER {journal_file} && chmod 644 {journal_file}',
                                    'commands': [f'ls -lah {journal_file}']
                                })
                            
                            elif 'JSONDecodeError' in latest_error:
                                issues.append({
                                    'problem': 'Journal logging fails - corrupted JSON',
                                    'root_cause': 'trading_journal.json is corrupted or has invalid JSON',
                                    'evidence': latest_error,
                                    'fix': f'Restore from backup or validate JSON: python3 -m json.tool {journal_file}',
                                    'commands': [
                                        f'tail -n 50 {journal_file}',
                                        f'python3 -c "import json; json.load(open(\'{journal_file}\'))"'
                                    ]
                                })
                            
                            else:
                                # Generic error - show full error
                                issues.append({
                                    'problem': 'Journal logging fails with unknown error',
                                    'root_cause': 'Check error details below',
                                    'evidence': latest_error,
                                    'fix': 'Review error and check log_trade_to_journal() function',
                                    'commands': [
                                        f'grep -B 5 -A 10 "def log_trade_to_journal" {base_path}/bot.py | head -n 30'
                                    ]
                                })
                        
                        else:
                            # Signals generated, no errors, but not logged - logic issue
                            issues.append({
                                'problem': 'Signals generated but not logged to journal',
                                'root_cause': 'log_trade_to_journal() is not being called OR returns silently',
                                'evidence': f'{len(signal_complete_logs)} signals generated, 0 journal entries',
                                'fix': 'Check if log_trade_to_journal() is called after signal generation',
                                'code_location': 'bot.py - auto_signal_job function',
                                'commands': [
                                    f'grep -n "log_trade_to_journal" {base_path}/bot.py'
                                ]
                            })
        except Exception as e:
            logger.error(f"❌ Error checking journal update time: {e}")
    
    # ==================== CHECK 4: METADATA VS ACTUAL COUNT ====================
    if journal and 'metadata' in journal and 'trades' in journal:
        try:
            metadata_count = journal['metadata'].get('total_trades', 0)
            actual_count = len(journal['trades'])
            
            if metadata_count != actual_count:
                issues.append({
                    'problem': f'Metadata mismatch: {metadata_count} expected, {actual_count} actual',
                    'root_cause': 'Journal was manually edited or corrupted',
                    'evidence': f'Difference: {abs(metadata_count - actual_count)} trades',
                    'fix': 'Auto-repair: Run /health again to trigger automatic metadata sync',
                    'commands': [
                        'python3 -c "import json; j=json.load(open(\'trading_journal.json\')); print(f\'Metadata: {j[\\\"metadata\\\"][\\\"total_trades\\\"]}, Actual: {len(j[\\\"trades\\\"])}\')"'
                    ]
                })
        except Exception as e:
            logger.error(f"❌ Error checking metadata: {e}")
    
    return issues


# ==================== ML TRAINING DIAGNOSTICS ====================

async def diagnose_ml_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Deep diagnosis of ML training problems
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found with root cause analysis
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    ml_model_file = f'{base_path}/ml_model.pkl'
    ml_scaler_file = f'{base_path}/ml_scaler.pkl'
    
    # ==================== CHECK 1: MODEL FILE EXISTS ====================
    if not os.path.exists(ml_model_file):
        issues.append({
            'problem': 'ML model file missing',
            'root_cause': 'Model was never trained or file was deleted',
            'evidence': 'ml_model.pkl not found',
            'fix': 'Run manual ML training or wait for weekly auto-training (Sunday 03:00 UTC)',
            'commands': [
                f'ls -lah {ml_model_file} {ml_scaler_file}',
                f'grep "ML.*train" {base_path}/bot.log | tail -n 20'
            ]
        })
        return issues
    
    # ==================== CHECK 2: MODEL AGE ====================
    try:
        last_trained = datetime.fromtimestamp(os.path.getmtime(ml_model_file))
        days_old = (datetime.now() - last_trained).days
        
        if days_old > 10:
            # Deep dive: WHY not trained?
            
            # Sub-check 2a: Weekly job running?
            ml_training_logs = grep_logs('ml_auto_training_job', hours=7*24, base_path=base_path)
            
            if not ml_training_logs:
                issues.append({
                    'problem': f'ML model not trained for {days_old} days',
                    'root_cause': 'Weekly ML training job is NOT running',
                    'evidence': 'No ml_auto_training_job logs in last 7 days',
                    'fix': 'Scheduler issue. Check if ML training job is registered.',
                    'code_location': 'bot.py - ML AUTO-TRAINING SCHEDULER section',
                    'commands': [
                        f'grep "ML AUTO-TRAINING" {base_path}/bot.log | tail -n 10',
                        f'grep "ml_auto_training_job" {base_path}/bot.log | tail -n 20'
                    ]
                })
            else:
                # Sub-check 2b: Job ran but failed?
                ml_errors = grep_logs('ERROR.*ml.*train', hours=7*24, base_path=base_path)
                
                if ml_errors:
                    latest_error = ml_errors[-1]
                    
                    # Parse error type
                    if 'No trading journal found' in latest_error:
                        issues.append({
                            'problem': f'ML model not trained for {days_old} days',
                            'root_cause': 'trading_journal.json not found during training',
                            'evidence': latest_error,
                            'fix': 'Check if trading_journal.json exists and is readable',
                            'commands': [
                                f'ls -lah {base_path}/trading_journal.json'
                            ]
                        })
                    
                    elif 'Minimum 50 trades' in latest_error or 'not enough data' in latest_error.lower():
                        journal = load_journal_safe(base_path)
                        if journal and 'trades' in journal:
                            completed_trades = len([
                                t for t in journal['trades'] 
                                if t.get('status') in ['WIN', 'LOSS', 'COMPLETED']
                            ])
                            
                            issues.append({
                                'problem': f'ML model not trained for {days_old} days',
                                'root_cause': f'Not enough completed trades ({completed_trades}/50 minimum)',
                                'evidence': latest_error,
                                'fix': f'Need {50 - completed_trades} more completed trades. Wait for more signals to close.',
                                'note': 'ML training requires minimum 50 completed trades (WIN/LOSS)'
                            })
                        else:
                            issues.append({
                                'problem': f'ML model not trained for {days_old} days',
                                'root_cause': 'Not enough data in trading journal',
                                'evidence': latest_error,
                                'fix': 'Generate more trading signals and wait for them to complete'
                            })
                    
                    elif 'MemoryError' in latest_error or 'Cannot allocate memory' in latest_error:
                        issues.append({
                            'problem': f'ML model not trained for {days_old} days',
                            'root_cause': 'Out of memory during training',
                            'evidence': latest_error,
                            'fix': 'Restart bot to free memory or upgrade server RAM',
                            'commands': [
                                'free -h',
                                'sudo systemctl restart crypto-bot'
                            ]
                        })
                    
                    else:
                        # Generic error
                        issues.append({
                            'problem': f'ML model not trained for {days_old} days',
                            'root_cause': 'Training failed with error (see evidence)',
                            'evidence': latest_error,
                            'fix': 'Review error details and check ml_predictor.py/ml_engine.py',
                            'commands': [
                                f'grep -B 10 -A 10 "def train" {base_path}/ml_predictor.py | head -n 30'
                            ]
                        })
                
                else:
                    # Job ran, no errors, but model not updated - strange
                    issues.append({
                        'problem': f'ML model not trained for {days_old} days',
                        'root_cause': 'Training job runs but model file not updated',
                        'evidence': f'Last training log: {ml_training_logs[-1][:100]}...' if ml_training_logs else 'No logs',
                        'fix': 'Check if training actually completes and saves model',
                        'commands': [
                            f'grep -A 20 "ml_auto_training_job" {base_path}/bot.log | tail -n 40'
                        ]
                    })
    except Exception as e:
        logger.error(f"❌ Error checking ML model age: {e}")
    
    return issues


# ==================== DAILY REPORT DIAGNOSTICS ====================

async def diagnose_daily_report_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Check if yesterday's daily report was sent
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check for daily report execution in last 24 hours
    daily_report_logs = grep_logs('Daily report sent successfully', hours=24, base_path=base_path)
    
    if not daily_report_logs:
        # Check if scheduled
        scheduler_logs = grep_logs('Daily reports scheduled', hours=24*7, base_path=base_path)
        
        if not scheduler_logs:
            issues.append({
                'problem': 'Daily report not sent in last 24 hours',
                'root_cause': 'Daily report job is NOT scheduled',
                'evidence': 'No "Daily reports scheduled" log found',
                'fix': 'Check scheduler initialization in bot.py',
                'code_location': 'bot.py - schedule_reports function',
                'commands': [
                    f'grep "Daily reports scheduled" {base_path}/bot.log | tail -n 5'
                ]
            })
        else:
            # Scheduled but not executed - check for errors
            report_errors = grep_logs('ERROR.*Daily report', hours=24, base_path=base_path)
            
            if report_errors:
                issues.append({
                    'problem': 'Daily report not sent in last 24 hours',
                    'root_cause': 'Daily report job failed with error',
                    'evidence': report_errors[-1],
                    'fix': 'Check report generation logic and data availability',
                    'commands': [
                        f'grep "Daily report" {base_path}/bot.log | tail -n 20'
                    ]
                })
            else:
                issues.append({
                    'problem': 'Daily report not sent in last 24 hours',
                    'root_cause': 'Unknown - job scheduled but not executed',
                    'evidence': 'No error logs, but no success logs either',
                    'fix': 'Check APScheduler status and misfire_grace_time setting',
                    'commands': [
                        f'grep "APScheduler" {base_path}/bot.log | tail -n 20'
                    ]
                })
    
    return issues


# ==================== POSITION MONITOR DIAGNOSTICS ====================

async def diagnose_position_monitor_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Check for position monitor errors
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check for position monitor errors in last hour
    position_errors = grep_logs('ERROR.*position', hours=1, base_path=base_path)
    
    if position_errors:
        issues.append({
            'problem': f'{len(position_errors)} position monitor errors in last hour',
            'root_cause': 'Position monitoring encountering errors',
            'evidence': position_errors[-1],
            'fix': 'Check position_manager.py and database connectivity',
            'commands': [
                f'grep "ERROR.*position" {base_path}/bot.log | tail -n 10'
            ]
        })
    
    return issues


# ==================== SCHEDULER DIAGNOSTICS ====================

async def diagnose_scheduler_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Check for scheduler health
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check for scheduler errors
    scheduler_errors = grep_logs('ERROR.*scheduler|ERROR.*APScheduler', hours=12, base_path=base_path)
    
    if scheduler_errors:
        issues.append({
            'problem': f'{len(scheduler_errors)} scheduler errors in last 12 hours',
            'root_cause': 'APScheduler encountering errors',
            'evidence': scheduler_errors[-1],
            'fix': 'Check scheduler job definitions and error handling',
            'commands': [
                f'grep "ERROR.*scheduler" {base_path}/bot.log | tail -n 10'
            ]
        })
    
    # Check for missed jobs
    misfire_logs = grep_logs('misfire', hours=12, base_path=base_path)
    
    if misfire_logs:
        issues.append({
            'problem': f'{len(misfire_logs)} job misfires in last 12 hours',
            'root_cause': 'Scheduled jobs are missing their execution window',
            'evidence': misfire_logs[-1],
            'fix': 'Check bot uptime and misfire_grace_time settings',
            'commands': [
                f'grep "misfire" {base_path}/bot.log | tail -n 10'
            ]
        })
    
    return issues


# ==================== DISK SPACE DIAGNOSTICS ====================

async def diagnose_disk_space_issue(base_path: str = None) -> List[Dict[str, Any]]:
    """
    Check disk space availability
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        List of issues found
    """
    issues = []
    
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    try:
        import shutil
        
        total, used, free = shutil.disk_usage(base_path)
        
        # Convert to GB
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        used_percent = (used / total) * 100
        
        if used_percent > 90:
            issues.append({
                'problem': f'Disk space critically low: {used_percent:.1f}% used',
                'root_cause': 'Disk is nearly full',
                'evidence': f'Used: {used_gb:.2f}GB / {total_gb:.2f}GB, Free: {free_gb:.2f}GB',
                'fix': 'Clean up old logs, backups, or temporary files',
                'commands': [
                    f'du -sh {base_path}/*',
                    f'df -h {base_path}'
                ]
            })
        elif used_percent > 80:
            issues.append({
                'problem': f'Disk space running low: {used_percent:.1f}% used',
                'root_cause': 'Disk usage is high',
                'evidence': f'Used: {used_gb:.2f}GB / {total_gb:.2f}GB, Free: {free_gb:.2f}GB',
                'fix': 'Monitor disk usage and plan cleanup',
                'commands': [
                    f'du -sh {base_path}/*',
                    f'df -h {base_path}'
                ]
            })
    except Exception as e:
        logger.error(f"❌ Error checking disk space: {e}")
    
    return issues


# ==================== COMPREHENSIVE HEALTH CHECK ====================

async def run_full_health_check(base_path: str = None) -> Dict[str, Any]:
    """
    Run all diagnostic checks and return comprehensive report
    
    Args:
        base_path: Base path for bot files
    
    Returns:
        Dict with health status for all components
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Run all diagnostics
    journal_issues = await diagnose_journal_issue(base_path)
    ml_issues = await diagnose_ml_issue(base_path)
    daily_report_issues = await diagnose_daily_report_issue(base_path)
    position_issues = await diagnose_position_monitor_issue(base_path)
    scheduler_issues = await diagnose_scheduler_issue(base_path)
    disk_issues = await diagnose_disk_space_issue(base_path)
    
    # Compile results with explicit severity
    health_report['components']['trading_journal'] = {
        'status': 'CRITICAL' if any('missing' in str(i.get('problem', '')) for i in journal_issues) else 'WARNING' if journal_issues else 'HEALTHY',
        'issues': journal_issues
    }
    
    health_report['components']['ml_model'] = {
        'status': 'CRITICAL' if any('missing' in str(i.get('problem', '')) for i in ml_issues) else 'WARNING' if ml_issues else 'HEALTHY',
        'issues': ml_issues
    }
    
    health_report['components']['daily_reports'] = {
        'status': 'WARNING' if daily_report_issues else 'HEALTHY',
        'issues': daily_report_issues
    }
    
    health_report['components']['position_monitor'] = {
        'status': 'CRITICAL' if len(position_issues) > 5 else 'WARNING' if position_issues else 'HEALTHY',
        'issues': position_issues
    }
    
    health_report['components']['scheduler'] = {
        'status': 'CRITICAL' if len(scheduler_issues) > 3 else 'WARNING' if scheduler_issues else 'HEALTHY',
        'issues': scheduler_issues
    }
    
    health_report['components']['disk_space'] = {
        'status': 'CRITICAL' if any('critically low' in str(i.get('problem', '')) for i in disk_issues) else 'WARNING' if disk_issues else 'HEALTHY',
        'issues': disk_issues
    }
    
    # Count statuses
    statuses = [comp['status'] for comp in health_report['components'].values()]
    health_report['summary'] = {
        'healthy': statuses.count('HEALTHY'),
        'warning': statuses.count('WARNING'),
        'critical': statuses.count('CRITICAL')
    }
    
    return health_report
