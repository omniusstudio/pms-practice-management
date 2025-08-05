#!/bin/bash

# Performance Testing Setup Script
# Mental Health Practice Management System

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js is required but not installed"
        exit 1
    fi
    log_success "Node.js $(node --version) found"
    
    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm is required but not installed"
        exit 1
    fi
    log_success "npm $(npm --version) found"
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    if [ ! -f "package.json" ]; then
        log_error "package.json not found"
        exit 1
    fi
    
    npm install
    log_success "Dependencies installed"
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p results reports baselines
    log_success "Directories created"
}

validate_config() {
    log_info "Validating configuration files..."
    
    if [ -f "performance-budgets.json" ]; then
        if node -e "require('./performance-budgets.json'); console.log('Performance budgets valid');"; then
            log_success "Performance budgets configuration valid"
        else
            log_error "Invalid performance budgets configuration"
            exit 1
        fi
    else
        log_error "performance-budgets.json not found"
        exit 1
    fi
    
    if [ -f "artillery.yml" ]; then
        log_success "Artillery configuration found"
    else
        log_error "artillery.yml not found"
        exit 1
    fi
    
    if [ -f "baseline-test.js" ]; then
        if node -c "baseline-test.js" >/dev/null 2>&1; then
            log_success "baseline-test.js syntax valid"
        else
            log_error "baseline-test.js has syntax errors"
            exit 1
        fi
    else
        log_error "baseline-test.js not found"
        exit 1
    fi
}

setup_git_hooks() {
    log_info "Setting up Git hooks..."
    
    if git rev-parse --git-dir >/dev/null 2>&1; then
        hooks_dir="$(git rev-parse --git-dir)/hooks"
        mkdir -p "$hooks_dir"
        
        # Create pre-push hook
        cat > "$hooks_dir/pre-push" << 'HOOK_EOF'
#!/bin/bash
echo "Validating performance test configuration..."
cd "$(git rev-parse --show-toplevel)/tests/performance"
if [ -f "performance-budgets.json" ]; then
    if ! node -e "require('./performance-budgets.json')"; then
        echo "Invalid performance budgets configuration"
        exit 1
    fi
fi
echo "Performance configuration is valid"
HOOK_EOF
        
        chmod +x "$hooks_dir/pre-push"
        log_success "Git pre-push hook installed"
    else
        log_warning "Not in a Git repository, skipping Git hooks setup"
    fi
}

print_usage() {
    echo ""
    echo -e "${GREEN}🎯 Performance Testing Setup Complete!${NC}"
    echo ""
    echo -e "${BLUE}Available Commands:${NC}"
    echo "  npm test                    # Run performance test with budget validation"
    echo "  npm run test:baseline       # Run and save as new baseline"
    echo "  npm run test:quiet          # Run in quiet mode"
    echo "  npm run clean               # Clean previous results"
    echo ""
    echo -e "${BLUE}Manual Commands:${NC}"
    echo "  node baseline-test.js       # Run baseline test script directly"
    echo "  artillery run artillery.yml # Run Artillery test directly"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Ensure your target application is running"
    echo "  2. Review performance budgets in performance-budgets.json"
    echo "  3. Run your first test: npm test"
    echo "  4. Check generated reports in the reports/ directory"
    echo ""
    echo -e "${YELLOW}Note:${NC} This setup is HIPAA-compliant and uses synthetic test data."
    echo ""
}

main() {
    echo -e "${BLUE}"
    echo "======================================"
    echo "🎯 Performance Testing Setup"
    echo "Mental Health Practice Management"
    echo "======================================"
    echo -e "${NC}"
    
    check_prerequisites
    install_dependencies
    setup_directories
    validate_config
    setup_git_hooks
    
    print_usage
    
    log_success "Setup completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        print_usage
        exit 0
        ;;
    --validate-only)
        validate_config
        log_success "Configuration validation completed"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac