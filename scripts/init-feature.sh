#!/bin/bash

# Feature Branch Initialization Script for HIPAA-compliant Mental Health PMS
# Creates a feature branch, ensures proper naming conventions, and sets up tracking

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
readonly REQUIRED_PREFIX="feature/"
readonly PROTECTED_BRANCHES=("main" "master" "develop" "staging" "production" "release")
readonly MAX_BRANCH_NAME_LENGTH=80

# Function to validate branch name
validate_branch_name() {
    local branch_name="$1"

    # Check if branch name starts with required prefix
    if [[ ! "$branch_name" =~ ^${REQUIRED_PREFIX} ]]; then
        log_error "Branch name must start with '${REQUIRED_PREFIX}'"
        return 1
    fi

    # Check length
    if (( ${#branch_name} > MAX_BRANCH_NAME_LENGTH )); then
        log_error "Branch name too long (${#branch_name} chars). Maximum: ${MAX_BRANCH_NAME_LENGTH}"
        return 1
    fi

    # Check for invalid characters (only allow alphanumeric, hyphens, underscores, slashes)
    if [[ ! "$branch_name" =~ ^[a-zA-Z0-9/_-]+$ ]]; then
        log_error "Branch name contains invalid characters. Only alphanumeric, hyphens, underscores, and slashes allowed."
        return 1
    fi

    # Check for consecutive special characters
    if [[ "$branch_name" =~ [-_/]{2,} ]]; then
        log_error "Branch name cannot contain consecutive special characters"
        return 1
    fi

    # Check it doesn't end with special characters
    if [[ "$branch_name" =~ [-_/]$ ]]; then
        log_error "Branch name cannot end with special characters"
        return 1
    fi

    return 0
}

# Function to check if branch is protected
is_protected_branch() {
    local branch_name="$1"
    for protected in "${PROTECTED_BRANCHES[@]}"; do
        if [[ "$branch_name" == "$protected" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to ensure we're on main branch
ensure_on_main() {
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    if [[ "$current_branch" != "main" ]]; then
        log_warning "Not on main branch (currently on: $current_branch)"
        read -p "Switch to main branch? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Switching to main branch..."
            git checkout main
        else
            log_error "Aborting. Please switch to main branch manually."
            exit 1
        fi
    fi
}

# Function to update main branch
update_main() {
    log_info "Updating main branch..."
    if ! git fetch origin main; then
        log_error "Failed to fetch main branch"
        exit 1
    fi

    if ! git rebase origin/main; then
        log_error "Failed to rebase main branch"
        exit 1
    fi

    log_success "Main branch updated successfully"
}

# Function to create feature branch
create_feature_branch() {
    local branch_name="$1"

    # Check if branch already exists locally
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        log_error "Branch '$branch_name' already exists locally"
        exit 1
    fi

    # Check if branch exists on remote
    if git ls-remote --exit-code origin "$branch_name" >/dev/null 2>&1; then
        log_warning "Branch '$branch_name' exists on remote"
        read -p "Check out existing remote branch? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git checkout -b "$branch_name" "origin/$branch_name"
            log_success "Checked out existing remote branch: $branch_name"
            return
        else
            log_error "Aborting to avoid conflicts"
            exit 1
        fi
    fi

    # Create new branch
    if ! git checkout -b "$branch_name"; then
        log_error "Failed to create branch: $branch_name"
        exit 1
    fi

    log_success "Created and switched to branch: $branch_name"
}

# Function to set up branch tracking
setup_tracking() {
    local branch_name="$1"

    log_info "Setting up remote tracking..."
    if ! git push -u origin "$branch_name"; then
        log_error "Failed to set up remote tracking"
        exit 1
    fi

    log_success "Remote tracking set up successfully"
}

# Function to display next steps
display_next_steps() {
    local branch_name="$1"

    cat << EOF

${GREEN}✅ Branch Setup Complete!${NC}

${BLUE}Branch:${NC} $branch_name
${BLUE}Remote:${NC} origin/$branch_name

${YELLOW}Next Steps:${NC}
1. Make your changes
2. Commit frequently with descriptive messages
3. Push changes: ${BLUE}git push${NC}
4. Create a Pull Request targeting ${BLUE}main${NC}

${YELLOW}Important Reminders:${NC}
• Follow HIPAA compliance guidelines
• Write comprehensive tests
• Update documentation as needed
• Run pre-commit hooks before pushing
• Ensure CI/CD passes before requesting review

${BLUE}Pull Request Process:${NC}
• Create PR with descriptive title and body
• Link to relevant issues/tickets
• Request review from team members
• Address feedback promptly
• Ensure all checks pass before merge

EOF
}

<<<<<<< HEAD
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
=======
# Function to display PR process reminder
>>>>>>> feat: implement comprehensive DevOps infrastructure and workflow automation
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
<<<<<<< HEAD
    echo "6. 📤 Push and create draft PR"
    echo "   • git push -u origin $branch_name"
    echo "   • Create draft PR through GitHub UI or CLI"
    echo "   • Convert to ready when development is complete"
=======
    echo "6. 📤 Push and create PR"
    echo "   • git push -u origin $branch_name"
    echo "   • Create PR through GitHub UI or CLI"
>>>>>>> feat: implement comprehensive DevOps infrastructure and workflow automation
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

<<<<<<< HEAD
    # Optional: Get ticket number
    echo
    read -p "Enter ticket/issue number (optional): " ticket_number

    echo
    print_info "Branch name: $branch_name"
    if [[ -n "$ticket_number" ]]; then
        print_info "Ticket number: #$ticket_number"
    fi
=======
    echo
    print_info "Branch name: $branch_name"
>>>>>>> feat: implement comprehensive DevOps infrastructure and workflow automation

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
<<<<<<< HEAD

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
=======
    show_pr_process_reminder "$branch_name"
>>>>>>> feat: implement comprehensive DevOps infrastructure and workflow automation
}

# Run main function
main "$@"
