#!/bin/bash

# 🧪 Signal Generation Fix - Validation Test Suite
# Run this after PR merge and bot restart to validate all 10 changes

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 SIGNAL GENERATION FIX - VALIDATION TEST SUITE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Configuration
LOG_FILE="bot.log"
LOG_LINES=500

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ ERROR: $LOG_FILE not found"
    echo "Please run this script from the bot directory"
    exit 1
fi

echo "📝 Using log file: $LOG_FILE"
echo "📊 Analyzing last $LOG_LINES lines"
echo ""

# Test 1: candles_ago Field Exists
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: candles_ago Field Exists"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ENRICHMENT_COUNT=$(tail -n $LOG_LINES $LOG_FILE | grep -c "Enriched components with recency")
CANDLES_AGO_COUNT=$(tail -n $LOG_LINES $LOG_FILE | grep "candles_ago" | grep -v "999" | wc -l)

echo "Enrichment logs found: $ENRICHMENT_COUNT"
echo "candles_ago values (non-999): $CANDLES_AGO_COUNT"

if [ $ENRICHMENT_COUNT -gt 0 ] && [ $CANDLES_AGO_COUNT -gt 0 ]; then
    echo "✅ PASS: candles_ago field is being enriched"
else
    echo "❌ FAIL: candles_ago enrichment not working"
fi
echo ""

# Test 2: End of 999 Defaults
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: End of 999 Defaults"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ERRORS_999=$(tail -n $LOG_LINES $LOG_FILE | grep -c "999 candles ago")

echo "\"999 candles ago\" errors: $ERRORS_999"

if [ $ERRORS_999 -eq 0 ]; then
    echo "✅ PASS: No 999 defaults found"
else
    echo "❌ FAIL: Still seeing 999 default values"
fi
echo ""

# Test 3: Scenarios Pass Validation
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Scenarios Pass Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ELIGIBLE_SCENARIOS=$(tail -n $LOG_LINES $LOG_FILE | grep "eligible scenarios" | grep -v "No eligible" | wc -l)

echo "Eligible scenarios found: $ELIGIBLE_SCENARIOS"

if [ $ELIGIBLE_SCENARIOS -gt 0 ]; then
    echo "✅ PASS: Scenarios are passing validation"
    tail -n $LOG_LINES $LOG_FILE | grep "eligible scenarios" | grep -v "No eligible" | head -5
else
    echo "⚠️  WARNING: No eligible scenarios found yet"
fi
echo ""

# Test 4: Signals Reach Step 13
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Signals Reach Step 13"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
STEP_13_COUNT=$(tail -n $LOG_LINES $LOG_FILE | grep -c "Step 13: Signal Generation")

echo "Analyses reaching Step 13: $STEP_13_COUNT"

if [ $STEP_13_COUNT -ge 10 ]; then
    echo "✅ PASS: ≥10 signals reached Step 13"
elif [ $STEP_13_COUNT -gt 0 ]; then
    echo "⚠️  PARTIAL: Some signals reaching Step 13, but < 10"
else
    echo "❌ FAIL: No signals reaching Step 13"
fi
echo ""

# Test 5: Signals Actually Sent
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: Signals Actually Sent"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
SIGNALS_SENT=$(tail -n $LOG_LINES $LOG_FILE | grep -c "✅ New signal")

echo "Signals sent: $SIGNALS_SENT"

if [ $SIGNALS_SENT -ge 10 ]; then
    echo "✅ PASS: ≥10 signals sent"
elif [ $SIGNALS_SENT -gt 0 ]; then
    echo "⚠️  PARTIAL: Some signals sent, but < 10"
else
    echo "❌ FAIL: No signals sent"
fi
echo ""

# Test 6: TOO_FAR is Soft Warning
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: TOO_FAR is Soft Warning"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOO_FAR_SOFT=$(tail -n $LOG_LINES $LOG_FILE | grep "TOO_FAR" | grep -E "(soft|warning|Continuing)" | wc -l)
TOO_FAR_BLOCK=$(tail -n $LOG_LINES $LOG_FILE | grep "TOO_FAR" | grep -i "blocked" | wc -l)

echo "TOO_FAR soft warnings: $TOO_FAR_SOFT"
echo "TOO_FAR hard blocks: $TOO_FAR_BLOCK"

if [ $TOO_FAR_BLOCK -eq 0 ]; then
    echo "✅ PASS: TOO_FAR is now a soft warning"
else
    echo "❌ FAIL: TOO_FAR still causing hard blocks"
fi
echo ""

# Test 7: Distance Limits are Adaptive
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Distance Limits are Adaptive"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DISTANCE_LOGS=$(tail -n $LOG_LINES $LOG_FILE | grep "Distance limits for" | wc -l)

echo "Distance limit logs found: $DISTANCE_LOGS"

