#!/bin/bash

# Repository Maintenance Script
# Run this script monthly to keep the repository clean

set -e

echo "🧹 Starting repository maintenance..."

# Navigate to repository root
cd "$(dirname "$0")/.."

# Function to print section headers
print_section() {
    echo
    echo "=== $1 ==="
}

# Function to check file count and size
check_cleanup_impact() {
    local description="$1"
    local find_pattern="$2"
    
    local count=$(find . $find_pattern 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        echo "⚠️  Found $count $description files"
        find . $find_pattern 2>/dev/null | head -5
        if [ "$count" -gt 5 ]; then
            echo "   ... and $((count - 5)) more"
        fi
        return 1
    else
        echo "✅ No $description files found"
        return 0
    fi
}

print_section "Checking for temporary files"
check_cleanup_impact "temporary" "-name '*.pyc' -o -name '*.pyo' -o -name '__pycache__' -o -name '*~' -o -name '*.tmp' -o -name '*.temp'"

print_section "Checking for backup files"
check_cleanup_impact "backup" "-name '*.bak' -o -name '*.old' -o -name '*.orig'"

print_section "Checking for large generated files"
if [ -f "test_pyramid_report.json" ] || [ -f "test_integration.db" ] || [ -f "apps/frontend/eslint-report.json" ]; then
    echo "⚠️  Found generated files that should be in .gitignore:"
    ls -lh test_pyramid_report.json test_integration.db apps/frontend/eslint-report.json 2>/dev/null || true
else
    echo "✅ No large generated files found"
fi

print_section "Checking for disabled files"
check_cleanup_impact "disabled" "-name '*.disabled'"

print_section "Repository size analysis"
echo "📊 Current repository size breakdown:"
du -sh * 2>/dev/null | sort -hr | head -10

print_section "Performance tests size"
if [ -d "tests/performance/node_modules" ]; then
    perf_size=$(du -sh tests/performance/node_modules 2>/dev/null | cut -f1)
    echo "📦 Performance tests node_modules: $perf_size"
    echo "💡 Consider running: ./scripts/cleanup-performance-tests.sh"
else
    echo "✅ Performance tests node_modules not found or already optimized"
fi

print_section "Git repository health"
echo "📈 Repository statistics:"
echo "   Commits: $(git rev-list --count HEAD)"
echo "   Branches: $(git branch -r | wc -l | tr -d ' ')"
echo "   Repository size: $(du -sh .git | cut -f1)"

# Check for large files in git history
echo "🔍 Checking for large files in repository:"
git ls-files | xargs ls -l 2>/dev/null | awk '$5 > 1048576 {print $5/1048576 "MB", $9}' | sort -nr | head -5

print_section "Maintenance recommendations"
echo "📋 Regular maintenance tasks:"
echo "   • Run this script monthly"
echo "   • Review and remove old branches"
echo "   • Update dependencies regularly"
echo "   • Clean up performance test dependencies"
echo "   • Review TODO comments and placeholder code"

echo
echo "✅ Repository maintenance check completed!"
echo "📅 Next recommended run: $(date -d '+1 month' '+%Y-%m-%d' 2>/dev/null || date -v+1m '+%Y-%m-%d' 2>/dev/null || echo 'in 1 month')"