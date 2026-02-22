#!/bin/bash

# Setup script for validation environment
# Creates virtual environment, installs dependencies, runs validation suite

set -e

echo "================================================================================"
echo "VALIDATION ENVIRONMENT SETUP"
echo "Stabilization PR - Regression Suite"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Create virtual environment
echo -e "${YELLOW}Step 1: Creating virtual environment...${NC}"
if [ -d "venv_validation" ]; then
    echo "Removing existing venv_validation..."
    rm -rf venv_validation
fi
python3 -m venv venv_validation
echo -e "${GREEN}✅ Virtual environment created: venv_validation${NC}"
echo ""

# Step 2: Activate virtual environment
echo -e "${YELLOW}Step 2: Activating virtual environment...${NC}"
source venv_validation/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo ""

# Step 3: Upgrade pip
echo -e "${YELLOW}Step 3: Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✅ Pip upgraded${NC}"
echo ""

# Step 4: Install dependencies
echo -e "${YELLOW}Step 4: Installing dependencies from requirements.txt...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Step 5: Run validation suite
echo "================================================================================"
echo "RUNNING VALIDATION SUITE"
echo "================================================================================"
echo ""

echo -e "${YELLOW}Running validate_timeframe_contract.py...${NC}"
python3 validate_timeframe_contract.py
echo -e "${GREEN}✅ Timeframe contract validation: PASS${NC}"
echo ""

echo -e "${YELLOW}Running validate_component_flow.py...${NC}"
python3 validate_component_flow.py
echo -e "${GREEN}✅ Component flow validation: PASS${NC}"
echo ""

echo -e "${YELLOW}Running validate_scenario_logic.py...${NC}"
python3 validate_scenario_logic.py
echo -e "${GREEN}✅ Scenario logic validation: PASS${NC}"
echo ""

echo -e "${YELLOW}Running validate_message_integrity.py...${NC}"
python3 validate_message_integrity.py
echo -e "${GREEN}✅ Message integrity validation: PASS${NC}"
echo ""

echo -e "${YELLOW}Running validate_regression_suite.py...${NC}"
python3 validate_regression_suite.py
echo -e "${GREEN}✅ Regression suite validation: PASS${NC}"
echo ""

echo -e "${YELLOW}Running master orchestrator (run_all_validations.py)...${NC}"
python3 run_all_validations.py
echo ""

# Step 6: Summary
echo "================================================================================"
echo "VALIDATION COMPLETE"
echo "================================================================================"
echo ""
echo -e "${GREEN}✅ All validation scripts executed successfully${NC}"
echo -e "${GREEN}✅ Virtual environment: venv_validation${NC}"
echo -e "${GREEN}✅ All dependencies installed${NC}"
echo -e "${GREEN}✅ All validations passed${NC}"
echo ""
echo "To use this environment again:"
echo "  source venv_validation/bin/activate"
echo ""
echo "To deactivate:"
echo "  deactivate"
echo ""
echo "================================================================================"
echo -e "${GREEN}STATUS: PASS${NC}"
echo -e "${GREEN}RECOMMENDATION: APPROVED FOR MERGE${NC}"
echo "================================================================================"
