# Crypto Bot Diagnostic Suite

Comprehensive analysis tool for comparing `main.py` vs `bot.py` execution paths.

## ⚠️ Important

**This suite makes ZERO code changes.** It only reads, analyzes, and reports.

## 🎯 Purpose

This diagnostic suite was created to analyze the differences between running the Crypto Signal Bot via:
- `python main.py` (wrapper entry point)
- `python bot.py` (direct execution)

It specifically investigates:
- Logging handler duplication issues
- Startup sequence differences
- Component loading order
- Import chain dependencies
- Function inventory and categorization
- Telegram interface mapping
- Log evidence analysis

## 📋 Features

### 8 Specialized Analyzers

1. **Startup Tracer** (`startup_tracer.py`)
   - Traces execution flow step-by-step for both entry points
   - Estimates startup time
   - Identifies when logging handlers are created

2. **Component Loader** (`component_loader.py`)
   - Tracks what modules load when
   - Categorizes imports (standard library, third-party, local)
   - Analyzes loading order differences

3. **Handler Inspector** (`handler_inspector.py`)
   - Performs runtime inspection of logging handlers
   - Compares handler counts between execution paths
   - Identifies duplicate handlers

4. **Import Chain Mapper** (`import_chain_mapper.py`)
   - Maps full dependency tree
   - Identifies all modules that configure logging
   - Detects circular dependencies

5. **AST Comparator** (`ast_comparator.py`)
   - Uses Python AST for code structure analysis
   - Compares functions, classes, imports
   - Identifies logging configuration calls

6. **Function Inventory** (`function_inventory.py`)
   - Creates complete inventory of all functions
   - Categorizes by type (commands, callbacks, helpers, etc.)
   - Counts async vs sync functions

7. **Telegram Mapper** (`telegram_mapper.py`)
   - Maps user commands to source code
   - Identifies callback handlers
   - Lists scheduled jobs
   - Tracks message handlers

8. **Log Parser** (`log_parser.py`)
   - Parses bot.log for evidence
   - Identifies errors and warnings
   - Detects double logging patterns
   - Extracts startup events

### Comprehensive Report Generator

Generates a markdown report with 12 sections:
1. Executive Summary
2. Startup Sequence Comparison
3. Component Loading Analysis
4. Logging Handler Analysis
5. Import Chain Mapping
6. AST-Based Code Structure Comparison
7. Function Inventory
8. Telegram Interface Mapping
9. Log Evidence Analysis
10. Side-by-Side Comparison Tables
11. Decision Matrix
12. Recommendations & Action Plan

## 🚀 Usage

### Basic Usage

```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot
python diagnostic/run_full_diagnostic.py
```

### Alternative (as module)

```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot
python -m diagnostic.run_full_diagnostic
```

## 📤 Output

The diagnostic generates a timestamped markdown report:

```
diagnostic_report_2026-01-28_23-45-30.md
```

The report contains:
- Detailed analysis of both execution paths
- Side-by-side comparisons
- Evidence from logs
- Clear recommendations
- Step-by-step action plan (if changes needed)

## ⏱️ Performance

- **Runtime:** ~30-60 seconds
- **Resources:** Minimal CPU and memory usage
- **Impact:** Zero impact on running bot (read-only)

## 📊 Sample Output

```
==================================================================
🔍 CRYPTO BOT DIAGNOSTIC SUITE
==================================================================

⚠️  This diagnostic performs ZERO code changes
✅  Read-only analysis and reporting only

------------------------------------------------------------------
📂 Working directory: /home/runner/work/Crypto-signal-bot/Crypto-signal-bot

[1/8] 🚀 Tracing startup sequences...
    ✅ Startup sequences traced

[2/8] 📦 Analyzing component loading...
    ✅ Component loading analyzed

[3/8] 🔍 Inspecting logging handlers...
    ✅ Logging handlers inspected

[4/8] 🔗 Mapping import chains...
    ✅ Import chains mapped

[5/8] 🌳 Comparing code structure (AST)...
    ✅ Code structure compared

[6/8] 📚 Creating function inventory...
    ✅ Function inventory created

[7/8] 💬 Mapping Telegram interface...
    ✅ Telegram interface mapped

[8/8] 📋 Parsing logs...
    ✅ Logs parsed

==================================================================
📝 Generating comprehensive report...
==================================================================

✅ Report generated successfully!

==================================================================
📊 DIAGNOSTIC SUMMARY
==================================================================

📄 Report Location: diagnostic_report_2026-01-28_23-45-30.md

Key Findings:
----------------------------------------------------------------------
  Logging Handlers:
    • main.py path:  3 handlers
    • bot.py path:   2 handlers
    • Difference:    +1 (main.py creates extra handler)

  Functions:
    • bot.py:        247 functions
    • main.py:       1 functions

  Telegram Interface:
    • Commands:      42
    • Callbacks:     38
    • Scheduler Jobs: 18
    • Total Points:  98

  Log Analysis:
    • Errors:        5
    • Warnings:      2
    • Double Logging: Yes ⚠️

==================================================================
🎯 RECOMMENDATION
==================================================================

  ✅ Continue using: python bot.py
  ⚠️  Avoid using:    python main.py (causes double logging)

==================================================================

📖 For detailed analysis, see: diagnostic_report_2026-01-28_23-45-30.md
```

