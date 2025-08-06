# Terraform Docs Installation

## Issue
The `terraform-docs==0.16.0` package was incorrectly listed in `apps/infra/requirements.txt` as a Python package, but terraform-docs is actually a standalone binary tool.

## Solution
terraform-docs should be installed separately as a binary, not via pip.

## Installation Options

### macOS (Homebrew)
```bash
brew install terraform-docs
```

### Manual Installation
1. Download the appropriate binary from: https://github.com/terraform-docs/terraform-docs/releases
2. Place it in your $PATH

### Docker
```bash
docker run --rm --volume "$(pwd):/terraform-docs" -u $(id -u) quay.io/terraform-docs/terraform-docs:0.20.0 markdown /terraform-docs
```

## Reference
- Official Installation Guide: https://terraform-docs.io/user-guide/installation/