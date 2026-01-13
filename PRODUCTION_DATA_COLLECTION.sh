#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# PRODUCTION DATA COLLECTION SCRIPT
# ═══════════════════════════════════════════════════════════════════
# Purpose: Collect production data for audit analysis
# Type: READ-ONLY - NO CHANGES TO SYSTEM
# Date: 2026-01-13
# Repository: galinborisov10-art/Crypto-signal-bot
# ═══════════════════════════════════════════════════════════════════

set -e  # Exit on error

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  PRODUCTION DATA COLLECTION - AUDIT                   ║"
echo "║  READ-ONLY MODE - NO SYSTEM CHANGES                   ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "⏰ Started at: $(date)"
echo ""

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Detect base path (server vs codespace vs local)
if [ -d "/root/Crypto-signal-bot" ]; then
    BASE_PATH="/root/Crypto-signal-bot"
    LOG_FILE="/root/Crypto-signal-bot/bot.log"
elif [ -d "/workspaces/Crypto-signal-bot" ]; then
    BASE_PATH="/workspaces/Crypto-signal-bot"
    LOG_FILE="/workspaces/Crypto-signal-bot/bot.log"
else
    BASE_PATH="$(pwd)"
    LOG_FILE="$(pwd)/bot.log"
fi

echo "📂 Base Path: $BASE_PATH"
echo "📄 Log File: $LOG_FILE"
echo ""

# Create audit directory
AUDIT_DIR="$BASE_PATH/audit_data"
mkdir -p "$AUDIT_DIR"
cd "$AUDIT_DIR"

echo "💾 Audit data will be saved to: $AUDIT_DIR"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "⚠️ WARNING: Log file not found at $LOG_FILE"
    echo "   Creating placeholder files with 'NO DATA' message"
    echo ""
    LOG_LINES=0
else
    LOG_LINES=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
    echo "✅ Log file found: $LOG_LINES lines"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════════
# DATA COLLECTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

