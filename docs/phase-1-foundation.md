# Phase 1: Project Foundation & Setup

**Goal**: Establish the basic infrastructure and ensure all services can run locally

**Estimated Time**: 4-6 hours

**Dependencies**: None (starting point)

## Overview

This phase sets up the foundational structure for the entire application. By the end, you'll have:
- Complete directory structure
- Docker Compose environment with PostgreSQL and Redis
- Basic FastAPI server running
- Basic Next.js frontend running
- All services communicating correctly

## Tasks Breakdown

### Task 1.1: Create Project Directory Structure

Create the following folder structure:

```
fantasy-football-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   └── __init__.py
│   │   ├── agents/
│   │   │   └── __init__.py
│   │   ├── tools/
│   │   │   └── __init__.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       └── database.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── shared/
│   └── schemas/
│
├── docs/
│   └── (phase documentation files)
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

### Task 1.2: Backend Setup - FastAPI Boilerplate

#### requirements.txt
```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
sqlalchemy==2.0.25
alembic==1.13.1
asyncpg==0.29.0
redis==5.0.1
celery==5.3.6
python-dotenv==1.0.0

# LangGraph & AI
langgraph==0.0.20
langchain==0.1.0
langchain-anthropic==0.1.1
anthropic==0.8.1

# HTTP Clients
httpx==0.26.0
aiohttp==3.9.1

# Data Scraping/APIs
praw==7.7.1
beautifulsoup4==4.12.3
lxml==5.1.0

# Utilities
python-multipart==0.0.6
websockets==12.0
```

#### backend/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### backend/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="Fantasy Football AI Manager API",
    description="AI-powered fantasy football team management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Fantasy Football AI Manager API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### backend/app/core/config.py
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Fantasy Football AI Manager"

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "fantasy_football"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # AI/LLM
    ANTHROPIC_API_KEY: Optional[str] = None

    # Sleeper
    SLEEPER_BASE_URL: str = "https://api.sleeper.app/v1"
    SLEEPER_USERNAME: Optional[str] = None

    # External APIs (optional)
    TAVILY_API_KEY: Optional[str] = None
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### Task 1.3: Frontend Setup - Next.js 14

#### Initialize Next.js
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
```

#### frontend/package.json (additional dependencies)
```json
{
  "dependencies": {
    "@tanstack/react-query": "^5.17.19",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-tabs": "^1.0.4",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "recharts": "^2.10.3",
    "tailwind-merge": "^2.2.0",
    "date-fns": "^3.0.6",
    "lucide-react": "^0.307.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3"
  }
}
```

#### frontend/Dockerfile
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Run development server
CMD ["npm", "run", "dev"]
```

#### frontend/next.config.js
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/:path*',
      },
    ]
  },
}

module.exports = nextConfig
```

#### frontend/lib/api-client.ts
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchAPI(endpoint: string, options?: RequestInit) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }

  return response.json();
}
```

#### frontend/app/page.tsx
```typescript
export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">
        Fantasy Football AI Manager
      </h1>
      <p className="text-xl text-gray-600">
        Your intelligent assistant for dominating your league
      </p>
    </main>
  );
}
```

### Task 1.4: Docker Compose Configuration

#### docker-compose.yml
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: fantasy-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fantasy_football
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: fantasy-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    container_name: fantasy-backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    container_name: fantasy-frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### Task 1.5: Environment Configuration

#### .env.example
```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fantasy_football
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# AI/LLM (REQUIRED)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Sleeper (REQUIRED)
SLEEPER_USERNAME=your_sleeper_username

# Optional External APIs
TAVILY_API_KEY=your_tavily_api_key_here
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=FantasyFootballAI/1.0

# Application
DEBUG=True
LOG_LEVEL=INFO
```

### Task 1.6: Git Configuration

#### .gitignore
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv/
*.egg-info/

# Node
node_modules/
.next/
out/
build/
dist/
*.log

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
*.log

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db
```

## Success Criteria

After completing Phase 1, you should be able to:

1. ✅ Run `docker-compose up -d` without errors
2. ✅ Access backend at http://localhost:8000 and see API welcome message
3. ✅ Access backend docs at http://localhost:8000/docs
4. ✅ Access frontend at http://localhost:3000
5. ✅ PostgreSQL accessible at localhost:5432
6. ✅ Redis accessible at localhost:6379
7. ✅ Backend can import core modules without errors
8. ✅ Frontend can build and run development server

## Verification Commands

```bash
# Check all services are running
docker-compose ps

# Test backend
curl http://localhost:8000/health

# Test PostgreSQL
docker exec -it fantasy-postgres psql -U postgres -c "SELECT version();"

# Test Redis
docker exec -it fantasy-redis redis-cli ping

# Check backend logs
docker logs fantasy-backend

# Check frontend logs
docker logs fantasy-frontend
```

## Common Issues & Solutions

### Issue: Port already in use
**Solution**: Change ports in docker-compose.yml or stop conflicting services

### Issue: Docker build fails for backend
**Solution**: Ensure Python requirements are valid, check Dockerfile syntax

### Issue: Frontend can't connect to backend
**Solution**: Verify CORS settings in backend and proxy config in Next.js

### Issue: Database connection fails
**Solution**: Ensure postgres service is healthy before backend starts (use depends_on with healthcheck)

## Next Steps

Once all services are running successfully, proceed to:
- **[Phase 2: Backend Core](./phase-2-backend-core.md)** - Build Sleeper API integration

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
