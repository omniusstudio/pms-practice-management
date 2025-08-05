#!/bin/bash
# Install git hooks for test pyramid enforcement

set -e

echo "🔧 Installing git hooks for test pyramid enforcement..."

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
PRE_COMMIT_SCRIPT="$PROJECT_ROOT/scripts/pre-commit-test-gates.sh"

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if pre-commit script exists
if [ ! -f "$PRE_COMMIT_SCRIPT" ]; then
    echo "❌ Error: Pre-commit script not found at $PRE_COMMIT_SCRIPT"
    exit 1
fi

# Make sure the pre-commit script is executable
chmod +x "$PRE_COMMIT_SCRIPT"

# Create or update the pre-commit hook
PRE_COMMIT_HOOK="$GIT_HOOKS_DIR/pre-commit"

cat > "$PRE_COMMIT_HOOK" << 'EOF'
#!/bin/bash
# Git pre-commit hook for test pyramid enforcement
# This hook runs the test gates before allowing commits

# Get the project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PRE_COMMIT_SCRIPT="$PROJECT_ROOT/scripts/pre-commit-test-gates.sh"

# Run the pre-commit test gates
if [ -f "$PRE_COMMIT_SCRIPT" ]; then
    exec "$PRE_COMMIT_SCRIPT"
else
    echo "⚠️  Warning: Pre-commit test gates script not found"
    echo "   Expected at: $PRE_COMMIT_SCRIPT"
    echo "   Allowing commit to proceed..."
    exit 0
fi
EOF

# Make the hook executable
chmod +x "$PRE_COMMIT_HOOK"

echo "✅ Git hooks installed successfully!"
echo ""
echo "📋 What was installed:"
echo "  • Pre-commit hook: $PRE_COMMIT_HOOK"
echo "  • Test gates script: $PRE_COMMIT_SCRIPT"
echo ""
echo "🔍 The pre-commit hook will now:"
echo "  • Validate test pyramid structure"
echo "  • Run tests for changed files"
echo "  • Check coverage thresholds"
echo "  • Enforce HIPAA compliance tests"
echo "  • Run security and lint checks"
echo ""
echo "⚙️  To bypass hooks (not recommended):"
echo "  git commit --no-verify"
echo ""
echo "🗑️  To uninstall hooks:"
echo "  rm $PRE_COMMIT_HOOK"
echo ""
echo "🎉 Ready to enforce test pyramid requirements!"