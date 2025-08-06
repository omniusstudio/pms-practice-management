#!/bin/bash

# Quick Requirements Test
echo "🎯 Quick Performance Testing Requirements Check"
echo "============================================="

# Test 1: Setup Script
echo "1. Setup Script Syntax:"
bash -n setup.sh && echo "   ✅ Valid" || echo "   ❌ Invalid"

# Test 2: Configuration Files
echo "2. Configuration Validation:"
node -e "require('./performance-budgets.json')" 2>/dev/null && echo "   ✅ performance-budgets.json valid" || echo "   ❌ performance-budgets.json invalid"
[ -f "artillery.yml" ] && echo "   ✅ artillery.yml exists" || echo "   ❌ artillery.yml missing"
[ -f "simple-test.yml" ] && echo "   ✅ simple-test.yml exists" || echo "   ❌ simple-test.yml missing"

# Test 3: Backend Health
echo "3. Backend Status:"
BACKEND_URL=${API_BASE_URL:-http://localhost:8000}
curl -s "$BACKEND_URL/healthz" > /dev/null 2>&1 && echo "   ✅ Backend responding" || echo "   ⚠️  Backend not responding"

# Test 4: Dependencies
echo "4. Dependencies:"
node --version > /dev/null 2>&1 && echo "   ✅ Node.js available" || echo "   ❌ Node.js missing"
npm --version > /dev/null 2>&1 && echo "   ✅ NPM available" || echo "   ❌ NPM missing"
npx artillery --version > /dev/null 2>&1 && echo "   ✅ Artillery available" || echo "   ❌ Artillery missing"

# Test 5: NPM Scripts
echo "5. NPM Scripts:"
npm run clean > /dev/null 2>&1 && echo "   ✅ Clean script works" || echo "   ❌ Clean script failed"

echo "============================================="
echo "✅ Quick validation complete!"
echo "For full validation, run: ./validate-requirements.sh"
