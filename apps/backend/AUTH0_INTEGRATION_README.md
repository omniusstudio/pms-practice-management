# Auth0 Integration for PMS Application

This document explains how to integrate Auth0 OIDC authentication with the PMS (Practice Management System) application.

## Overview

The Auth0 integration provides:
- HIPAA-compliant authentication using Auth0's healthcare-focused features
- OIDC (OpenID Connect) protocol implementation
- Session-based authentication for web applications
- JWT token verification for API access
- Audit logging for compliance requirements

## Setup Instructions

### 1. Auth0 Configuration

1. **Create Auth0 Application**:
   - Go to Auth0 Dashboard → Applications
   - Create a new "Regular Web Application"
   - Note down the Domain, Client ID, and Client Secret

2. **Configure Application Settings**:
   - **Allowed Callback URLs**: `http://localhost:8000/api/auth/callback`
   - **Allowed Logout URLs**: `http://localhost:3000`
   - **Allowed Web Origins**: `http://localhost:3000`
   - **Allowed Origins (CORS)**: `http://localhost:3000`

3. **Enable HIPAA Compliance** (if available in your Auth0 plan):
   - Go to Auth0 Dashboard → Security → Compliance
   - Enable HIPAA compliance features
   - Configure audit logging

### 2. Environment Variables

Create a `.env` file in the backend directory with the following variables:

```bash
# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your-client-id
AUTH0_CLIENT_SECRET=your-client-secret
AUTH0_AUDIENCE=https://your-api-identifier

# Application URLs
REDIRECT_URI=http://localhost:8000/api/auth/callback
LOGOUT_REDIRECT_URI=http://localhost:3000

# Session Configuration
SESSION_SECRET_KEY=your-secure-session-key-change-this
SESSION_MAX_AGE=3600

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# HIPAA Compliance
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_RETENTION_DAYS=2555

# Environment
ENVIRONMENT=development
```

### 3. Install Dependencies

The required dependencies are already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key dependencies for Auth0 integration:
- `PyJWT==2.8.0` - JWT token handling
- `requests==2.31.0` - HTTP requests to Auth0
- `python-jose[cryptography]==3.3.0` - JWT verification
- `authlib==1.2.1` - OAuth/OIDC client

### 4. Database Migration

The User model is defined in the auth router. To create the users table:

```bash
# Generate migration
alembic revision --autogenerate -m "Add users table for Auth0 integration"

# Apply migration
alembic upgrade head
```

## API Endpoints

The Auth0 integration provides the following endpoints:

### Authentication Endpoints

- **`GET /api/auth/login`** - Initiate Auth0 login
  - Query params: `next` (optional) - URL to redirect after login
  - Redirects to Auth0 authorization server

- **`GET /api/auth/callback`** - Auth0 callback handler
  - Handles the authorization code exchange
  - Creates/updates user in database
  - Establishes user session

- **`POST /api/auth/logout`** - Logout user
  - Clears session
  - Returns Auth0 logout URL

- **`GET /api/auth/user`** - Get current user info
  - Returns authenticated user details
  - Returns 401 if not authenticated

### Protected Route Example

```python
from fastapi import Depends
from routers.auth_router import require_auth

@app.get("/api/patients")
async def get_patients(
    current_user: dict = Depends(require_auth)
):
    # Access current_user data
    user_id = current_user["sub"]
    # Your protected logic here
    return {"patients": []}
```

## Frontend Integration

See `examples/auth0_frontend_integration.js` for a complete frontend integration example.

### Basic Usage

```javascript
// Initialize Auth0 client
const auth = new Auth0Client('http://localhost:8000/api');

// Check if user is authenticated
const user = await auth.getCurrentUser();
if (user) {
    console.log('Authenticated user:', user);
} else {
    // Redirect to login
    auth.login();
}

// Make authenticated API calls
const data = await auth.apiRequest('/patients');
```

### HTML Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>PMS Auth0 Integration</title>
</head>
<body>
    <div id="user-info"></div>
    <div id="authenticated-content" style="display: none;">
        <h2>Protected Content</h2>
        <p>This content is only visible to authenticated users.</p>
    </div>
    <button id="login-button" onclick="auth.login()">Login</button>
    
    <script src="auth0_frontend_integration.js"></script>
</body>
</html>
```

## Security Features

### HIPAA Compliance
- Audit logging of all authentication events
- Secure session management
- PHI data protection
- Access control and user management

### Security Best Practices
- CSRF protection using state parameter
- Secure session cookies
- JWT token verification
- HTTPS enforcement in production
- CORS configuration

## Configuration Files

### Key Files Created/Modified

1. **`config/auth_config.py`** - Auth0 configuration management
2. **`routers/auth_router.py`** - Authentication endpoints
3. **`middleware/session_middleware.py`** - Session management
4. **`main.py`** - Updated to include Auth0 router and middleware
5. **`requirements.txt`** - Updated with Auth0 dependencies

## Testing

### Manual Testing

1. Start the backend server:
   ```bash
   uvicorn main:app --reload
   ```

2. Visit `http://localhost:8000/api/auth/login`
3. Complete Auth0 login flow
4. Verify callback handling and session creation
5. Test protected endpoints

### Automated Testing

```python
# Example test
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_auth_login_redirect():
    response = client.get("/api/auth/login")
    assert response.status_code == 307  # Redirect
    assert "auth0.com" in response.headers["location"]

def test_protected_endpoint_requires_auth():
    response = client.get("/api/auth/user")
    assert response.status_code == 401
```

## Troubleshooting

### Common Issues

1. **"Invalid state parameter"**
   - Ensure session middleware is properly configured
   - Check session secret key

2. **"Token verification failed"**
   - Verify Auth0 domain and audience configuration
   - Check JWKS endpoint accessibility

3. **"CORS errors"**
   - Update CORS_ORIGINS environment variable
   - Verify Auth0 application CORS settings

4. **"Database connection errors"**
   - Ensure database is running
   - Run Alembic migrations

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export SQL_ECHO=true
```

## Production Deployment

### Environment Variables for Production

```bash
# Use production Auth0 tenant
AUTH0_DOMAIN=your-prod-tenant.auth0.com

# Use production URLs
REDIRECT_URI=https://your-domain.com/api/auth/callback
LOGOUT_REDIRECT_URI=https://your-domain.com
CORS_ORIGINS=https://your-domain.com

# Secure session configuration
SESSION_SECRET_KEY=your-very-secure-production-key
ENVIRONMENT=production

# Enable HTTPS
HTTPS_ONLY=true
```

### Security Checklist

- [ ] Use HTTPS in production
- [ ] Rotate session secret keys regularly
- [ ] Enable Auth0 anomaly detection
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerting
- [ ] Review audit logs regularly
- [ ] Implement proper error handling
- [ ] Use environment-specific Auth0 tenants

## Support

For issues related to:
- **Auth0 configuration**: Check Auth0 documentation and dashboard
- **PMS integration**: Review this README and code comments
- **HIPAA compliance**: Consult with your compliance team

## Next Steps

1. **Multi-factor Authentication**: Enable MFA in Auth0
2. **Role-based Access Control**: Implement user roles and permissions
3. **Single Sign-On**: Configure SSO with healthcare systems
4. **Advanced Security**: Implement device fingerprinting and risk assessment