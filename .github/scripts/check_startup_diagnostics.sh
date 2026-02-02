#!/bin/bash

###############################################################################
# Startup Diagnostics Guard - CI Enforcement Script
#
# This script enforces the non-blocking startup diagnostics policy by
# detecting violations that would cause the bot to block during startup.
#
# POLICY: Diagnostics MUST NOT block bot startup
# - Diagnostics must be wrapped in run_startup_diagnostics_safe()
# - send_startup_message() must be called BEFORE diagnostics
# - No direct run_quick_check() calls in post_init()
#
# Exit Codes:
#   0 - All checks passed
#   1 - Violation detected
###############################################################################

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VIOLATION_FOUND=0
BOT_FILE="bot.py"

# Check if bot.py exists
if [ ! -f "$BOT_FILE" ]; then
    echo -e "${RED}❌ ERROR: bot.py not found${NC}"
    exit 1
fi

###############################################################################
# Helper Function: Extract post_init function
###############################################################################

extract_post_init() {
    # Extract post_init function (from its definition to the next top-level async def)
    # Assumes 4-space indentation for class methods
    sed -n '/^    async def post_init/,/^    async def \|^async def /p' "$BOT_FILE" | head -n -1
}

echo "🔍 Startup Diagnostics Guard - Checking for violations..."
echo ""

###############################################################################
# RULE 1: Direct run_quick_check() call in post_init()
###############################################################################
echo "📋 Rule 1: Checking for direct run_quick_check() in post_init()..."

# Extract post_init function using helper
POST_INIT_CONTENT=$(extract_post_init)

