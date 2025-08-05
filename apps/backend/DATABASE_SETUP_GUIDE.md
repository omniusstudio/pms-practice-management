# Database Setup Guide for PMS Application

## Current Status

The application is configured to use PostgreSQL but the server at `localhost:8080` is not accessible. This guide provides multiple setup options.

## Option 1: PostgreSQL Setup (Recommended for Production)

### Prerequisites
- PostgreSQL server running and accessible
- Admin credentials for database creation

### Manual Setup Steps

1. **Connect to PostgreSQL server:**
   ```bash
   # If you have psql installed
   psql -h localhost -p 8080 -U postgres
   
   # Or use any PostgreSQL client
   ```

2. **Create database and user:**
   ```sql
   -- Create user
   CREATE USER pms_user WITH PASSWORD 'pms_password';
   
   -- Create database
   CREATE DATABASE pms_dev OWNER pms_user;
   
   -- Grant permissions
   GRANT ALL PRIVILEGES ON DATABASE pms_dev TO pms_user;
   ```

3. **Run initialization script:**
   ```bash
   # From the backend directory
   cd /Volumes/external\ storage\ /PMS/apps/backend
   
   # Execute the init script
   psql -h localhost -p 8080 -U pms_user -d pms_dev -f ../../scripts/db/init.sql
   ```

4. **Run Alembic migrations:**
   ```bash
   # From the backend directory
   alembic upgrade head
   ```

### Automated Setup (when server is accessible)

Run the provided setup script:
```bash
cd /Volumes/external\ storage\ /PMS/apps/backend
python3 setup_database.py
```

## Option 2: Docker PostgreSQL Setup

If you need to set up PostgreSQL using Docker:

```bash
# Run PostgreSQL in Docker
docker run --name pms-postgres \
  -e POSTGRES_DB=pms_dev \
  -e POSTGRES_USER=pms_user \
  -e POSTGRES_PASSWORD=pms_password \
  -p 8080:5432 \
  -d postgres:15

# Wait for container to start, then run migrations
sleep 10
cd /Volumes/external\ storage\ /PMS/apps/backend
alembic upgrade head
```

## Option 3: SQLite Development Setup (Current Fallback)

The application currently uses SQLite for development when PostgreSQL is unavailable:

- **Database file:** `demo.db` in the backend directory
- **Configuration:** Automatically used when PostgreSQL connection fails
- **Limitations:** Single-user, no advanced PostgreSQL features

### SQLite Setup Commands
```bash
cd /Volumes/external\ storage\ /PMS/apps/backend

# Create tables using the demo database setup
python3 -c "from demo_database import create_tables_sync; create_tables_sync()"

# Or run migrations (will use SQLite URL)
DATABASE_URL=sqlite:///demo.db alembic upgrade head
```

## Configuration Files Updated

The following files have been configured for PostgreSQL on port 8080:

1. **`database.py`** - Updated connection string to `localhost:8080`
2. **`alembic.ini`** - Updated sqlalchemy.url to use port 8080
3. **Dependencies installed:**
   - `psycopg2-binary` - PostgreSQL adapter
   - `asyncpg` - Async PostgreSQL adapter
   - `types-psycopg2` - Type stubs

## Environment Variables

You can override database settings using environment variables:

```bash
export DATABASE_URL="postgresql://pms_user:pms_password@localhost:8080/pms_dev"
export ASYNC_DATABASE_URL="postgresql+asyncpg://pms_user:pms_password@localhost:8080/pms_dev"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="your_admin_password"
```

## Troubleshooting

### Connection Issues
- Verify PostgreSQL server is running on port 8080
- Check firewall settings
- Verify credentials
- Test connection: `telnet localhost 8080`

### Migration Issues
- Ensure database exists before running migrations
- Check Alembic configuration in `alembic.ini`
- Verify user has necessary permissions

### Current Application Status
- ✅ Backend server running (using SQLite fallback)
- ✅ Frontend server running
- ✅ All tests passing
- ⚠️ PostgreSQL connection pending server setup

## Next Steps

1. **Immediate:** Application works with SQLite for development
2. **Short-term:** Set up PostgreSQL server properly
3. **Production:** Use managed PostgreSQL service

The application is fully functional with the current SQLite setup for development and testing purposes.