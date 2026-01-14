#!/usr/bin/env python3
"""
💬 Diagnostic Message Formatting
Formats health alerts and reports for Telegram with copy-paste friendly layout
"""

from datetime import datetime
from typing import Dict, List, Any


def get_status_emoji(status: str) -> str:
    """Get emoji for health status"""
    return {
        'HEALTHY': '✅',
        'WARNING': '⚠️',
        'CRITICAL': '❌'
    }.get(status, '❓')


def format_issue_alert(component_name: str, issue: Dict[str, Any]) -> str:
    """
    Format a single issue as Telegram alert message
    
    Args:
        component_name: Name of component (e.g., "TRADING JOURNAL")
        issue: Issue dict with problem, root_cause, evidence, fix, etc.
    
    Returns:
        Formatted Telegram message
    """
    # Determine severity
    severity = '❌ CRITICAL' if 'critical' in issue.get('problem', '').lower() else '⚠️ WARNING'
    
    message = f"""🚨 <b>{component_name.upper()} HEALTH ALERT</b>

📊 Status: {severity}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 <b>PROBLEM:</b>
{issue.get('problem', 'Unknown issue')}

🔍 <b>ROOT CAUSE:</b>
{issue.get('root_cause', 'Unknown cause')}

📋 <b>EVIDENCE:</b>
<code>{issue.get('evidence', 'No evidence available')[:500]}</code>"""
    
    # Add code location if available
    if 'code_location' in issue:
        message += f"\n\n📍 <b>CODE LOCATION:</b>\n{issue['code_location']}"
    
    # Add fix suggestion
    message += f"\n\n💡 <b>FIX:</b>\n{issue.get('fix', 'Manual investigation required')}"
    
    # Add note if available
    if 'note' in issue:
        message += f"\n\n📌 <b>NOTE:</b>\n{issue['note']}"
    
    # Add debug commands
    if 'commands' in issue and issue['commands']:
        message += "\n\n🔧 <b>DEBUG COMMANDS:</b>\n<pre>"
        for cmd in issue['commands'][:3]:  # Limit to 3 commands
            message += f"\n{cmd}"
        message += "</pre>"
    
    message += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Use /health for full system check
📌 Copy this message to Copilot for instant fix"""
    
    return message


def format_health_summary(health_report: Dict[str, Any]) -> str:
    """
    Format comprehensive health report for /health command
    
    Args:
        health_report: Full health check report
    
    Returns:
        Formatted Telegram message
    """
    components = health_report.get('components', {})
    summary = health_report.get('summary', {})
    
    message = """🏥 <b>SYSTEM HEALTH DIAGNOSTIC</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
    
    # Trading Journal
    journal = components.get('trading_journal', {})
    journal_status = journal.get('status', 'UNKNOWN')
    journal_emoji = get_status_emoji(journal_status)
    
    message += f"📝 <b>TRADING JOURNAL:</b> {journal_emoji} {journal_status}\n"
    
    if journal.get('issues'):
        for issue in journal['issues'][:1]:  # Show first issue only
            message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        # Get journal stats
        message += "   Status: Updating correctly\n"
    
    # ML Model
    ml = components.get('ml_model', {})
    ml_status = ml.get('status', 'UNKNOWN')
    ml_emoji = get_status_emoji(ml_status)
    
    message += f"\n🤖 <b>ML MODEL:</b> {ml_emoji} {ml_status}\n"
    
    if ml.get('issues'):
        for issue in ml['issues'][:1]:
            message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        message += "   Status: Up to date\n"
    
    # Daily Reports
    reports = components.get('daily_reports', {})
    reports_status = reports.get('status', 'UNKNOWN')
    reports_emoji = get_status_emoji(reports_status)
    
    message += f"\n📊 <b>DAILY REPORTS:</b> {reports_emoji} {reports_status}\n"
    
    if reports.get('issues'):
        for issue in reports['issues'][:1]:
            message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        message += "   Status: Executing on schedule\n"
    
    # Position Monitor
    position = components.get('position_monitor', {})
    position_status = position.get('status', 'UNKNOWN')
    position_emoji = get_status_emoji(position_status)
    
    message += f"\n⚙️ <b>POSITION MONITOR:</b> {position_emoji} {position_status}\n"
    
    if position.get('issues'):
        for issue in position['issues'][:1]:
            message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        message += "   Status: Monitoring active trades\n"
    
    # Scheduler
    scheduler = components.get('scheduler', {})
    scheduler_status = scheduler.get('status', 'UNKNOWN')
    scheduler_emoji = get_status_emoji(scheduler_status)
    
    message += f"\n⏰ <b>SCHEDULER:</b> {scheduler_emoji} {scheduler_status}\n"
    
    if scheduler.get('issues'):
        for issue in scheduler['issues'][:1]:
            message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        message += "   Status: All jobs running\n"
    
    # Disk Space
    disk = components.get('disk_space', {})
    disk_status = disk.get('status', 'UNKNOWN')
    disk_emoji = get_status_emoji(disk_status)
    
    message += f"\n💾 <b>DISK SPACE:</b> {disk_emoji} {disk_status}\n"
    
    if disk.get('issues'):
        for issue in disk['issues'][:1]:
            # Extract evidence for disk info
            evidence = issue.get('evidence', '')
            if evidence:
                message += f"   {evidence}\n"
            else:
                message += f"   Issue: {issue.get('problem', 'Unknown')[:60]}...\n"
    else:
        message += "   Status: Sufficient space available\n"
    
    # Overall summary
    message += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Overall:</b>  ✅ {summary.get('healthy', 0)} OK, ⚠️ {summary.get('warning', 0)} WARNING, ❌ {summary.get('critical', 0)} CRITICAL

