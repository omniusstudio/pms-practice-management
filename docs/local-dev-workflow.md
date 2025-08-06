# Local Development Workflow

This guide covers the **Local Dev Loop: Update, Build, Redeploy** process for the PMS application running on Kubernetes.

## Quick Start

### 1. Initial Setup
```bash
# Ensure your application is deployed
kubectl apply -f k8s-simple.yaml

# Check status
./dev-helpers.sh status
```

### 2. Development Loop
```bash
# Full rebuild and redeploy (both frontend and backend)
./dev-loop.sh all

# Or rebuild specific components
./dev-loop.sh backend
./dev-loop.sh frontend
```

## Available Scripts

### `dev-loop.sh` - Main Development Loop
Automated script for the update, build, and redeploy cycle.

**Usage:**
```bash
./dev-loop.sh [backend|frontend|all]
```

**What it does:**
1. Builds Docker images with latest code changes
2. Restarts Kubernetes deployments
3. Waits for rollout completion
4. Shows deployment status
5. Runs health checks

### `dev-helpers.sh` - Development Utilities
Collection of helpful commands for development tasks.

**Available Commands:**
```bash
./dev-helpers.sh status                    # Show current deployment status
./dev-helpers.sh logs [component]          # Watch logs (default: backend)
./dev-helpers.sh shell [component]         # Open shell in pod (default: backend)
./dev-helpers.sh forward <component> [port] # Port-forward service
./dev-helpers.sh restart [component]       # Restart deployment
./dev-helpers.sh clean                     # Clean up and redeploy everything
./dev-helpers.sh test                      # Run development tests
./dev-helpers.sh help                      # Show help
```

## Common Development Workflows

### 1. Code Change → Test Cycle
```bash
# 1. Make code changes in apps/backend or apps/frontend
# 2. Run the dev loop
./dev-loop.sh all

# 3. Test your changes
open http://localhost:80  # Frontend
./dev-helpers.sh forward backend 8000  # Backend API
```

### 2. Debugging Issues
```bash
# Check pod status
./dev-helpers.sh status

# Watch logs
./dev-helpers.sh logs backend
./dev-helpers.sh logs frontend

# Shell into pod for debugging
./dev-helpers.sh shell backend
```

### 3. Database/Redis Access
```bash
# Access PostgreSQL
./dev-helpers.sh forward postgres 5432
psql -h localhost -p 5432 -U postgres -d pms

# Access Redis
./dev-helpers.sh forward redis 6379
redis-cli -h localhost -p 6379
```

### 4. Clean Restart
```bash
# When things get messy, clean restart
./dev-helpers.sh clean
```

## Application URLs

- **Frontend**: http://localhost:80 (LoadBalancer)
- **Backend API**: Port-forward required
  ```bash
  ./dev-helpers.sh forward backend 8000
  # Then access: http://localhost:8000
  ```

## Development Tips

### 1. Fast Iteration
- Use `./dev-loop.sh backend` or `./dev-loop.sh frontend` for single component updates
- Keep terminal windows open for logs: `./dev-helpers.sh logs backend`

### 2. Debugging
- Use `./dev-helpers.sh shell backend` to inspect the container environment
- Check pod events: `kubectl describe pod <pod-name> -n pms`
- View resource usage: `kubectl top pods -n pms`

### 3. Performance
- Docker builds are cached, so subsequent builds are faster
- Kubernetes rolling updates ensure zero downtime
- Use `kubectl rollout status` to monitor deployment progress

### 4. Troubleshooting

**Pods stuck in ImagePullBackOff:**
```bash
# Rebuild and restart
./dev-loop.sh all
```

**Services not accessible:**
```bash
# Check service status
./dev-helpers.sh status

# Test connectivity
./dev-helpers.sh test
```

**Database connection issues:**
```bash
# Check postgres pod
kubectl logs deployment/postgres -n pms

# Restart database
./dev-helpers.sh restart all
```

## File Structure

```
PMS/
├── apps/
│   ├── backend/          # Backend source code
│   └── frontend/         # Frontend source code
├── k8s-simple.yaml       # Kubernetes deployment config
├── dev-loop.sh           # Main development loop script
├── dev-helpers.sh        # Development utility commands
└── LOCAL-DEV-WORKFLOW.md # This documentation
```

## Environment Variables

The application uses the following key environment variables (configured in k8s-simple.yaml):

**Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `NODE_ENV`: Environment (development/production)

**Frontend:**
- `REACT_APP_API_URL`: Backend API URL
- `NODE_ENV`: Environment setting

## Next Steps

1. **CI/CD Integration**: Extend these scripts for automated testing
2. **Hot Reloading**: Implement file watching for automatic rebuilds
3. **Multi-Environment**: Adapt scripts for staging/production deployments
4. **Monitoring**: Add health checks and metrics collection

---

**Happy Coding! 🚀**

For questions or improvements to this workflow, please update this documentation.