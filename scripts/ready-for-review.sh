#!/bin/bash

# ready-for-review.sh - Convert draft PR to ready for review
# This script helps transition a draft PR to ready status when development is complete

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions for colored output
print_error() {
    echo -e "${RED}❌ Error: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header() {
    echo
    echo -e "${BLUE}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "🚀 Ready for Review - Draft PR Converter"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"
    echo
}

# Function to check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
}

# Function to check if GitHub CLI is available
check_github_cli() {
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) is required but not installed"
        print_info "Please install GitHub CLI: https://cli.github.com/"
        exit 1
    fi

    # Check if user is authenticated
    if ! gh auth status &> /dev/null; then
        print_error "GitHub CLI is not authenticated"
        print_info "Please run: gh auth login"
        exit 1
    fi
}

# Function to get current branch
get_current_branch() {
    git branch --show-current
}

# Function to check if current branch has a PR
check_pr_exists() {
    local branch_name="$1"

    if ! gh pr view "$branch_name" &> /dev/null; then
        print_error "No PR found for branch '$branch_name'"
        print_info "Please create a PR first or switch to a branch with an existing PR"
        exit 1
    fi
}

# Function to check if PR is already ready
check_pr_status() {
    local branch_name="$1"

    local is_draft=$(gh pr view "$branch_name" --json isDraft --jq '.isDraft')

    if [[ "$is_draft" == "false" ]]; then
        print_warning "PR for branch '$branch_name' is already ready for review"
        local pr_url=$(gh pr view "$branch_name" --json url --jq '.url')
        print_info "PR URL: $pr_url"
        exit 0
    fi
}

# Function to run pre-review checks
run_pre_review_checks() {
    local branch_name="$1"

    print_info "Running pre-review checks..."
    echo

    # Check if there are uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        print_warning "You have uncommitted changes"
        read -p "Commit changes before marking ready? (Y/n): " commit_changes
        if [[ ! "$commit_changes" =~ ^[Nn]$ ]]; then
            print_info "Please commit your changes first, then run this script again"
            exit 1
        fi
    fi

    # Push any new commits
    print_info "Pushing latest changes..."
    if ! git push; then
        print_error "Failed to push changes"
        exit 1
    fi

    print_success "Pre-review checks completed"
    echo
}

# Function to show readiness checklist
show_readiness_checklist() {
    echo
    print_warning "📋 READINESS CHECKLIST"
    echo
    echo "Before marking this PR as ready for review, please confirm:"
    echo
    echo "✅ Code Quality:"
    echo "   • Code follows project standards and conventions"
    echo "   • No debugging code, console.logs, or temporary fixes"
    echo "   • Code is well-documented and commented"
    echo
    echo "✅ Testing:"
    echo "   • All existing tests pass locally"
    echo "   • New tests added for new functionality"
    echo "   • Edge cases and error scenarios covered"
    echo
    echo "✅ Security:"
    echo "   • No secrets, API keys, or sensitive data exposed"
    echo "   • Input validation and sanitization implemented"
    echo "   • Security best practices followed"
    echo
    echo "✅ Documentation:"
    echo "   • README updated if needed"
    echo "   • API documentation updated"
    echo "   • PR description is complete and accurate"
    echo
    echo "✅ Integration:"
    echo "   • Changes tested in development environment"
    echo "   • No breaking changes to existing functionality"
    echo "   • Database migrations (if any) are reversible"
    echo
}

# Function to convert draft PR to ready
convert_to_ready() {
    local branch_name="$1"

    print_info "Converting draft PR to ready for review..."

    if gh pr ready "$branch_name"; then
        print_success "PR successfully marked as ready for review!"

        local pr_url=$(gh pr view "$branch_name" --json url --jq '.url')
        local pr_title=$(gh pr view "$branch_name" --json title --jq '.title')

        echo
        print_info "PR Details:"
        echo "   Title: $pr_title"
        echo "   URL: $pr_url"
        echo

        # Show next steps
        print_warning "📋 NEXT STEPS"
        echo
        echo "1. 👥 Request reviewers"
        echo "   • Add at least 1 reviewer (required by branch protection)"
        echo "   • Consider adding relevant team members"
        echo
        echo "2. 🏷️  Add labels (if applicable)"
        echo "   • bug, feature, enhancement, etc."
        echo
        echo "3. 📝 Link to issues"
        echo "   • Use 'Fixes #123' or 'Closes #123' in PR description"
        echo
        echo "4. ⏳ Wait for CI/CD"
        echo "   • All status checks must pass"
        echo "   • Address any failing tests or linting issues"
        echo
        echo "5. 🔄 Address review feedback"
        echo "   • Respond to comments promptly"
        echo "   • Make requested changes"
        echo "   • Re-request review after changes"
        echo

        print_success "Your PR is now ready for review! 🎉"

    else
        print_error "Failed to convert PR to ready status"
        exit 1
    fi
}

# Main execution
main() {
    print_header

    # Pre-flight checks
    check_git_repo
    check_github_cli

    # Get current branch
    local current_branch=$(get_current_branch)

    if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
        print_error "Cannot mark main/master branch PR as ready"
        print_info "Please switch to your feature branch first"
        exit 1
    fi

    print_info "Current branch: $current_branch"

    # Check if PR exists and get status
    check_pr_exists "$current_branch"
    check_pr_status "$current_branch"

    # Show readiness checklist
    show_readiness_checklist

    # Confirm with user
    echo
    read -p "Are you ready to mark this PR for review? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_info "Operation cancelled. Continue development and run this script when ready."
        exit 0
    fi

    echo

    # Run pre-review checks
    run_pre_review_checks "$current_branch"

    # Convert to ready
    convert_to_ready "$current_branch"
}

# Run main function
main "$@"