collect_data() {
    local section=$1
    local output_file=$2
    local grep_pattern=$3
    local description=$4
    
    echo "=== $section ==="
    
    if [ $LOG_LINES -eq 0 ]; then
        echo "NO DATA - Log file not found or empty" > "$output_file"
    else
        tail -5000 "$LOG_FILE" 2>/dev/null | grep -E "$grep_pattern" > "$output_file" 2>/dev/null || echo "NO MATCHES FOUND" > "$output_file"
    fi
    
    local matches=$(grep -c -v "^NO" "$output_file" 2>/dev/null || echo "0")
    echo "   $description"
    echo "   Saved to: $output_file ($matches matches)"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# 1. TIMEFRAME ANALYSIS
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "1. TIMEFRAME USAGE" \
    "timeframe_usage.txt" \
    "generate_signal|timeframe|Generating.*signal|1H|2H|4H|1D|1W" \
    "Analyzing which timeframes are used in signal generation"

# ═══════════════════════════════════════════════════════════════════
# 2. STEP 7b BLOCKING ANALYSIS
# ═══════════════════════════════════════════════════════════════════

echo "=== 2. STEP 7b BLOCKING ==="
if [ $LOG_LINES -eq 0 ]; then
    echo "NO DATA - Log file not found or empty" > "step7b_blocks.txt"
else
    {
        echo "=== BLOCKED SIGNALS ==="
        tail -5000 "$LOG_FILE" 2>/dev/null | grep "BLOCKED at Step 7b" || echo "No blocks found"
        echo ""
        echo "=== PASSED STEP 7 ==="
        tail -5000 "$LOG_FILE" 2>/dev/null | grep "PASSED Step 7" || echo "No passes found"
    } > "step7b_blocks.txt"
fi
echo "   Analyzing HTF bias blocking behavior"
echo "   Saved to: step7b_blocks.txt"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 3. SIGNAL TYPE DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "3. SIGNAL TYPES" \
    "signal_types.txt" \
    "BUY signal|SELL signal|HOLD signal|SignalType\." \
    "Distribution of signal types (BUY/SELL/HOLD)"

# ═══════════════════════════════════════════════════════════════════
# 4. CONFIDENCE SCORE ANALYSIS
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "4. CONFIDENCE SCORES" \
    "confidence_scores.txt" \
    "Confidence:|confidence|Base Confidence|Final.*[0-9]+%" \
    "Confidence score calculations and components"

# ═══════════════════════════════════════════════════════════════════
# 5. ICT COMPONENT DETECTION
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "5. ICT COMPONENTS" \
    "component_detection.txt" \
    "Order Blocks:|FVG|Fair Value Gap|Liquidity|S/R Levels:|Support|Resistance" \
    "Detection rates of ICT components"

# ═══════════════════════════════════════════════════════════════════
# 6. HTF BIAS USAGE
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "6. HTF BIAS" \
    "htf_bias.txt" \
    "HTF Bias|HTF bias|Final Bias|BULLISH|BEARISH|NEUTRAL|RANGING" \
    "HTF bias determination and usage"

# ═══════════════════════════════════════════════════════════════════
# 7. ACTIVE TRADE MONITORING
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "7. TRADE MONITORING" \
    "trade_monitoring.txt" \
    "25%|50%|75%|85%|checkpoint|re-analysis|PARTIAL|TP reached|SL hit" \
    "Active trade monitoring and checkpoints"

# ═══════════════════════════════════════════════════════════════════
# 8. S/R VALIDATION
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "8. S/R VALIDATION" \
    "sr_validation.txt" \
    "S/R|Support|Resistance|SR.*Level|near.*S/R|conflict" \
    "Support/Resistance validation and conflicts"

# ═══════════════════════════════════════════════════════════════════
# 9. BTC INFLUENCE
# ═══════════════════════════════════════════════════════════════════

collect_data \
    "9. BTC INFLUENCE" \
    "btc_influence.txt" \
    "BTC|correlation|btc.*impact|divergence|aligned" \
    "BTC correlation and influence on altcoin signals"

# ═══════════════════════════════════════════════════════════════════
# 10. PIPELINE STEP TRACKING
# ═══════════════════════════════════════════════════════════════════

echo "=== 10. PIPELINE STEPS ==="
if [ $LOG_LINES -eq 0 ]; then
    echo "NO DATA - Log file not found or empty" > "pipeline_steps.txt"
else
    {
        echo "=== 12-STEP PIPELINE EXECUTION ==="
        tail -5000 "$LOG_FILE" 2>/dev/null | grep -E "Step [0-9]+|BLOCKED at Step|PASSED Step" || echo "No pipeline logs found"
    } > "pipeline_steps.txt"
fi
echo "   Tracking which steps block/pass signals"
echo "   Saved to: pipeline_steps.txt"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 11. STATISTICS SUMMARY
# ═══════════════════════════════════════════════════════════════════

echo "=== 11. STATISTICS SUMMARY ==="

if [ $LOG_LINES -eq 0 ]; then
    cat > stats_summary.txt << 'EOF'
═══════════════════════════════════════════════════════════
STATISTICS SUMMARY - NO DATA AVAILABLE
═══════════════════════════════════════════════════════════

⚠️ Log file not found or empty

Please ensure:
1. Bot is running and generating logs
2. Log file path is correct: $LOG_FILE
3. Log file has sufficient data (at least 100 lines)

EOF
else
    BUY_COUNT=$(grep -c "BUY signal" signal_types.txt 2>/dev/null || echo "0")
    SELL_COUNT=$(grep -c "SELL signal" signal_types.txt 2>/dev/null || echo "0")
    HOLD_COUNT=$(grep -c "HOLD signal" signal_types.txt 2>/dev/null || echo "0")
    BLOCKED_7B=$(grep -c "BLOCKED at Step 7b" step7b_blocks.txt 2>/dev/null || echo "0")
    PASSED_7=$(grep -c "PASSED Step 7" step7b_blocks.txt 2>/dev/null || echo "0")
    
    cat > stats_summary.txt << EOF
═══════════════════════════════════════════════════════════
STATISTICS SUMMARY
═══════════════════════════════════════════════════════════

📊 SIGNAL DISTRIBUTION (last 5000 log lines)
───────────────────────────────────────────────────────────
   BUY signals:  $BUY_COUNT
   SELL signals: $SELL_COUNT
   HOLD signals: $HOLD_COUNT
   ─────────────────
   TOTAL:        $((BUY_COUNT + SELL_COUNT + HOLD_COUNT))

🚧 STEP 7b BLOCKING ANALYSIS
───────────────────────────────────────────────────────────
   Blocked at Step 7b: $BLOCKED_7B
   Passed Step 7:      $PASSED_7
   ─────────────────
   Block Rate:         $(awk "BEGIN {if ($PASSED_7 + $BLOCKED_7B > 0) printf \"%.1f%%\", ($BLOCKED_7B / ($PASSED_7 + $BLOCKED_7B) * 100); else print \"N/A\"}")

📈 TIMEFRAMES DETECTED
───────────────────────────────────────────────────────────
EOF

    if [ -f "timeframe_usage.txt" ]; then
        grep -oE "1H|2H|4H|1D|1W|timeframe.*=.*['\"]?[0-9]+[HDW]" timeframe_usage.txt 2>/dev/null | \
            sort | uniq -c | sort -rn >> stats_summary.txt || echo "   No timeframe data" >> stats_summary.txt
    else
        echo "   No timeframe data" >> stats_summary.txt
    fi

    cat >> stats_summary.txt << EOF

🧩 ICT COMPONENTS
───────────────────────────────────────────────────────────
   Order Blocks: $(grep -c "Order Block" component_detection.txt 2>/dev/null || echo "0")
   FVG Zones:    $(grep -c "FVG\|Fair Value Gap" component_detection.txt 2>/dev/null || echo "0")
   Liquidity:    $(grep -c "Liquidity" component_detection.txt 2>/dev/null || echo "0")
   S/R Levels:   $(grep -c "S/R\|Support\|Resistance" component_detection.txt 2>/dev/null || echo "0")

📊 CONFIDENCE SCORES
───────────────────────────────────────────────────────────
   Avg Confidence: $(grep -oE "[0-9]+\.[0-9]+%" confidence_scores.txt 2>/dev/null | grep -oE "[0-9]+\.[0-9]+" | awk '{sum+=$1; count++} END {if (count>0) printf "%.1f%%", sum/count; else print "N/A"}')
   Min Threshold:  60% (configured)

🔗 BTC CORRELATION
───────────────────────────────────────────────────────────
   BTC mentions:  $(grep -c "BTC\|correlation" btc_influence.txt 2>/dev/null || echo "0")
   Divergences:   $(grep -c "divergence" btc_influence.txt 2>/dev/null || echo "0")

⏱️  TRADE MONITORING
───────────────────────────────────────────────────────────
   25% checkpoints: $(grep -c "25%" trade_monitoring.txt 2>/dev/null || echo "0")
   50% checkpoints: $(grep -c "50%" trade_monitoring.txt 2>/dev/null || echo "0")
   75% checkpoints: $(grep -c "75%" trade_monitoring.txt 2>/dev/null || echo "0")
   85% checkpoints: $(grep -c "85%" trade_monitoring.txt 2>/dev/null || echo "0")

═══════════════════════════════════════════════════════════
Collection completed at: $(date)
Log lines analyzed: $LOG_LINES (last 5000 lines)
═══════════════════════════════════════════════════════════
EOF
fi

cat stats_summary.txt
echo ""

# ═══════════════════════════════════════════════════════════════════
# 12. METADATA FILE
# ═══════════════════════════════════════════════════════════════════

cat > audit_metadata.json << EOF
{
  "collection_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "base_path": "$BASE_PATH",
  "log_file": "$LOG_FILE",
  "log_lines_total": $LOG_LINES,
  "log_lines_analyzed": 5000,
  "audit_directory": "$AUDIT_DIR",
  "files_created": [
    "timeframe_usage.txt",
    "step7b_blocks.txt",
    "signal_types.txt",
    "confidence_scores.txt",
    "component_detection.txt",
    "htf_bias.txt",
    "trade_monitoring.txt",
    "sr_validation.txt",
    "btc_influence.txt",
    "pipeline_steps.txt",
    "stats_summary.txt",
    "audit_metadata.json"
  ],
  "status": "completed"
}
EOF

echo "✅ Created metadata file: audit_metadata.json"
echo ""

# ═══════════════════════════════════════════════════════════════════
# COMPLETION SUMMARY
# ═══════════════════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════════╗"
echo "║  DATA COLLECTION COMPLETE                             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "📁 All data saved in: $AUDIT_DIR"
echo ""
echo "📋 Files created:"
echo "   1. timeframe_usage.txt       - Timeframe patterns"
echo "   2. step7b_blocks.txt         - HTF blocking analysis"
echo "   3. signal_types.txt          - BUY/SELL/HOLD distribution"
echo "   4. confidence_scores.txt     - Confidence calculations"
echo "   5. component_detection.txt   - ICT component rates"
echo "   6. htf_bias.txt              - HTF bias usage"
echo "   7. trade_monitoring.txt      - Trade checkpoints"
echo "   8. sr_validation.txt         - S/R validation"
echo "   9. btc_influence.txt         - BTC correlation"
echo "   10. pipeline_steps.txt       - 12-step execution"
echo "   11. stats_summary.txt        - Summary statistics"
echo "   12. audit_metadata.json      - Collection metadata"
echo ""
echo "📊 Quick Stats:"
if [ $LOG_LINES -eq 0 ]; then
    echo "   ⚠️ No log data available"
else
    echo "   Signals: $((BUY_COUNT + SELL_COUNT + HOLD_COUNT)) total (BUY: $BUY_COUNT, SELL: $SELL_COUNT, HOLD: $HOLD_COUNT)"
    echo "   Step 7b blocks: $BLOCKED_7B / $((PASSED_7 + BLOCKED_7B)) signals"
fi
echo ""
echo "🔍 Next Steps:"
echo "   1. Review files in $AUDIT_DIR"
echo "   2. Share findings with analysis team"
echo "   3. Update AUDIT_EXPECTATIONS_VS_REALITY.md with real data"
echo "   4. Complete AUDIT_CHECKLIST.md verification"
echo ""
echo "⏰ Completed at: $(date)"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
