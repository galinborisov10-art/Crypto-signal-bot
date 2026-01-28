"""
Log Parser

Parses bot.log to find evidence of issues, errors, and double logging.
"""

import os
import re
from typing import Dict, List, Any
from datetime import datetime
from collections import defaultdict


def parse_logs(log_file_name: str = 'bot.log', num_lines: int = 1000) -> Dict[str, Any]:
    """
    Parse bot.log for evidence of issues.
    
    Args:
        log_file_name: Name of log file to parse
        num_lines: Number of lines to analyze (from end of file)
    
    Returns:
        Dictionary with log analysis results
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(base_path, log_file_name)
    
    if not os.path.exists(log_path):
        return {
            "file_exists": False,
            "error": f"Log file not found: {log_path}",
            "total_lines_analyzed": 0,
            "errors": [],
            "warnings": [],
            "double_logging_evidence": {
                "detected": False,
                "note": "Cannot analyze - log file not found"
            }
        }
    
    try:
        # Read the last num_lines from the file
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            lines = all_lines[-num_lines:] if len(all_lines) > num_lines else all_lines
        
        errors = analyze_errors(lines)
        warnings = analyze_warnings(lines)
        double_logging = detect_double_logging(lines)
        startup_events = extract_startup_events(lines)
        
        return {
            "file_exists": True,
            "log_file": log_path,
            "total_lines_in_file": len(all_lines),
            "total_lines_analyzed": len(lines),
            "analysis_range": f"Last {len(lines)} lines",
            "errors": errors,
            "error_count": len(errors),
            "warnings": warnings,
            "warning_count": len(warnings),
            "double_logging_evidence": double_logging,
            "startup_events": startup_events,
            "startup_event_count": len(startup_events)
        }
    
    except Exception as e:
        return {
            "file_exists": True,
            "error": f"Failed to parse log file: {str(e)}",
            "total_lines_analyzed": 0,
            "errors": [],
            "warnings": []
        }


def analyze_errors(lines: List[str]) -> List[Dict[str, Any]]:
    """Extract and categorize errors from log lines"""
    errors = defaultdict(lambda: {"count": 0, "first_seen": None, "last_seen": None, "examples": []})
    
    error_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+ - .+ - ERROR - (.+)')
    
    for line in lines:
        match = error_pattern.search(line)
        if match:
            timestamp = match.group(1)
            message = match.group(2).strip()
            
            # Normalize the message for grouping
            normalized = normalize_error_message(message)
            
            errors[normalized]["count"] += 1
            if errors[normalized]["first_seen"] is None:
                errors[normalized]["first_seen"] = timestamp
            errors[normalized]["last_seen"] = timestamp
            
            if len(errors[normalized]["examples"]) < 2:
                errors[normalized]["examples"].append(message[:200])  # First 200 chars
    
    # Convert to list
    result = []
    for normalized, data in errors.items():
        result.append({
            "message": normalized,
            "count": data["count"],
            "first_seen": data["first_seen"],
            "last_seen": data["last_seen"],
            "examples": data["examples"]
        })
    
    return sorted(result, key=lambda x: x["count"], reverse=True)


def analyze_warnings(lines: List[str]) -> List[Dict[str, Any]]:
    """Extract and categorize warnings from log lines"""
    warnings = defaultdict(lambda: {"count": 0, "first_seen": None, "last_seen": None})
    
    warning_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\d+ - .+ - WARNING - (.+)')
    
    for line in lines:
        match = warning_pattern.search(line)
        if match:
            timestamp = match.group(1)
            message = match.group(2).strip()
            
            normalized = normalize_error_message(message)
            
            warnings[normalized]["count"] += 1
            if warnings[normalized]["first_seen"] is None:
                warnings[normalized]["first_seen"] = timestamp
            warnings[normalized]["last_seen"] = timestamp
    
    result = []
    for normalized, data in warnings.items():
        result.append({
            "message": normalized,
            "count": data["count"],
            "first_seen": data["first_seen"],
            "last_seen": data["last_seen"]
        })
    
    return sorted(result, key=lambda x: x["count"], reverse=True)


def normalize_error_message(message: str) -> str:
    """Normalize error messages for grouping"""
    # Remove file paths
    message = re.sub(r'/[^\s]+\.py', '[PATH].py', message)
    # Remove specific IDs, numbers
    message = re.sub(r'\b\d+\b', '[NUM]', message)
    # Remove timestamps
    message = re.sub(r'\d{4}-\d{2}-\d{2}', '[DATE]', message)
    message = re.sub(r'\d{2}:\d{2}:\d{2}', '[TIME]', message)
    
    return message[:200]  # Limit length


def detect_double_logging(lines: List[str]) -> Dict[str, Any]:
    """Detect evidence of double logging"""
    
    # Look for identical consecutive messages
    duplicates = []
    prev_message = None
    prev_timestamp = None
    duplicate_count = 0
    
    message_pattern = re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+ - (.+ - .+ - .+)')
    
    for line in lines:
        match = message_pattern.search(line)
        if match:
            message = match.group(1)
            
            if message == prev_message:
                duplicate_count += 1
                if duplicate_count == 1:  # First duplicate
                    duplicates.append({
                        "message": message[:100],
                        "appears_consecutively": True
                    })
            else:
                duplicate_count = 0
            
            prev_message = message
    
    # Look for specific duplicate patterns
    scheduler_started = sum(1 for line in lines if 'Scheduler started' in line or 'APScheduler started' in line)
    bot_started = sum(1 for line in lines if 'Bot started' in line or 'Starting bot' in line)
    
    detected = len(duplicates) > 0 or scheduler_started > 1 or bot_started > 1
    
    evidence = {
        "detected": detected,
        "consecutive_duplicates": len(duplicates),
        "duplicate_examples": duplicates[:5],  # First 5 examples
        "scheduler_start_count": scheduler_started,
        "bot_start_count": bot_started
    }
    
    if detected:
        evidence["conclusion"] = "Double logging detected - likely due to multiple logging handlers"
        if scheduler_started > 1:
            evidence["expected_scheduler_starts"] = 1
            evidence["actual_scheduler_starts"] = scheduler_started
            evidence["ratio"] = round(scheduler_started / 1.0, 1)
    else:
        evidence["conclusion"] = "No clear evidence of double logging in analyzed lines"
    
    return evidence


def extract_startup_events(lines: List[str]) -> List[Dict[str, str]]:
    """Extract startup-related events from logs"""
    events = []
    
    startup_keywords = [
        'Starting', 'Started', 'Initialized', 'Loading', 'Loaded',
        'Scheduler', 'APScheduler', 'Bot', 'Application', 'Handler'
    ]
    
    timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})')
    
    for line in lines:
        # Check if line contains startup keywords
        if any(keyword in line for keyword in startup_keywords):
            timestamp_match = timestamp_pattern.search(line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                
                # Extract the event description
                event = line.split(' - ')[-1].strip()[:100]  # Last part, first 100 chars
                
                events.append({
                    "timestamp": timestamp,
                    "event": event
                })
    
    return events[:50]  # Limit to 50 events


if __name__ == "__main__":
    # Test the parser
    results = parse_logs(num_lines=1000)
    
    if results.get("file_exists"):
        print(f"=== Log Analysis ===")
        print(f"Total lines analyzed: {results['total_lines_analyzed']}")
        print(f"Errors found: {results['error_count']}")
        print(f"Warnings found: {results['warning_count']}")
        print(f"Double logging detected: {results['double_logging_evidence']['detected']}")
        
        if results['errors']:
            print(f"\nTop error:")
            print(f"  {results['errors'][0]['message']}")
            print(f"  Count: {results['errors'][0]['count']}")
    else:
        print(f"Log file not found or cannot be read")
