#!/bin/bash

# init-feature.sh - Initialize a new feature branch with proper workflow
# Usage: ./scripts/init-feature.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "🚀 Feature Branch Initialization Script"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
}

# Function to validate branch name
validate_branch_name() {
    local branch_name="$1"

    # Check if branch name is empty
    if [[ -z "$branch_name" ]]; then
        print_error "Branch name cannot be empty"
        return 1
    fi

    # Check for valid characters (alphanumeric, hyphens, underscores, forward slashes)
    if [[ ! "$branch_name" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
        print_error "Branch name contains invalid characters. Use only letters, numbers, hyphens, underscores, and forward slashes."
        return 1
    fi

    # Check if branch name starts with a letter
    if [[ ! "$branch_name" =~ ^[a-zA-Z] ]]; then
        print_error "Branch name must start with a letter"
        return 1
    fi

    # Check length (reasonable limit)
    if [[ ${#branch_name} -gt 50 ]]; then
        print_error "Branch name is too long (max 50 characters)"
        return 1
    fi

    return 0
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository. Please run this script from the project root."
        exit 1
    fi
}

# Function to check if main branch exists
check_main_branch() {
    if ! git show-ref --verify --quiet refs/heads/main; then
        if git show-ref --verify --quiet refs/heads/master; then
            print_warning "Using 'master' branch instead of 'main'"
            MAIN_BRANCH="master"
        else
            print_error "Neither 'main' nor 'master' branch found"
            exit 1
        fi
    else
        MAIN_BRANCH="main"
    fi
}

# Function to check for uncommitted changes
check_working_directory() {
    if ! git diff-index --quiet HEAD --; then
        print_error "You have uncommitted changes. Please commit or stash them before creating a new feature branch."
        echo
        print_info "Uncommitted changes:"
        git status --porcelain
        exit 1
    fi
}

# Function to update main branch
update_main_branch() {
    print_info "Updating $MAIN_BRANCH branch..."

    # Fetch latest changes
    if ! git fetch origin; then
        print_error "Failed to fetch from origin"
        exit 1
    fi

    # Switch to main branch
    if ! git checkout "$MAIN_BRANCH"; then
        print_error "Failed to checkout $MAIN_BRANCH branch"
        exit 1
    fi

    # Pull latest changes
    if ! git pull origin "$MAIN_BRANCH"; then
        print_error "Failed to pull latest changes from $MAIN_BRANCH"
        exit 1
    fi

    print_success "$MAIN_BRANCH branch updated successfully"
}

# Function to create feature branch
create_feature_branch() {
    local branch_name="$1"

    print_info "Creating feature branch: $branch_name"

    # Check if branch already exists
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        print_error "Branch '$branch_name' already exists locally"
        exit 1
    fi

    # Check if branch exists on remote
    if git show-ref --verify --quiet "refs/remotes/origin/$branch_name"; then
        print_error "Branch '$branch_name' already exists on remote"
        exit 1
    fi

    # Create and checkout the new branch
    if ! git checkout -b "$branch_name"; then
        print_error "Failed to create branch '$branch_name'"
        exit 1
    fi

    print_success "Feature branch '$branch_name' created and checked out"
}

# Function to display PR process reminder
show_pr_process_reminder() {
    local branch_name="$1"

    echo
    echo -e "${GREEN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "🎉 Feature branch setup complete!"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"

    print_info "Current branch: $(git branch --show-current)"
    echo

    print_warning "📋 IMPORTANT: Pull Request Process Reminder"
    echo
    echo "Before creating your PR, make sure to:"
    echo
    echo "1. 🧪 Test your code locally"
    echo "   • Run all tests: make test (or your project's test command)"
    echo "   • Verify functionality works as expected"
    echo
    echo "2. 🔒 Security check"
    echo "   • Remove any secrets, API keys, or sensitive data"
    echo "   • Review code for security vulnerabilities"
    echo
    echo "3. ✅ Ensure all tests pass"
    echo "   • Unit tests, integration tests, and linting"
    echo "   • Fix any failing tests before pushing"
    echo
    echo "4. 🚀 Deploy to staging (if applicable)"
    echo "   • Test your changes in staging environment"
    echo "   • Verify no breaking changes"
    echo
    echo "5. 📝 Link to issue"
    echo "   • Reference the related issue number in your PR"
    echo "   • Use format: 'Fixes #123' or 'Closes #123'"
    echo
    echo "6. 📤 Push and create PR"
    echo "   • git push -u origin $branch_name"
    echo "   • Create PR through GitHub UI or CLI"
    echo
    echo "7. 👥 Request reviews"
    echo "   • At least 1 reviewer required (as per branch protection)"
    echo "   • Address review feedback promptly"
    echo

    print_info "Branch protection rules are in place:"
    echo "   • Direct commits to main are blocked"
    echo "   • PR reviews are required"
    echo "   • All CI checks must pass"
    echo "   • Linear history is enforced"
    echo

    print_success "Happy coding! 🚀"
    echo
}

# Main execution
main() {
    print_header

    # Pre-flight checks
    check_git_repo
    check_main_branch
    check_working_directory

    # Get branch name from user
    echo
    print_info "Let's create a new feature branch!"
    echo

    # Suggest branch naming conventions
    print_info "Branch naming suggestions:"
    echo "   • feature/user-authentication"
    echo "   • feature/payment-integration"
    echo "   • bugfix/login-error"
    echo "   • hotfix/security-patch"
    echo

    while true; do
        read -p "Enter feature branch name: " branch_name

        if validate_branch_name "$branch_name"; then
            break
        fi
        echo
    done

    echo
    print_info "Branch name: $branch_name"

    # Confirm with user
    read -p "Proceed with creating this branch? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled"
        exit 0
    fi

    echo

    # Execute the workflow
    update_main_branch
    create_feature_branch "$branch_name"
    show_pr_process_reminder "$branch_name"
}

# Run main function
main "$@"
