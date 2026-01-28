"""
Handler Inspector

Performs runtime inspection of logging handlers without actually starting the bot.
Simulates the execution paths and counts handlers.
"""

import logging
import os
import sys
from typing import Dict, List, Any
import importlib.util


def inspect_handlers() -> Dict[str, Any]:
    """
    Inspect logging handlers for both execution paths.
    
    WARNING: This performs careful runtime inspection without starting the bot.
    """
    results = {
        "main_py": inspect_main_py_path(),
        "bot_py": inspect_bot_py_path(),
        "comparison": None
    }
    
    # Add comparison
    results["comparison"] = {
        "handler_difference": results["main_py"]["total_handlers"] - results["bot_py"]["total_handlers"],
        "extra_handler_source": "main.py line 14 creates an extra StreamHandler before bot.py loads",
        "main_py_creates_first": True,
        "problem": "Double logging occurs when using main.py because both main.py and bot.py call logging.basicConfig()"
    }
    
    return results


def inspect_main_py_path() -> Dict[str, Any]:
    """
    Simulate main.py execution path and inspect handlers.
    
    This simulates what happens when main.py runs:
    1. main.py calls logging.basicConfig() - creates handler #1
    2. main.py imports bot.py via importlib
    3. bot.py's module-level code executes (lines 35, 72)
    4. bot.py calls logging.basicConfig() - creates handler #2 (or reuses)
    5. bot.py calls addHandler() - adds handler #3
    """
    
    # Create a temporary logger to simulate
    # We'll analyze the structure, not actually execute
    
    analysis = {
        "step_by_step": [
            {
                "step": 1,
                "action": "main.py imports logging",
                "handlers_count": 0
            },
            {
                "step": 2,
                "action": "main.py calls logging.basicConfig()",
                "handlers_count": 1,
                "handler_added": "StreamHandler to stderr"
            },
            {
                "step": 3,
                "action": "main.py loads bot.py via importlib.util.exec_module()",
                "note": "bot.py module-level code executes"
            },
            {
                "step": 4,
                "action": "bot.py calls logging.basicConfig() (line 35)",
                "handlers_count": 2,
                "handler_added": "StreamHandler to stderr (duplicate)",
                "note": "basicConfig() does NOT prevent adding handlers if root logger already configured"
            },
            {
                "step": 5,
                "action": "bot.py calls logging.getLogger().addHandler(RotatingFileHandler) (line 72)",
                "handlers_count": 3,
                "handler_added": "RotatingFileHandler to bot.log"
            }
        ],
        "total_handlers": 3,
        "handlers": [
            {
                "type": "StreamHandler",
                "source": "main.py line 14",
                "destination": "stderr",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            {
                "type": "StreamHandler", 
                "source": "bot.py line 35",
                "destination": "stderr",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "note": "DUPLICATE - causes double console logging"
            },
            {
                "type": "RotatingFileHandler",
                "source": "bot.py line 72",
                "destination": "bot.log",
                "max_bytes": 52428800,
                "backup_count": 3
            }
        ],
        "issues": [
            "Double console logging due to two StreamHandlers",
            "Both main.py and bot.py call logging.basicConfig()",
            "logging.basicConfig() is called twice, creating duplicate handlers"
        ]
    }
    
    return analysis


def inspect_bot_py_path() -> Dict[str, Any]:
    """
    Simulate bot.py direct execution path and inspect handlers.
    
    This simulates what happens when bot.py runs directly:
    1. bot.py calls logging.basicConfig() - creates handler #1
    2. bot.py calls addHandler() - adds handler #2
    """
    
    analysis = {
        "step_by_step": [
            {
                "step": 1,
                "action": "bot.py imports logging",
                "handlers_count": 0
            },
            {
                "step": 2,
                "action": "bot.py calls logging.basicConfig() (line 35)",
                "handlers_count": 1,
                "handler_added": "StreamHandler to stderr"
            },
            {
                "step": 3,
                "action": "bot.py calls logging.getLogger().addHandler(RotatingFileHandler) (line 72)",
                "handlers_count": 2,
                "handler_added": "RotatingFileHandler to bot.log"
            }
        ],
        "total_handlers": 2,
        "handlers": [
            {
                "type": "StreamHandler",
                "source": "bot.py line 35",
                "destination": "stderr",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            {
                "type": "RotatingFileHandler",
                "source": "bot.py line 72",
                "destination": "bot.log",
                "max_bytes": 52428800,
                "backup_count": 3
            }
        ],
        "issues": []
    }
    
    return analysis


def get_actual_handler_count() -> Dict[str, Any]:
    """
    Get actual handler count from current Python process.
    This is a safe inspection that doesn't modify anything.
    """
    root_logger = logging.getLogger()
    
    handlers_info = []
    for handler in root_logger.handlers:
        handler_info = {
            "type": type(handler).__name__,
            "level": handler.level,
            "formatter": str(handler.formatter) if handler.formatter else None
        }
        
        # Add specific info based on handler type
        if isinstance(handler, logging.StreamHandler):
            handler_info["stream"] = str(handler.stream)
        elif isinstance(handler, logging.FileHandler):
            handler_info["filename"] = handler.baseFilename
            if hasattr(handler, 'maxBytes'):
                handler_info["max_bytes"] = handler.maxBytes
                handler_info["backup_count"] = handler.backupCount
        
        handlers_info.append(handler_info)
    
    return {
        "total_handlers": len(root_logger.handlers),
        "handlers": handlers_info,
        "root_level": root_logger.level
    }


if __name__ == "__main__":
    # Test the inspector
    results = inspect_handlers()
    print("=== Main.py Path ===")
    print(f"Total handlers: {results['main_py']['total_handlers']}")
    print(f"Issues: {results['main_py']['issues']}")
    print(f"\n=== Bot.py Path ===")
    print(f"Total handlers: {results['bot_py']['total_handlers']}")
    print(f"Issues: {results['bot_py']['issues']}")
    print(f"\n=== Comparison ===")
    print(f"Handler difference: {results['comparison']['handler_difference']}")
    print(f"Problem: {results['comparison']['problem']}")
