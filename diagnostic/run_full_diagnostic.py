#!/usr/bin/env python3
"""
Comprehensive Diagnostic Suite for Crypto Signal Bot

ZERO code changes. ONLY analysis and reporting.

This script orchestrates all diagnostic analyzers and generates a comprehensive
report comparing main.py vs bot.py execution paths.

Usage:
    python diagnostic/run_full_diagnostic.py
    
    or from repository root:
    python -m diagnostic.run_full_diagnostic

Output:
    diagnostic_report_YYYY-MM-DD_HH-MM-SS.md
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all analyzers
from diagnostic.analyzers.startup_tracer import trace_startup_sequences
from diagnostic.analyzers.component_loader import analyze_components
from diagnostic.analyzers.handler_inspector import inspect_handlers
from diagnostic.analyzers.import_chain_mapper import map_import_chains
from diagnostic.analyzers.ast_comparator import compare_code_structure
from diagnostic.analyzers.function_inventory import inventory_functions
from diagnostic.analyzers.telegram_mapper import map_telegram_interface
from diagnostic.analyzers.log_parser import parse_logs

# Import report generator
from diagnostic.generators.report_generator import generate_report


def main():
    """Run full diagnostic suite"""
    print("="*70)
    print("🔍 CRYPTO BOT DIAGNOSTIC SUITE")
    print("="*70)
    print("\n⚠️  This diagnostic performs ZERO code changes")
    print("✅  Read-only analysis and reporting only\n")
    print("-"*70)
    
    # Change to repository root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)
    print(f"📂 Working directory: {repo_root}\n")
    
    # Collect all analysis results
    results = {}
    total_steps = 8
    
    try:
        print(f"[1/{total_steps}] 🚀 Tracing startup sequences...")
        results['startup'] = trace_startup_sequences()
        print("    ✅ Startup sequences traced")
        
        print(f"\n[2/{total_steps}] 📦 Analyzing component loading...")
        results['components'] = analyze_components()
        print("    ✅ Component loading analyzed")
        
        print(f"\n[3/{total_steps}] 🔍 Inspecting logging handlers...")
        results['handlers'] = inspect_handlers()
        print("    ✅ Logging handlers inspected")
        
        print(f"\n[4/{total_steps}] 🔗 Mapping import chains...")
        results['imports'] = map_import_chains()
        print("    ✅ Import chains mapped")
        
        print(f"\n[5/{total_steps}] 🌳 Comparing code structure (AST)...")
        results['ast'] = compare_code_structure('bot.py', 'main.py')
        print("    ✅ Code structure compared")
        
        print(f"\n[6/{total_steps}] 📚 Creating function inventory...")
        results['functions'] = inventory_functions()
        print("    ✅ Function inventory created")
        
        print(f"\n[7/{total_steps}] 💬 Mapping Telegram interface...")
        results['telegram'] = map_telegram_interface()
        print("    ✅ Telegram interface mapped")
        
        print(f"\n[8/{total_steps}] 📋 Parsing logs...")
        results['logs'] = parse_logs('bot.log', num_lines=1000)
        print("    ✅ Logs parsed")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Generate report
    print("\n" + "="*70)
    print("📝 Generating comprehensive report...")
    print("="*70 + "\n")
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f'diagnostic_report_{timestamp}.md'
    report_path = os.path.join(repo_root, report_filename)
    
    try:
        generate_report(results, report_path)
        print(f"✅ Report generated successfully!\n")
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Display summary
    print("="*70)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"\n📄 Report Location: {report_filename}\n")
    
    print("Key Findings:")
    print("-"*70)
    
    # Handler comparison
    main_handlers = results['handlers']['main_py']['total_handlers']
    bot_handlers = results['handlers']['bot_py']['total_handlers']
    print(f"  Logging Handlers:")
    print(f"    • main.py path:  {main_handlers} handlers")
    print(f"    • bot.py path:   {bot_handlers} handlers")
    print(f"    • Difference:    +{main_handlers - bot_handlers} (main.py creates extra handler)")
    
    # Function counts
    bot_funcs = results['functions']['bot.py']['total_functions']
    main_funcs = results['functions']['main.py']['total_functions']
    print(f"\n  Functions:")
    print(f"    • bot.py:        {bot_funcs} functions")
    print(f"    • main.py:       {main_funcs} functions")
    
    # Telegram interface
    total_interface = results['telegram']['total_interface_points']
    print(f"\n  Telegram Interface:")
    print(f"    • Commands:      {results['telegram']['command_count']}")
    print(f"    • Callbacks:     {results['telegram']['callback_count']}")
    print(f"    • Scheduler Jobs: {results['telegram']['scheduler_job_count']}")
    print(f"    • Total Points:  {total_interface}")
    
    # Log analysis
    if results['logs'].get('file_exists'):
        print(f"\n  Log Analysis:")
        print(f"    • Errors:        {results['logs']['error_count']}")
        print(f"    • Warnings:      {results['logs']['warning_count']}")
        double_detected = results['logs']['double_logging_evidence']['detected']
        print(f"    • Double Logging: {'Yes ⚠️' if double_detected else 'No ✅'}")
    
    # Import conflicts
    conflict = results['imports']['critical_findings']['conflict']
    print(f"\n  Import Analysis:")
    print(f"    • Modules with logging setup: {results['imports']['total_modules_with_logging_setup']}")
    print(f"    • Conflict detected: {'Yes ⚠️' if conflict else 'No ✅'}")
    
    print("\n" + "="*70)
    print("🎯 RECOMMENDATION")
    print("="*70)
    print("\n  ✅ Continue using: python bot.py")
    print("  ⚠️  Avoid using:    python main.py (causes double logging)")
    print("\n" + "="*70)
    print(f"\n📖 For detailed analysis, see: {report_filename}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
