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

# Function to create draft PR
create_draft_pr() {
    local branch_name="$1"
    local ticket_number="$2"

    print_info "Creating draft PR for branch '$branch_name'..."

    # Push the branch first
    if ! git push -u origin "$branch_name"; then
        print_error "Failed to push branch '$branch_name'"
        exit 1
    fi

    # Check if GitHub CLI is available
    if ! command -v gh &> /dev/null; then
        print_warning "GitHub CLI (gh) not found. Please install it to auto-create draft PRs."
        print_info "Manual PR creation URL: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//g' | sed 's/\.git$//')/pull/new/$branch_name"
        return 1
    fi

    # Create draft PR title and body
    local pr_title="[DRAFT] $branch_name"
    local pr_body="## 🚧 Work in Progress

This is a draft PR for ticket${ticket_number:+ #$ticket_number}.

### Changes
- [ ] TODO: Describe your changes here

### Testing
- [ ] TODO: Add testing details

### Checklist
- [ ] Code follows project standards
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Security review completed

---
**Note**: This PR will be marked as ready for review when development is complete."

    # Create the draft PR
    if gh pr create --draft --title "$pr_title" --body "$pr_body" --head "$branch_name" --base "main"; then
        print_success "Draft PR created successfully!"
        local pr_url=$(gh pr view --json url --jq '.url')
        print_info "PR URL: $pr_url"
    else
        print_error "Failed to create draft PR"
        print_info "You can create it manually at: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//g' | sed 's/\.git$//')/pull/new/$branch_name"
    fi
}

# Function to display draft PR reminder
show_draft_pr_reminder() {
    local branch_name="$1"

    echo
    echo -e "${GREEN}"
    echo "═══════════════════════════════════════════════════════════════"
    echo "🎉 Feature branch and draft PR created!"
    echo "═══════════════════════════════════════════════════════════════"
    echo -e "${NC}"

    print_info "Current branch: $(git branch --show-current)"
    echo

    print_warning "📋 DEVELOPMENT WORKFLOW"
    echo
    echo "Your draft PR is now ready for development:"
    echo
    echo "1. 💻 Develop your feature"
    echo "   • Make commits as you work"
    echo "   • Push changes regularly: git push"
    echo "   • Update PR description with progress"
    echo
    echo "2. 🧪 Test your code locally"
    echo "   • Run all tests: make test"
    echo "   • Verify functionality works as expected"
    echo
    echo "3. 🔒 Security check"
    echo "   • Remove any secrets, API keys, or sensitive data"
    echo "   • Review code for security vulnerabilities"
    echo
    echo "4. ✅ When ready for review"
    echo "   • Run: ./scripts/ready-for-review.sh"
    echo "   • Or manually convert draft to ready in GitHub"
    echo "   • Ensure all tests pass and CI is green"
    echo
    echo "5. 👥 Request reviews"
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

# Function to display PR process reminder (for manual PR creation)
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
    echo "6. 📤 Push and create draft PR"
    echo "   • git push -u origin $branch_name"
    echo "   • Create draft PR through GitHub UI or CLI"
    echo "   • Convert to ready when development is complete"
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

    # Optional: Get ticket number
    echo
    read -p "Enter ticket/issue number (optional): " ticket_number

    echo
    print_info "Branch name: $branch_name"
    if [[ -n "$ticket_number" ]]; then
        print_info "Ticket number: #$ticket_number"
    fi

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

    # Ask if user wants to create a draft PR
    echo
    read -p "Create a draft PR now? (Y/n): " create_pr
    if [[ "$create_pr" =~ ^[Nn]$ ]]; then
        print_info "Skipping draft PR creation"
        show_pr_process_reminder "$branch_name"
    else
        create_draft_pr "$branch_name" "$ticket_number"
        show_draft_pr_reminder "$branch_name"
    fi
}

# Run main function
main "$@"