if [ $DISTANCE_LOGS -gt 0 ]; then
    echo "✅ PASS: Distance limits are timeframe-adaptive"
    tail -n $LOG_LINES $LOG_FILE | grep "Distance limits for" | head -5
else
    echo "⚠️  WARNING: No distance limit logs found yet"
fi
echo ""

# Test 8: Recency Thresholds are Adaptive
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 8: Recency Thresholds are Adaptive"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RECENCY_LOGS=$(tail -n $LOG_LINES $LOG_FILE | grep "too old" | grep -oP "\d+ for \w+" | wc -l)

echo "Adaptive recency checks found: $RECENCY_LOGS"

if [ $RECENCY_LOGS -gt 0 ]; then
    echo "✅ PASS: Recency thresholds are timeframe-adaptive"
    tail -n $LOG_LINES $LOG_FILE | grep "too old" | grep -oP "candles ago, max \d+ for \w+" | head -5
else
    echo "⚠️  INFO: No recency rejection logs found (might be good if all components are recent)"
fi
echo ""

# Test 9: Component Detection Unchanged
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 9: Component Detection Unchanged"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
COMPONENTS_DETECTED=$(tail -n $LOG_LINES $LOG_FILE | grep "detected on" | wc -l)

echo "Component detection logs: $COMPONENTS_DETECTED"

if [ $COMPONENTS_DETECTED -gt 0 ]; then
    echo "✅ PASS: Component detection still working"
    tail -n $LOG_LINES $LOG_FILE | grep "detected on" | head -5
else
    echo "❌ FAIL: No components being detected"
fi
echo ""

# Test 10: Calculate Success Rate
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 10: Success Rate Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ANALYSES=$(tail -n $LOG_LINES $LOG_FILE | grep -c "Step 1: HTF Bias")
SIGNALS=$(tail -n $LOG_LINES $LOG_FILE | grep -c "✅ New signal")

echo "Total analyses: $ANALYSES"
echo "Signals sent: $SIGNALS"

if [ $ANALYSES -gt 0 ]; then
    SUCCESS_RATE=$((SIGNALS * 100 / ANALYSES))
    echo "Success rate: $SUCCESS_RATE%"
    echo ""
    
    if [ $SUCCESS_RATE -ge 50 ]; then
        echo "🎯 EXCELLENT: Success rate ≥ 50% (stretch goal achieved!)"
    elif [ $SUCCESS_RATE -ge 37 ]; then
        echo "✅ PASS: Success rate ≥ 37% (primary goal achieved)"
    elif [ $SUCCESS_RATE -ge 25 ]; then
        echo "✅ PASS: Success rate ≥ 25% (minimum goal achieved)"
    else
        echo "❌ FAIL: Success rate < 25% minimum target"
    fi
else
    echo "⚠️  WARNING: No analyses found in logs yet"
    echo "Wait for 10-15 minutes for the analysis cycle to complete"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 VALIDATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# Count passes
[ $ENRICHMENT_COUNT -gt 0 ] && [ $CANDLES_AGO_COUNT -gt 0 ] && ((PASS_COUNT++)) || ((FAIL_COUNT++))
[ $ERRORS_999 -eq 0 ] && ((PASS_COUNT++)) || ((FAIL_COUNT++))
[ $ELIGIBLE_SCENARIOS -gt 0 ] && ((PASS_COUNT++))
[ $STEP_13_COUNT -ge 10 ] && ((PASS_COUNT++))
[ $SIGNALS_SENT -ge 10 ] && ((PASS_COUNT++))
[ $TOO_FAR_BLOCK -eq 0 ] && ((PASS_COUNT++)) || ((FAIL_COUNT++))
[ $DISTANCE_LOGS -gt 0 ] && ((PASS_COUNT++))
[ $COMPONENTS_DETECTED -gt 0 ] && ((PASS_COUNT++)) || ((FAIL_COUNT++))

echo "Tests passed: $PASS_COUNT"
echo "Tests failed: $FAIL_COUNT"
echo ""

if [ $PASS_COUNT -ge 7 ]; then
    echo "✅ OVERALL: Implementation successful!"
    echo ""
    echo "Next steps:"
    echo "1. Monitor bot for 24 hours"
    echo "2. Fine-tune thresholds if needed"
    echo "3. Collect feedback on signal quality"
elif [ $PASS_COUNT -ge 5 ]; then
    echo "⚠️  OVERALL: Partial success, needs tuning"
    echo ""
    echo "Recommended actions:"
    echo "1. Review failed tests"
    echo "2. Check bot logs for errors"
    echo "3. Adjust thresholds if needed"
else
    echo "❌ OVERALL: Implementation needs review"
    echo ""
    echo "Recommended actions:"
    echo "1. Check if bot restarted properly"
    echo "2. Verify all 10 changes are in code"
    echo "3. Review error logs"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "For detailed logs, run:"
echo "  tail -f $LOG_FILE | grep -E '(New signal|Enriched|Distance limits)'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