# Check if post_init contains direct run_quick_check call
# We're looking for "run_quick_check()" that's NOT inside a comment or string
if echo "$POST_INIT_CONTENT" | grep -v "^[[:space:]]*#" | grep -q "run_quick_check()"; then
    # Check if it's in run_startup_diagnostics_safe (which is allowed)
    if ! echo "$POST_INIT_CONTENT" | grep -B 5 "run_quick_check()" | grep -q "run_startup_diagnostics_safe"; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ CI GUARD FAILURE: Blocking Startup Diagnostics Detected${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "VIOLATION: Direct run_quick_check() call found in post_init()"
        echo ""
        echo "This violates the non-blocking startup diagnostics policy:"
        echo "  - Diagnostics MUST be wrapped in run_startup_diagnostics_safe()"
        echo "  - Diagnostics MUST NOT block bot startup"
        echo "  - Diagnostics MUST come AFTER send_startup_message()"
        echo ""
        echo "FOUND IN: bot.py (post_init function)"
        
        # Try to find the line number
        LINE_NUM=$(grep -n "async def post_init" "$BOT_FILE" | cut -d: -f1)
        if [ -n "$LINE_NUM" ]; then
            echo "  Line ~$LINE_NUM (post_init function)"
        fi
        
        echo ""
        echo "HOW TO FIX:"
        echo "  1. Use run_startup_diagnostics_safe() instead of direct calls"
        echo "  2. Ensure send_startup_message() is called FIRST"
        echo "  3. See PR #235 for correct implementation"
        echo ""
        echo "CORRECT PATTERN:"
        echo "  async def post_init(application):"
        echo "      await send_startup_message(application)  # FIRST"
        echo "      diagnostic_report = await run_startup_diagnostics_safe()  # SECOND"
        echo "      await send_diagnostic_report(application, diagnostic_report)"
        echo ""
        echo "For details, see NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        VIOLATION_FOUND=1
    fi
fi

if [ $VIOLATION_FOUND -eq 0 ]; then
    echo -e "${GREEN}  ✅ No direct run_quick_check() in post_init()${NC}"
fi

###############################################################################
# RULE 2: Diagnostics before startup message (wrong order)
###############################################################################
echo "📋 Rule 2: Checking startup message order..."

# Extract post_init function using helper (removes comments and empty lines)
POST_INIT_LINES=$(extract_post_init | grep -v "^[[:space:]]*#" | grep -v "^[[:space:]]*$")

# Find line numbers within post_init for send_startup_message and run_startup_diagnostics_safe
MESSAGE_LINE=$(echo "$POST_INIT_LINES" | grep -n "send_startup_message" | head -1 | cut -d: -f1)
DIAGNOSTIC_LINE=$(echo "$POST_INIT_LINES" | grep -n "run_startup_diagnostics_safe\|run_quick_check" | head -1 | cut -d: -f1)

if [ -n "$DIAGNOSTIC_LINE" ] && [ -n "$MESSAGE_LINE" ]; then
    # Compare line numbers - diagnostic must come AFTER message
    if [ "$DIAGNOSTIC_LINE" -lt "$MESSAGE_LINE" ]; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ CI GUARD FAILURE: Wrong Startup Order Detected${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "VIOLATION: Diagnostics called before startup message"
        echo ""
        echo "This violates the non-blocking startup diagnostics policy:"
        echo "  - send_startup_message() MUST be called FIRST"
        echo "  - Diagnostics come SECOND (to ensure operational confirmation)"
        echo ""
        echo "FOUND IN: bot.py (post_init function)"
        echo ""
        echo "HOW TO FIX:"
        echo "  1. Move send_startup_message() to the TOP of post_init()"
        echo "  2. Call diagnostics AFTER the startup message"
        echo ""
        echo "CORRECT ORDER:"
        echo "  async def post_init(application):"
        echo "      # STEP 1: Send startup message FIRST"
        echo "      await send_startup_message(application)"
        echo "      "
        echo "      # STEP 2: Run diagnostics SECOND"
        echo "      diagnostic_report = await run_startup_diagnostics_safe()"
        echo "      "
        echo "      # STEP 3: Send diagnostic report"
        echo "      await send_diagnostic_report(application, diagnostic_report)"
        echo ""
        echo "For details, see NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        VIOLATION_FOUND=1
    fi
fi

if [ $VIOLATION_FOUND -eq 0 ]; then
    echo -e "${GREEN}  ✅ Correct startup order (message before diagnostics)${NC}"
fi

###############################################################################
# RULE 3: Check for blocking patterns in post_init
###############################################################################
echo "📋 Rule 3: Checking for blocking patterns in post_init()..."

# Check for bare try/except around run_quick_check in post_init
# This would indicate blocking error handling
if echo "$POST_INIT_CONTENT" | grep -A 10 "try:" | grep -q "run_quick_check()"; then
    # Check if it's inside run_startup_diagnostics_safe (which is OK)
    SAFE_WRAPPER=$(sed -n '/async def run_startup_diagnostics_safe/,/^async def /p' "$BOT_FILE")
    
    if ! echo "$SAFE_WRAPPER" | grep -q "run_quick_check()"; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}❌ CI GUARD FAILURE: Blocking Pattern Detected${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        echo "VIOLATION: Blocking try/except around diagnostics in post_init()"
        echo ""
        echo "This violates the non-blocking startup diagnostics policy:"
        echo "  - Direct exception handling of diagnostics can block startup"
        echo "  - Use run_startup_diagnostics_safe() which handles errors internally"
        echo ""
        echo "FOUND IN: bot.py (post_init function)"
        echo ""
        echo "HOW TO FIX:"
        echo "  1. Remove try/except from post_init()"
        echo "  2. Use run_startup_diagnostics_safe() which is already fail-safe"
        echo ""
        echo "CORRECT PATTERN:"
        echo "  async def post_init(application):"
        echo "      await send_startup_message(application)"
        echo "      # No try/except needed - run_startup_diagnostics_safe handles errors"
        echo "      diagnostic_report = await run_startup_diagnostics_safe()"
        echo "      await send_diagnostic_report(application, diagnostic_report)"
        echo ""
        echo "For details, see NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        VIOLATION_FOUND=1
    fi
fi

if [ $VIOLATION_FOUND -eq 0 ]; then
    echo -e "${GREEN}  ✅ No blocking patterns detected${NC}"
fi

###############################################################################
# Summary
###############################################################################
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $VIOLATION_FOUND -eq 1 ]; then
    echo -e "${RED}❌ STARTUP DIAGNOSTICS GUARD: FAILED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "One or more violations detected. See error messages above."
    echo ""
    echo "This PR introduces changes that could block bot startup."
    echo "Please review the non-blocking diagnostics policy and fix the violations."
    echo ""
    echo "📚 Documentation: NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md"
    echo "📚 CI Guard Info: docs/CI_STARTUP_GUARD.md"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ STARTUP DIAGNOSTICS GUARD: PASSED${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "All checks passed! No blocking startup diagnostics detected."
    echo ""
    exit 0
fi
