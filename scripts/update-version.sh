#!/bin/bash

# Update version script for PMS
# Called by semantic-release to update version information across the codebase

set -e

VERSION="$1"

if [ -z "$VERSION" ]; then
    echo "❌ Error: Version parameter is required"
    echo "Usage: $0 <version>"
    exit 1
fi

echo "🔄 Updating version to: $VERSION"

# Create VERSION file
echo "$VERSION" > VERSION
echo "✅ Created VERSION file"

# Update backend version.json
BACKEND_VERSION_FILE="apps/backend/version.json"
if [ -f "$BACKEND_VERSION_FILE" ]; then
    # Update existing version.json
    cat > "$BACKEND_VERSION_FILE" << EOF
{
  "version": "$VERSION",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD)",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD)",
  "release_type": "semantic"
}
EOF
else
    # Create new version.json
    mkdir -p "$(dirname "$BACKEND_VERSION_FILE")"
    cat > "$BACKEND_VERSION_FILE" << EOF
{
  "version": "$VERSION",
  "build_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD)",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD)",
  "release_type": "semantic"
}
EOF
fi
echo "✅ Updated backend version.json"

# Update frontend package.json
FRONTEND_PACKAGE_JSON="apps/frontend/package.json"
if [ -f "$FRONTEND_PACKAGE_JSON" ]; then
    # Use jq to update version if available, otherwise use sed
    if command -v jq >/dev/null 2>&1; then
        jq ".version = \"$VERSION\"" "$FRONTEND_PACKAGE_JSON" > "${FRONTEND_PACKAGE_JSON}.tmp" && \
        mv "${FRONTEND_PACKAGE_JSON}.tmp" "$FRONTEND_PACKAGE_JSON"
    else
        # Fallback to sed for basic version update
        sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/g" "$FRONTEND_PACKAGE_JSON" && \
        rm "${FRONTEND_PACKAGE_JSON}.bak"
    fi
    echo "✅ Updated frontend package.json"
else
    echo "⚠️  Frontend package.json not found, skipping"
fi

# Update root package.json if it exists
ROOT_PACKAGE_JSON="package.json"
if [ -f "$ROOT_PACKAGE_JSON" ]; then
    if command -v jq >/dev/null 2>&1; then
        jq ".version = \"$VERSION\"" "$ROOT_PACKAGE_JSON" > "${ROOT_PACKAGE_JSON}.tmp" && \
        mv "${ROOT_PACKAGE_JSON}.tmp" "$ROOT_PACKAGE_JSON"
    else
        sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/g" "$ROOT_PACKAGE_JSON" && \
        rm "${ROOT_PACKAGE_JSON}.bak"
    fi
    echo "✅ Updated root package.json"
fi

# Update Python package version if setup.py or pyproject.toml exists
if [ -f "setup.py" ]; then
    sed -i.bak "s/version=['\"][^'\"]*['\"]/version='$VERSION'/g" setup.py && rm setup.py.bak
    echo "✅ Updated setup.py"
fi

if [ -f "pyproject.toml" ]; then
    sed -i.bak "s/version = ['\"][^'\"]*['\"]/version = \"$VERSION\"/g" pyproject.toml && rm pyproject.toml.bak
    echo "✅ Updated pyproject.toml"
fi

# Update Docker compose files with new version
for compose_file in docker-compose*.yml; do
    if [ -f "$compose_file" ]; then
        # Update image tags that use version placeholders
        sed -i.bak "s/:latest/:$VERSION/g; s/:v[0-9]\+\.[0-9]\+\.[0-9]\+/:v$VERSION/g" "$compose_file" && \
        rm "${compose_file}.bak"
        echo "✅ Updated $compose_file"
    fi
done

# Update Kubernetes manifests if they exist
if [ -d "k8s" ] || [ -d "kubernetes" ]; then
    for k8s_dir in k8s kubernetes; do
        if [ -d "$k8s_dir" ]; then
            find "$k8s_dir" -name "*.yaml" -o -name "*.yml" | while read -r file; do
                if grep -q "image:" "$file"; then
                    sed -i.bak "s/:latest/:$VERSION/g; s/:v[0-9]\+\.[0-9]\+\.[0-9]\+/:v$VERSION/g" "$file" && \
                    rm "${file}.bak"
                    echo "✅ Updated $file"
                fi
            done
        fi
    done
fi

# Update Helm charts if they exist
if [ -f "charts/pms/Chart.yaml" ]; then
    sed -i.bak "s/version: [0-9]\+\.[0-9]\+\.[0-9]\+/version: $VERSION/g; s/appVersion: [0-9]\+\.[0-9]\+\.[0-9]\+/appVersion: $VERSION/g" "charts/pms/Chart.yaml" && \
    rm "charts/pms/Chart.yaml.bak"
    echo "✅ Updated Helm chart"
fi

# Create release artifacts
mkdir -p release-artifacts

# Create version info artifact
cat > "release-artifacts/version-info.json" << EOF
{
  "version": "$VERSION",
  "release_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "git_commit": "$(git rev-parse HEAD)",
  "git_branch": "$(git rev-parse --abbrev-ref HEAD)",
  "build_number": "${GITHUB_RUN_NUMBER:-local}",
  "release_type": "semantic",
  "components": {
    "backend": {
      "version": "$VERSION",
      "python_version": "$(python3 --version 2>/dev/null || echo 'Unknown')"
    },
    "frontend": {
      "version": "$VERSION",
      "node_version": "$(node --version 2>/dev/null || echo 'Unknown')"
    }
  }
}
EOF

echo "✅ Created release artifacts"
echo "🎉 Version update completed successfully: $VERSION"

# Validate the update
echo "📋 Version update summary:"
echo "  - VERSION file: $(cat VERSION)"
if [ -f "$BACKEND_VERSION_FILE" ]; then
    echo "  - Backend version: $(grep '"version"' "$BACKEND_VERSION_FILE" | cut -d'"' -f4)"
fi
if [ -f "$FRONTEND_PACKAGE_JSON" ]; then
    echo "  - Frontend version: $(grep '"version"' "$FRONTEND_PACKAGE_JSON" | head -1 | cut -d'"' -f4)"
fi

echo "✅ All version updates completed successfully!"
