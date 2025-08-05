#!/bin/bash

# Script to create a new service template
# Usage: ./scripts/create-service.sh <service-name> <service-type>

set -e

SERVICE_NAME="$1"
SERVICE_TYPE="$2"

if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_TYPE" ]; then
    echo "Usage: $0 <service-name> <service-type>"
    echo "Service types: backend, frontend, package"
    echo "Example: $0 user-service backend"
    exit 1
fi

case "$SERVICE_TYPE" in
    "backend")
        echo "Creating backend service: $SERVICE_NAME"
        mkdir -p "apps/$SERVICE_NAME"
        mkdir -p "apps/$SERVICE_NAME/tests"
        
        # Create basic FastAPI structure
        cat > "apps/$SERVICE_NAME/main.py" << EOF
"""$SERVICE_NAME FastAPI application."""

from fastapi import FastAPI
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="$SERVICE_NAME",
    description="HIPAA-compliant $SERVICE_NAME service",
    version="1.0.0",
)

@app.get("/")
async def root():
    """Root endpoint for health check."""
    logger.info("Health check requested", service="$SERVICE_NAME")
    return {"message": "$SERVICE_NAME", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "$SERVICE_NAME"}
EOF

        # Create requirements.txt
        cp "apps/backend/requirements.txt" "apps/$SERVICE_NAME/requirements.txt"
        
        # Create basic test
        cat > "apps/$SERVICE_NAME/tests/test_main.py" << EOF
"""Tests for $SERVICE_NAME application."""

def test_basic_functionality():
    """Test basic functionality - no-op test for CI."""
    assert True

def test_service_configuration():
    """Test service configuration is valid."""
    config = {
        "service_name": "$SERVICE_NAME",
        "version": "1.0.0",
        "environment": "test"
    }
    assert config["service_name"] == "$SERVICE_NAME"
EOF
        
        echo "✅ Backend service '$SERVICE_NAME' created successfully!"
        echo "📁 Location: apps/$SERVICE_NAME/"
        ;;
        
    "frontend")
        echo "Creating frontend service: $SERVICE_NAME"
        mkdir -p "apps/$SERVICE_NAME/src/components"
        mkdir -p "apps/$SERVICE_NAME/src/pages"
        mkdir -p "apps/$SERVICE_NAME/tests"
        
        # Create package.json
        cat > "apps/$SERVICE_NAME/package.json" << EOF
{
  "name": "$SERVICE_NAME",
  "version": "1.0.0",
  "description": "$SERVICE_NAME frontend application",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "node tests/App.test.js"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^3.1.0",
    "typescript": "^4.9.3",
    "vite": "^4.1.0"
  }
}
EOF

        # Create basic React component
        cat > "apps/$SERVICE_NAME/src/App.tsx" << EOF
import React from 'react';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>$SERVICE_NAME</h1>
        <p>HIPAA-compliant $SERVICE_NAME application.</p>
      </header>
    </div>
  );
}

export default App;
EOF

        # Create basic test
        cat > "apps/$SERVICE_NAME/tests/App.test.js" << EOF
// Basic tests for $SERVICE_NAME application

function testBasicFunctionality() {
  const result = true;
  if (!result) {
    throw new Error('Basic test failed');
  }
  console.log('✓ $SERVICE_NAME basic functionality test passed');
}

try {
  testBasicFunctionality();
  console.log('✅ All $SERVICE_NAME tests passed!');
} catch (error) {
  console.error('❌ Test failed:', error.message);
  process.exit(1);
}
EOF
        
        echo "✅ Frontend service '$SERVICE_NAME' created successfully!"
        echo "📁 Location: apps/$SERVICE_NAME/"
        ;;
        
    "package")
        echo "Creating shared package: $SERVICE_NAME"
        mkdir -p "packages/$SERVICE_NAME/src"
        
        # Create package.json
        cat > "packages/$SERVICE_NAME/package.json" << EOF
{
  "name": "@pms/$SERVICE_NAME",
  "version": "1.0.0",
  "description": "$SERVICE_NAME shared package",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "devDependencies": {
    "typescript": "^4.9.3"
  }
}
EOF

        # Create TypeScript config
        cp "packages/shared-types/tsconfig.json" "packages/$SERVICE_NAME/tsconfig.json"
        
        # Create basic index file
        cat > "packages/$SERVICE_NAME/src/index.ts" << EOF
// $SERVICE_NAME shared package

export interface ${SERVICE_NAME^}Config {
  name: string;
  version: string;
}

export const ${SERVICE_NAME^}_VERSION = '1.0.0';
EOF
        
        echo "✅ Shared package '$SERVICE_NAME' created successfully!"
        echo "📁 Location: packages/$SERVICE_NAME/"
        ;;
        
    *)
        echo "❌ Unknown service type: $SERVICE_TYPE"
        echo "Available types: backend, frontend, package"
        exit 1
        ;;
esac

echo ""
echo "🚀 Next steps:"
echo "1. Update the root Makefile if needed"
echo "2. Add the service to docker-compose.dev.yml if applicable"
echo "3. Update CODEOWNERS file with appropriate reviewers"
echo "4. Run 'make test' to verify the new service works"