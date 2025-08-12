# Auth0 Authentication Troubleshooting Guide

This document provides comprehensive troubleshooting steps for Auth0 authentication issues encountered in the PMS application.

## Common Issues and Solutions

### 1. "Invalid state parameter" Error

**Symptoms:**
- Callback URL returns `{"detail":"Invalid state parameter"}`
- Auth0 redirects back but authentication fails
- 400 Bad Request on `/api/auth/callback`

**Root Cause:**
Missing or incorrect session configuration in the Kubernetes deployment, causing OAuth state parameter validation to fail.

**Solution:**
```bash
# Add missing environment variables to the deployment
kubectl patch deployment pms-backend -n pms --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/env/-",
    "value": {
      "name": "SESSION_SECRET_KEY",
      "value": "your-secure-session-key-change-this-in-production-12345678901234567890"
    }
  },
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/env/-",
    "value": {
      "name": "REDIRECT_URI",
      "value": "http://localhost:8000/api/auth/callback"
    }
  }
]'

# Wait for deployment to roll out
kubectl rollout status deployment/pms-backend -n pms
```

**Required Environment Variables:**
- `SESSION_SECRET_KEY`: Secure key for session management
- `REDIRECT_URI`: Must match Auth0 application callback URL

### 2. "Service not found" Error from Auth0

**Symptoms:**
- `{"detail":"Authentication error: access_denied"}`
- Auth0 logs show "Service not found: [audience-value]"
- 400 Bad Request during callback processing

**Root Cause:**
Incorrect `AUTH0_AUDIENCE` configuration that doesn't match any API identifier in the Auth0 tenant.

**Solution Options:**

#### Option A: Use Auth0 Management API (Recommended)
```bash
# Update to use Auth0 Management API audience
kubectl patch deployment pms-backend -n pms --type='json' -p='[{
  "op": "replace",
  "path": "/spec/template/spec/containers/0/env/5/value",
  "value": "https://dev-6ye11er0fid77jn6.us.auth0.com/api/v2/"
}]'
```

#### Option B: Create Custom API in Auth0
1. Go to Auth0 Dashboard > Applications > APIs
2. Click "Create API"
3. Set Name: "PMS Backend API"
4. Set Identifier: `https://pms-api` (must match AUTH0_AUDIENCE)
5. Update deployment with custom audience:
```bash
kubectl patch deployment pms-backend -n pms --type='json' -p='[{
  "op": "replace",
  "path": "/spec/template/spec/containers/0/env/5/value",
  "value": "https://pms-api"
}]'
```

### 3. "Empty reply from server" Error

**Symptoms:**
- `curl: (52) Empty reply from server`
- Connection established but no response
- Port forwarding appears to be working

**Root Cause:**
Port forwarding connection lost due to pod restarts during deployment updates.

**Solution:**
```bash
# Check if port forwarding is still active
kubectl get pods -n pms

# Restart port forwarding
kubectl port-forward service/pms-backend 8000:8000 -n pms
```

### 4. Session Cookie Issues

**Symptoms:**
- State parameter validation fails intermittently
- Users can't maintain authentication state
- Session data not persisting between requests

**Root Cause:**
Missing or incorrect session middleware configuration.

**Verification:**
```bash
# Test session cookie creation
curl -v -c cookies.txt http://localhost:8000/api/auth/login

# Test callback with session cookie
curl -v -b cookies.txt "http://localhost:8000/api/auth/callback?code=test&state=[state-from-login]"
```

**Required Session Configuration:**
- Session middleware must be added in `main.py`
- `SESSION_SECRET_KEY` must be set and secure
- Session cookies should be httponly and samesite=lax

## Diagnostic Commands

### Check Current Environment Variables
```bash
# List all environment variables
kubectl get deployment pms-backend -n pms -o json | jq '.spec.template.spec.containers[0].env'

# Check specific Auth0 variables
kubectl get deployment pms-backend -n pms -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AUTH0_DOMAIN")].value}'
kubectl get deployment pms-backend -n pms -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AUTH0_AUDIENCE")].value}'
```

### Check Application Logs
```bash
# View recent logs
kubectl logs deployment/pms-backend -n pms --tail=20

# Follow logs in real-time
kubectl logs deployment/pms-backend -n pms -f

# Check for specific errors
kubectl logs deployment/pms-backend -n pms | grep -i "auth\|error\|state"
```

### Test Authentication Flow
```bash
# Test login endpoint
curl -v -c cookies.txt http://localhost:8000/api/auth/login

# Extract state parameter from Auth0 URL and test callback
# (Replace [state] with actual state from login response)
curl -v -b cookies.txt "http://localhost:8000/api/auth/callback?code=test&state=[state]"
```

## Required Environment Variables Checklist

### Kubernetes Deployment Must Include:
- [ ] `DATABASE_URL`
- [ ] `REDIS_URL`
- [ ] `AUTH0_DOMAIN`
- [ ] `AUTH0_CLIENT_ID`
- [ ] `AUTH0_CLIENT_SECRET`
- [ ] `AUTH0_AUDIENCE`
- [ ] `SESSION_SECRET_KEY`
- [ ] `REDIRECT_URI`

### Auth0 Dashboard Configuration:
- [ ] Application created with correct type (Regular Web Application)
- [ ] Callback URLs configured: `http://localhost:8000/api/auth/callback`
- [ ] Logout URLs configured: `http://localhost:3000`
- [ ] API created (if using custom audience)
- [ ] API identifier matches `AUTH0_AUDIENCE` value

## Prevention Best Practices

1. **Always set SESSION_SECRET_KEY**: Never rely on default session keys in any environment
2. **Verify Auth0 configuration**: Ensure all URLs and identifiers match between code and Auth0 dashboard
3. **Test after deployments**: Always verify authentication flow after Kubernetes deployments
4. **Monitor logs**: Set up alerts for authentication errors
5. **Use environment-specific configurations**: Different Auth0 tenants for dev/staging/prod

## Related Files

- `/apps/backend/routers/auth_router.py` - Main authentication router
- `/apps/backend/config/auth_config.py` - Auth0 configuration
- `/apps/backend/middleware/session_middleware.py` - Session management
- `/apps/backend/main.py` - Application setup and middleware registration
- `/apps/backend/AUTH0_INTEGRATION_README.md` - Auth0 setup guide

## Troubleshooting Workflow

1. **Check logs first**: Look for specific error messages
2. **Verify environment variables**: Ensure all required variables are set
3. **Test authentication flow**: Use curl to isolate issues
4. **Check Auth0 dashboard**: Verify application and API configuration
5. **Restart services**: Sometimes a clean restart resolves transient issues
6. **Update documentation**: Add new issues and solutions to this guide

---

*Last updated: August 2025*
*For additional support, check the Auth0 documentation or contact the development team.*