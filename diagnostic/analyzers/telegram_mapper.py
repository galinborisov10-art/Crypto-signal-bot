"""
Telegram Command Mapper

Maps the Telegram interface (commands, callbacks, messages) to source code.
"""

import ast
import os
import re
from typing import Dict, List, Any


def map_telegram_interface() -> Dict[str, Any]:
    """
    Map the complete Telegram interface to source code.
    
    Identifies:
    - CommandHandler registrations
    - CallbackQueryHandler registrations  
    - MessageHandler registrations
    - APScheduler job registrations
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bot_path = os.path.join(base_path, 'bot.py')
    
    with open(bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    commands = extract_commands(content)
    callbacks = extract_callbacks(content)
    scheduler_jobs = extract_scheduler_jobs(content)
    message_handlers = extract_message_handlers(content)
    
    return {
        "commands": commands,
        "command_count": len(commands),
        "callbacks": callbacks,
        "callback_count": len(callbacks),
        "scheduler_jobs": scheduler_jobs,
        "scheduler_job_count": len(scheduler_jobs),
        "message_handlers": message_handlers,
        "message_handler_count": len(message_handlers),
        "total_interface_points": len(commands) + len(callbacks) + len(scheduler_jobs) + len(message_handlers),
        "interface_summary": {
            "user_commands": f"{len(commands)} commands available to users",
            "callback_buttons": f"{len(callbacks)} interactive buttons",
            "automated_jobs": f"{len(scheduler_jobs)} scheduled tasks",
            "message_processors": f"{len(message_handlers)} message handlers"
        }
    }


def extract_commands(content: str) -> List[Dict[str, Any]]:
    """Extract CommandHandler registrations"""
    commands = []
    
    # Pattern: CommandHandler('command_name', function_name)
    # Also: application.add_handler(CommandHandler(...))
    pattern = r"CommandHandler\(['\"](\w+)['\"],\s*(\w+)"
    
    for match in re.finditer(pattern, content):
        command = match.group(1)
        function = match.group(2)
        
        # Find the line number
        line_num = content[:match.start()].count('\n') + 1
        
        # Try to find the function definition and its docstring/comments
        func_pattern = rf"(?:async\s+)?def\s+{function}\s*\("
        func_match = re.search(func_pattern, content)
        
        display_text = ""
        if func_match:
            # Look for nearby strings that might be the display text
            func_start = func_match.start()
            func_section = content[func_start:func_start+500]
            
            # Look for await update.message.reply_text or similar
            reply_pattern = r"reply_text\(['\"]([^'\"]+)['\"]"
            reply_match = re.search(reply_pattern, func_section)
            if reply_match:
                display_text = reply_match.group(1)[:50]  # First 50 chars
        
        commands.append({
            "command": f"/{command}",
            "function": function,
            "line": line_num,
            "display_text": display_text,
            "file": "bot.py"
        })
    
    return commands


def extract_callbacks(content: str) -> List[Dict[str, Any]]:
    """Extract callback button handlers"""
    callbacks = []
    
    # Pattern 1: CallbackQueryHandler(function, pattern=...)
    pattern1 = r"CallbackQueryHandler\((\w+),\s*pattern=['\"]?([^'\")\s]+)['\"]?\)"
    
    for match in re.finditer(pattern1, content):
        function = match.group(1)
        pattern = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        
        callbacks.append({
            "callback_data": pattern,
            "function": function,
            "line": line_num,
            "file": "bot.py"
        })
    
    # Pattern 2: InlineKeyboardButton definitions
    button_pattern = r"InlineKeyboardButton\(['\"]([^'\"]+)['\"],\s*callback_data=['\"]([^'\"]+)['\"]"
    
    for match in re.finditer(button_pattern, content):
        button_text = match.group(1)
        callback_data = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        
        # Find if we already have this callback_data
        existing = next((c for c in callbacks if c['callback_data'] == callback_data), None)
        if existing:
            existing['button_text'] = button_text
        else:
            callbacks.append({
                "button_text": button_text,
                "callback_data": callback_data,
                "function": "unknown",
                "line": line_num,
                "file": "bot.py"
            })
    
    return callbacks


def extract_scheduler_jobs(content: str) -> List[Dict[str, Any]]:
    """Extract APScheduler job registrations"""
    jobs = []
    
    # Pattern: scheduler.add_job(function, trigger=..., ...)
    pattern = r"scheduler\.add_job\(([^,]+),\s*['\"]?(\w+)['\"]?,\s*([^)]+)\)"
    
    for match in re.finditer(pattern, content):
        function = match.group(1).strip()
        trigger = match.group(2)
        args = match.group(3)
        
        line_num = content[:match.start()].count('\n') + 1
        
        # Extract schedule details
        schedule = trigger
        if 'interval' in trigger:
            # Look for hours=, minutes=, etc.
            hours_match = re.search(r'hours?=(\d+)', args)
            minutes_match = re.search(r'minutes?=(\d+)', args)
            if hours_match:
                schedule = f"every {hours_match.group(1)} hour(s)"
            elif minutes_match:
                schedule = f"every {minutes_match.group(1)} minute(s)"
        
        jobs.append({
            "function": function,
            "trigger": trigger,
            "schedule": schedule,
            "line": line_num,
            "file": "bot.py"
        })
    
    return jobs


def extract_message_handlers(content: str) -> List[Dict[str, Any]]:
    """Extract MessageHandler registrations"""
    handlers = []
    
    # Pattern: MessageHandler(filters.TEXT, function)
    pattern = r"MessageHandler\(([^,]+),\s*(\w+)"
    
    for match in re.finditer(pattern, content):
        filter_type = match.group(1).strip()
        function = match.group(2)
        
        line_num = content[:match.start()].count('\n') + 1
        
        handlers.append({
            "filter": filter_type,
            "function": function,
            "line": line_num,
            "file": "bot.py"
        })
    
    return handlers


if __name__ == "__main__":
    # Test the mapper
    results = map_telegram_interface()
    print("=== Telegram Interface Mapping ===")
    print(f"Commands: {results['command_count']}")
    print(f"Callbacks: {results['callback_count']}")
    print(f"Scheduler jobs: {results['scheduler_job_count']}")
    print(f"Message handlers: {results['message_handler_count']}")
    print(f"\nTotal interface points: {results['total_interface_points']}")
    
    if results['commands']:
        print(f"\nSample commands:")
        for cmd in results['commands'][:5]:
            print(f"  {cmd['command']} -> {cmd['function']} (line {cmd['line']})")
