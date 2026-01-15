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
<code>{issue.get('evidence', 'No evidence available')[:500]}{"..." if len(issue.get('evidence', '')) > 500 else ''}</code>"""
    
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
    Format comprehensive health report
    Mixed language: Bulgarian structure + English technical terms
    
    Args:
        health_data: Dict with component health info
        
    Returns:
        Formatted HTML message (mixed BG/EN)
    """
    from datetime import datetime
    
    message = "🏥 <b>СИСТЕМНА ДИАГНОСТИКА</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"Завършено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    if 'duration' in health_report:
        message += f"Продължителност: {health_report['duration']:.1f}s\n"
    
    message += "\n"
    
    components = health_report.get('components', {})
    
    # Count OK vs problems
    total = len(components)
    ok_count = sum(1 for c in components.values() if c.get('status') == 'HEALTHY')
    problem_count = total - ok_count
    
    if problem_count == 0:
        message += f"✅ <b>ВСИЧКИ СИСТЕМИ РАБОТЯТ ({total}/{total})</b>\n\n"
    else:
        message += f"⚠️ <b>ОТКРИТИ {problem_count} ПРОБЛЕМА ({ok_count}/{total} OK)</b>\n\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Separate problems from healthy components
    problems = []
    healthy = []
    
    for comp_name, comp_data in components.items():
        if comp_data.get('status') != 'HEALTHY':
            problems.append((comp_name, comp_data))
        else:
            healthy.append((comp_name, comp_data))
    
    # Format problems with full details
    if problems:
        for i, (name, data) in enumerate(problems, 1):
            message += f"❌ <b>ПРОБЛЕМ #{i}: {name.upper()}</b>\n"
            message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            if 'status' in data:
                message += f"Статус: {data['status']}\n"
            
            # Show issues if available
            if 'issues' in data and data['issues']:
                for issue in data['issues'][:2]:  # Show top 2 issues
                    if 'problem' in issue:
                        message += f"\n<b>Проблем:</b> {issue['problem']}\n"
                    
                    if 'root_cause' in issue:
                        message += f"<b>Причина:</b> {issue['root_cause']}\n"
                    
                    if 'fix' in issue:
                        message += f"<b>Решение:</b> {issue['fix']}\n"
                    
                    if 'evidence' in issue:
                        evidence = issue['evidence'][:200]
                        if len(issue['evidence']) > 200:
                            evidence += "..."
                        message += f"\n<code>{evidence}</code>\n"
            
            message += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Show healthy components (summary)
    if healthy:
        message += f"✅ <b>ЗДРАВИ КОМПОНЕНТИ ({len(healthy)}/{total}):</b>\n\n"
        for name, data in healthy:
            status_emoji = get_status_emoji(data.get('status', 'HEALTHY'))
            message += f"{status_emoji} <b>{name}</b>\n"
        message += "\n"
    
    # Summary
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"📊 <b>ОБОБЩЕНИЕ:</b>\n"
    
    summary = health_report.get('summary', {})
    critical_count = summary.get('critical', 0)
    warning_count = summary.get('warning', 0)
    healthy_count = summary.get('healthy', 0)
    
    message += f"  • Критични: {critical_count}\n"
    message += f"  • Предупреждения: {warning_count}\n"
    message += f"  • Здрави: {healthy_count}\n"
    
    if problem_count > 0:
        message += f"\n<i>За бърза проверка: /quick_health</i>\n"
    
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
