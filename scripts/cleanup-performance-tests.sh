#!/bin/bash

# Performance Tests Cleanup Script
# This script optimizes the performance test dependencies and removes unnecessary packages

set -e

echo "🧹 Starting performance tests cleanup..."

# Navigate to performance tests directory
cd "$(dirname "$0")/../tests/performance"

# Backup current package.json
cp package.json package.json.backup
echo "📦 Backed up package.json"

# Remove node_modules to start fresh
echo "🗑️  Removing existing node_modules..."
rm -rf node_modules/

# Clean npm cache
echo "🧽 Cleaning npm cache..."
npm cache clean --force

# Install only production dependencies first
echo "📥 Installing production dependencies..."
npm install --production

# Check the size after cleanup
echo "📊 Checking new size..."
du -sh node_modules/ || echo "node_modules directory not found"

# Install dev dependencies if needed
read -p "Install dev dependencies? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📥 Installing dev dependencies..."
    npm install
fi

# Final size check
echo "📊 Final size check..."
du -sh node_modules/ || echo "node_modules directory not found"

echo "✅ Performance tests cleanup completed!"
echo "💾 Original package.json backed up as package.json.backup"
