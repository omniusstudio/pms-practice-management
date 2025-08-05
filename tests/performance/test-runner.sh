#!/bin/bash

# Simple Performance Test Runner
# Mental Health Practice Management System

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎯 Performance Test Runner${NC}"
echo "=============================="

# Check if Node.js is available
if ! command -v node >/dev/null 2>&1; then
    echo -e "${RED}❌ Node.js is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Node.js $(node --version) found${NC}"

# Check if npm is available
if ! command -v npm >/dev/null 2>&1; then
    echo -e "${RED}❌ npm is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ npm $(npm --version) found${NC}"

# Install dependencies if needed
if [ -f "package.json" ] && [ ! -d "node_modules" ]; then
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    npm install
fi

# Create directories
mkdir -p results reports

# Check if Artillery is available
if command -v artillery >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Artillery found globally${NC}"
elif npx artillery --version >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Artillery available via npx${NC}"
else
    echo -e "${YELLOW}⚠️  Installing Artillery...${NC}"
    npm install -g artillery || echo -e "${YELLOW}⚠️  Will use npx artillery${NC}"
fi

# Validate configuration files
if [ -f "performance-budgets.json" ]; then
    if node -e "require('./performance-budgets.json'); console.log('✅ Performance budgets valid');"; then
        echo -e "${GREEN}✅ Performance budgets configuration valid${NC}"
    else
        echo -e "${RED}❌ Invalid performance budgets configuration${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ performance-budgets.json not found${NC}"
    exit 1
fi

if [ -f "artillery.yml" ]; then
    echo -e "${GREEN}✅ Artillery configuration found${NC}"
else
    echo -e "${RED}❌ artillery.yml not found${NC}"
    exit 1
fi

if [ -f "baseline-test.js" ]; then
    if node -c "baseline-test.js" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ baseline-test.js syntax valid${NC}"
    else
        echo -e "${RED}❌ baseline-test.js has syntax errors${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ baseline-test.js not found${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}🚀 Running Performance Test...${NC}"
echo ""

# Run the performance test
if node baseline-test.js "$@"; then
    echo ""
    echo -e "${GREEN}✅ Performance test completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📊 Check the reports/ directory for detailed results${NC}"
    echo -e "${BLUE}📈 Check the results/ directory for raw data${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Performance test failed${NC}"
    echo ""
    echo -e "${YELLOW}💡 Check the logs above for details${NC}"
    exit 1
fi