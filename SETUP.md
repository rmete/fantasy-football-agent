# Fantasy Football AI Manager - Quick Setup Guide

## Prerequisites

- Docker and Docker Compose installed
- API keys ready:
  - Anthropic API key (required) - Get from https://console.anthropic.com/
  - Sleeper username (required)
  - Tavily API key (optional) - For web search
  - Reddit API credentials (optional) - For sentiment analysis

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
# REQUIRED:
# - ANTHROPIC_API_KEY
# - SLEEPER_USERNAME
```

### 2. Start All Services

```bash
# Build and start all containers
docker-compose up -d

# Watch the logs
docker-compose logs -f
```

### 3. Verify Services

Once all containers are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. Check Health

```bash
# Test backend
curl http://localhost:8000/health

# Check all services
docker-compose ps
```

## Expected Output

You should see:
```
NAME                 COMMAND                  SERVICE    STATUS         PORTS
fantasy-backend      "uvicorn main:app..."    backend    Up             0.0.0.0:8000->8000/tcp
fantasy-frontend     "docker-entrypoint..."   frontend   Up             0.0.0.0:3000->3000/tcp
fantasy-postgres     "docker-entrypoint..."   postgres   Up (healthy)   0.0.0.0:5432->5432/tcp
fantasy-redis        "docker-entrypoint..."   redis      Up (healthy)   0.0.0.0:6379->6379/tcp
```

## Common Issues

### Port Already in Use
```bash
# Change ports in docker-compose.yml if needed
# For example, change "3000:3000" to "3001:3000"
```

### Backend Won't Start
```bash
# Check backend logs
docker logs fantasy-backend

# Common issue: Missing API key
# Make sure ANTHROPIC_API_KEY is set in .env
```

### Frontend Build Errors
```bash
# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears database)
docker-compose down -v
```

## Next Steps

Once all services are running:

1. Visit http://localhost:3000 to see the frontend
2. Check http://localhost:8000/docs to see API documentation
3. Follow the phase documentation to implement features:
   - Start with `docs/phase-2-backend-core.md` for Sleeper integration
   - Then proceed through phases 3-9

## Development Workflow

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker logs -f fantasy-backend
docker logs -f fantasy-frontend

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose build
docker-compose up -d

# Execute commands in containers
docker exec -it fantasy-backend python tests/test_sleeper.py
docker exec -it fantasy-postgres psql -U postgres -d fantasy_football
```

## Getting Help

- Check the main README.md for architecture overview
- Review phase documentation in `docs/` directory
- Check API docs at http://localhost:8000/docs
- View container logs for error messages

🚀 Ready to build your Fantasy Football AI Manager!
