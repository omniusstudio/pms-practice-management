# Auth0 Quick Reference Card

## Emergency Fixes

### "Invalid state parameter" - Quick Fix
```bash
kubectl patch deployment pms-backend -n pms --type='json' -p='[
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"SESSION_SECRET_KEY","value":"your-secure-session-key-change-this-in-production-12345678901234567890"}},
  {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"REDIRECT_URI","value":"http://localhost:8000/api/auth/callback"}}
]'
```

### "Service not found" - Quick Fix
```bash
# Use Auth0 Management API
kubectl patch deployment pms-backend -n pms --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/env/5/value","value":"https://dev-6ye11er0fid77jn6.us.auth0.com/api/v2/"}]'
```

### "Empty reply from server" - Quick Fix
```bash
# Restart port forwarding
kubectl port-forward service/pms-backend 8000:8000 -n pms
```

## Essential Environment Variables
```bash
AUTH0_DOMAIN=dev-6ye11er0fid77jn6.us.auth0.com
AUTH0_CLIENT_ID=[your-client-id]
AUTH0_CLIENT_SECRET=[your-client-secret]
AUTH0_AUDIENCE=https://dev-6ye11er0fid77jn6.us.auth0.com/api/v2/
SESSION_SECRET_KEY=[secure-random-key]
REDIRECT_URI=http://localhost:8000/api/auth/callback
```

## Quick Diagnostics
```bash
# Check logs
kubectl logs deployment/pms-backend -n pms --tail=10

# Test auth flow
curl -v http://localhost:8000/api/auth/login

# Check env vars
kubectl get deployment pms-backend -n pms -o json | jq '.spec.template.spec.containers[0].env'
```

## Common Error Messages
- `Invalid state parameter` → Missing SESSION_SECRET_KEY
- `Service not found` → Wrong AUTH0_AUDIENCE
- `Empty reply from server` → Port forwarding lost
- `access_denied` → Auth0 configuration mismatch

---
*For detailed troubleshooting, see: auth0-authentication-troubleshooting.md*