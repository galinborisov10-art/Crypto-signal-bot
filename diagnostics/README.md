# 🔍 Full Engine Logic Audit - Diagnostic Module

## Overview

This diagnostic module provides a **read-only transparency layer** for the ICT Signal Engine. It explains, validates, and traces the engine's logic without modifying any production code.

## Purpose

- ✅ Explain component definitions (OB, FVG, Liquidity, etc.)
- ✅ Explain detection logic
- ✅ Explain timeframe routing
- ✅ Explain scenario decision logic
- ✅ Validate routing integrity
- ✅ Validate determinism
- ✅ Validate component-source consistency
- ✅ Produce human-readable structured trace

## Strict Rules

This module **DOES NOT**:

- ❌ Modify engine logic
- ❌ Modify scoring
- ❌ Modify scenario rules
- ❌ Modify production commands
- ❌ Change Telegram output
- ❌ Introduce side effects

**This is a read-only transparency layer.**

## Files

### `full_engine_audit.py`

Main diagnostic script that performs comprehensive engine audit.

### `deterministic_snapshots.json`

Contains fixed historical snapshots for validation testing.

## Usage

### Basic Usage

```bash
python diagnostics/full_engine_audit.py --symbol BTCUSDT --tf 1h
```

### Advanced Usage

```bash
# Test with different symbols and timeframes
python diagnostics/full_engine_audit.py --symbol ETHUSDT --tf 4h

# Save results to JSON file
python diagnostics/full_engine_audit.py --symbol BTCUSDT --tf 1h --output results.json
```

### Command Line Arguments

- `--symbol`: Trading symbol (default: BTCUSDT)
- `--tf`: Timeframe (default: 1h)
- `--output`: Optional output file path for JSON results

## Output Structure

The script produces 9 structured blocks in order:

### 1️⃣ Component Definitions Block

Dumps exact rules from code for each ICT component:
- Order Block
- Fair Value Gap (FVG)
- Liquidity Zone (BSL/SSL)
- Whale Order Block
- BOS/MSS
- Displacement

### 2️⃣ Timeframe Contract Block

Prints and validates timeframe hierarchy:
- SIGNAL_TF (Entry)
- CONFIRMATION_TF
- STRUCTURE_TF
- HTF_BIAS_TF

Fails if hierarchy is violated.

### 3️⃣ Component Source Mapping

Maps each component type to its expected source timeframe.

**Important**: Zero components ≠ failure. Failure only if component comes from wrong timeframe.

### 4️⃣ Explainable OB Detector Mode

Explains Order Block detection and rejection logic step-by-step.

### 5️⃣ Scenario Decision Trace

Shows how entry scenarios are scored and selected:
- ROLLBACK
- PULLBACK
- CONTINUATION
- REVERSAL

Displays weights, bonuses, penalties, and decision logic.

### 6️⃣ HTF Bias Block

Verifies HTF bias provides direction only and doesn't inject entry components.

### 7️⃣ Deterministic Check

Tests that running the engine twice with same data produces identical results.

### 8️⃣ Snapshot Validation Mode

Validates engine behavior against fixed historical snapshots.

### 9️⃣ Telegram Consistency Check

Verifies Telegram output matches actual engine state.

## Validation Rules

### What is NOT a Failure

- ❗ Zero components detected
- ❗ Missing liquidity zones
- ❗ No Order Blocks found

### What IS a Failure

- ❌ Routing violation (wrong timeframe hierarchy)
- ❌ Cross-timeframe contamination
- ❌ Determinism violation
- ❌ Scenario using wrong TF components
- ❌ Telegram mismatch

## Example Output

```
================================================================================
🔍 FULL ENGINE LOGIC AUDIT (READ-ONLY)
================================================================================
Symbol: BTCUSDT
Timeframe: 1h
Timestamp: 2026-02-22T01:00:00.000000
================================================================================

================================================================================
1️⃣ COMPONENT DEFINITIONS BLOCK
================================================================================

COMPONENT: OrderBlock
Definition:
  - Last opposite candle before displacement
  - Requires valid BOS (Break of Structure)
  - Min body threshold: 0.3
  - Displacement threshold: 0.5%
  - Min volume ratio: 1.0
  - Min strength: 35
  - Lookback candles: 5
  - Max wick ratio: 0.4
  - Mitigation threshold: 0.5

...

================================================================================
📊 AUDIT SUMMARY
================================================================================

Total Violations: 0
Total Warnings: 0

✅ NO VIOLATIONS FOUND

Audit Blocks Completed:
  ✅ component_definitions
  ✅ timeframe_contract
  ✅ component_source_mapping
  ✅ ob_detector_explanation
  ✅ scenario_decision_trace
  ✅ htf_bias
  ✅ determinism_check
  ✅ snapshot_validation
  ✅ telegram_consistency

================================================================================
🔍 AUDIT COMPLETE
================================================================================
```

## Integration

This diagnostic module is completely standalone and does not affect production code. It can be run at any time for debugging, validation, or transparency purposes.

## Exit Codes

- `0`: Audit passed (no violations)
- `1`: Audit failed (violations found OR core engine not available)

## Requirements

**CRITICAL**: The diagnostic script requires the ICT Signal Engine and core detectors (Order Block, FVG) to be available. If these core components cannot be imported, the script will exit with code 1.

### Required Components

The following components **MUST** be available:
- `ict_signal_engine` - Core ICT Signal Engine
- `order_block_detector` - Order Block Detector
- `fvg_detector` - Fair Value Gap Detector

### Optional Components

The following components are optional and will use fallback values if not available:
- `liquidity_map` - Liquidity Mapper
- `ict_whale_detector` - Whale Detector
- `mtf_analyzer` - Multi-Timeframe Analyzer
- `entry_scenario_config` - Scenario configuration (uses fallback values)

### Installation

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

If the script fails with "Engine Not Available" error, verify:
1. All Python dependencies are installed
2. Python environment is properly configured
3. Engine files are accessible in the repository

## Author

Diagnostic System
Date: 2026-02-22

## License

Part of the Crypto-signal-bot project.