## 🔒 Safety

### What This Tool Does
✅ Reads source code files  
✅ Parses with Python AST  
✅ Analyzes log files  
✅ Generates reports  
✅ Provides recommendations  

### What This Tool Does NOT Do
❌ Modify any code  
❌ Restart the bot  
❌ Execute bot.main()  
❌ Add/remove logging handlers  
❌ Change configuration  
❌ Access databases  
❌ Make network requests  

## 📝 Requirements

- Python 3.8+
- Standard library only (no external dependencies)
- Read access to repository files
- Optional: access to bot.log for log analysis

## 🔍 What It Analyzes

### Files Analyzed
- `main.py` - Entry point wrapper
- `bot.py` - Main bot code
- All `.py` files in repository (for import analysis)
- `bot.log` - Runtime logs (if available)

### Analysis Depth
- Line-by-line startup sequence
- Complete import dependency tree
- All function definitions
- All Telegram command registrations
- All logging configuration calls
- Error and warning patterns in logs

## 🎯 Use Cases

### When to Run This Diagnostic

1. **Before switching entry points** - Understand the differences
2. **Debugging double logging** - Identify root cause
3. **Code review** - Comprehensive codebase analysis
4. **Documentation** - Generate up-to-date function inventory
5. **Deployment planning** - Understand startup behavior

## 📚 Report Sections Explained

### Executive Summary
High-level findings and critical issues

### Startup Sequence Comparison
Step-by-step execution trace for both paths

### Component Loading Analysis
What modules load and when

### Logging Handler Analysis
Detailed handler inspection with sources

### Import Chain Mapping
Full dependency tree with logging configs

### AST Comparison
Structural code differences

### Function Inventory
Complete catalog of all functions with categorization

### Telegram Mapping
User interface → source code mapping

### Log Evidence Analysis
Patterns and issues found in logs

### Comparison Tables
Side-by-side metrics

### Decision Matrix
Should you use main.py or bot.py?

### Recommendations
Actionable advice based on findings

### Action Plan
Step-by-step guide if changes are needed

## 🛠️ Troubleshooting

### Issue: "Module not found"
**Solution:** Run from repository root or use `python -m diagnostic.run_full_diagnostic`

### Issue: "Log file not found"
**Solution:** This is normal if bot hasn't run yet. Report will note this and continue.

### Issue: "Permission denied"
**Solution:** Ensure read access to all repository files

### Issue: "Import error"
**Solution:** Ensure Python 3.8+ and standard library available

## 📖 Understanding the Results

### Handler Count: 3 vs 2
- **3 handlers (main.py path):** Indicates double logging
- **2 handlers (bot.py path):** Correct configuration

### Double Logging Evidence
- **Detected:** Same message appears multiple times
- **Not Detected:** Clean logs, no duplication

### Recommendation: "Use bot.py"
Based on:
- Fewer handlers (2 vs 3)
- No double logging
- Simpler execution path
- Faster startup time

## 🔄 Updating the Diagnostic

The diagnostic is designed to be:
- **Self-contained** - All logic in diagnostic/ folder
- **Isolated** - No dependencies on bot code
- **Safe** - Read-only operations
- **Extensible** - Easy to add new analyzers

## 📞 Support

If you encounter issues:
1. Check file permissions
2. Verify Python version (3.8+)
3. Run from repository root
4. Check error messages in output

## 📄 License

Same as parent project (Crypto Signal Bot)

## 🙏 Acknowledgments

Created to solve the double logging mystery in Crypto Signal Bot and provide comprehensive codebase analysis without modifying production code.

---

**Last Updated:** 2026-01-28  
**Version:** 1.0.0  
**Status:** Production Ready ✅