Last full scan: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
    
    # If there are warnings or critical issues, add note
    if summary.get('warning', 0) > 0 or summary.get('critical', 0) > 0:
        message += "\n💡 <b>Action Required:</b> Check individual alerts for details and fixes"
    
    return message


def format_ml_training_alert(days_old: int, completed_trades: int, required_trades: int = 50) -> str:
    """
    Format ML training status alert
    
    Args:
        days_old: Days since last training
        completed_trades: Number of completed trades
        required_trades: Minimum trades required
    
    Returns:
        Formatted alert message
    """
    status = "⚠️ WARNING" if days_old > 10 else "ℹ️ INFO"
    
    message = f"""🤖 <b>ML TRAINING HEALTH ALERT</b>

📊 Status: {status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 <b>PROBLEM:</b>
ML model not trained for {days_old} days

🔍 <b>ROOT CAUSE:</b>
Not enough completed trades ({completed_trades}/{required_trades} minimum)

📋 <b>EVIDENCE:</b>
Training requires {required_trades}+ completed trades (WIN/LOSS status)

💡 <b>FIX:</b>
Need {required_trades - completed_trades} more completed trades before ML can train.
Wait for current signals to hit TP/SL.

📊 <b>CURRENT STATUS:</b>
  • Completed (WIN/LOSS): {completed_trades}
  • Minimum required: {required_trades}
  • Missing: {required_trades - completed_trades}

⏰ <b>NEXT TRAINING:</b>
Sunday 03:00 UTC (05:00 BG) - if {required_trades}+ trades by then

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 This is expected - not critical
📌 ML will auto-train when enough data available
"""
    
    return message


def format_journal_health_alert(hours_lag: float, error_type: str, error_details: str) -> str:
    """
    Format trading journal health alert
    
    Args:
        hours_lag: Hours since last journal update
        error_type: Type of error (e.g., "AttributeError")
        error_details: Detailed error message
    
    Returns:
        Formatted alert message
    """
    message = f"""🚨 <b>JOURNAL HEALTH ALERT</b>

📊 Status: ❌ CRITICAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 <b>PROBLEM:</b>
Journal not updated for {hours_lag:.1f} hours

🔍 <b>ROOT CAUSE:</b>
{error_type} in journal logging

📋 <b>EVIDENCE:</b>
<code>{error_details[:500]}</code>

📍 <b>CODE LOCATION:</b>
bot.py - auto_signal_job function (lines ~10450-10650)

💡 <b>FIX:</b>
Check log_trade_to_journal() function and verify all required attributes exist

🔧 <b>DEBUG COMMANDS:</b>
<pre>
grep -n "log_trade_to_journal" /root/Crypto-signal-bot/bot.py
grep "ERROR.*journal" /root/Crypto-signal-bot/bot.log | tail -n 10
</pre>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Use /health for full system check
📌 Copy this message to Copilot for instant fix
"""
    
    return message


def format_scheduler_alert(issue_count: int, latest_error: str) -> str:
    """
    Format scheduler health alert
    
    Args:
        issue_count: Number of scheduler issues
        latest_error: Latest error message
    
    Returns:
        Formatted alert message
    """
    message = f"""⏰ <b>SCHEDULER HEALTH ALERT</b>

📊 Status: ⚠️ WARNING

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 <b>PROBLEM:</b>
{issue_count} scheduler issues detected in last 12 hours

🔍 <b>ROOT CAUSE:</b>
APScheduler encountering errors

📋 <b>EVIDENCE:</b>
<code>{latest_error[:500]}</code>

💡 <b>FIX:</b>
Check scheduler job definitions and ensure bot uptime is stable

🔧 <b>DEBUG COMMANDS:</b>
<pre>
grep "ERROR.*scheduler" /root/Crypto-signal-bot/bot.log | tail -n 20
grep "APScheduler" /root/Crypto-signal-bot/bot.log | tail -n 10
</pre>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Use /health for full system check
"""
    
    return message


def format_disk_space_alert(used_percent: float, used_gb: float, total_gb: float, free_gb: float) -> str:
    """
    Format disk space alert
    
    Args:
        used_percent: Percentage of disk used
        used_gb: GB used
        total_gb: Total GB
        free_gb: Free GB
    
    Returns:
        Formatted alert message
    """
    status = "❌ CRITICAL" if used_percent > 90 else "⚠️ WARNING"
    
    message = f"""💾 <b>DISK SPACE ALERT</b>

📊 Status: {status}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 <b>PROBLEM:</b>
Disk space {"critically low" if used_percent > 90 else "running low"}: {used_percent:.1f}% used

📋 <b>CURRENT USAGE:</b>
  • Used: {used_gb:.2f}GB / {total_gb:.2f}GB
  • Free: {free_gb:.2f}GB
  • Usage: {used_percent:.1f}%

💡 <b>FIX:</b>
{"Clean up old logs, backups, or temporary files IMMEDIATELY" if used_percent > 90 else "Monitor disk usage and plan cleanup soon"}

🔧 <b>DEBUG COMMANDS:</b>
<pre>
du -sh /root/Crypto-signal-bot/*
df -h /root/Crypto-signal-bot
find /root/Crypto-signal-bot -name "*.log" -size +10M
</pre>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Consider rotating logs or removing old backups
"""
    
    return message
