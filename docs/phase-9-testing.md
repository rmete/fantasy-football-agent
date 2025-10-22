# Phase 9: Testing & Polish

**Goal**: Comprehensive testing, bug fixes, and final polish

**Estimated Time**: 6-8 hours

**Dependencies**: Phases 1-8

## Overview

Final phase to ensure production readiness:
- End-to-end testing with real data
- Error handling and edge cases
- Performance optimization
- UI/UX improvements
- Documentation
- Deployment preparation

## Tasks Breakdown

### Task 9.1: Comprehensive Backend Testing

#### backend/tests/test_end_to_end.py

```python
import asyncio
import pytest
from app.core.database import AsyncSessionLocal, init_db
from app.agents.orchestrator import orchestrator
from app.tools.sleeper_client import sleeper_client
from app.core.config import settings

@pytest.mark.asyncio
async def test_sit_start_workflow():
    """Test complete sit/start workflow"""

    if not settings.SLEEPER_USERNAME:
        pytest.skip("SLEEPER_USERNAME not configured")

    # Get user
    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    assert user is not None

    # Get leagues
    leagues = await sleeper_client.get_user_leagues(user["user_id"], "nfl", "2024")
    assert len(leagues) > 0

    league_id = leagues[0]["league_id"]

    # Get rosters
    rosters = await sleeper_client.get_league_rosters(league_id)
    assert len(rosters) > 0

    # Run sit/start analysis
    initial_state = {
        "user_id": "test_user",
        "league_id": league_id,
        "roster_id": 1,
        "task_type": "sit_start",
        "task_id": "test_123",
        "week": 1
    }

    result = await orchestrator.run(initial_state)

    # Verify results
    assert result["current_step"] == "completed"
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0

    print(f"✅ Sit/Start test passed! Found {len(result['recommendations'])} recommendations")

@pytest.mark.asyncio
async def test_trade_analysis_workflow():
    """Test trade analysis workflow"""

    if not settings.SLEEPER_USERNAME:
        pytest.skip("SLEEPER_USERNAME not configured")

    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    leagues = await sleeper_client.get_user_leagues(user["user_id"], "nfl", "2024")
    league_id = leagues[0]["league_id"]

    # Test trade analysis
    initial_state = {
        "user_id": "test_user",
        "league_id": league_id,
        "roster_id": 1,
        "task_type": "trade_analysis",
        "task_id": "test_456",
        "input_data": {
            "my_players": ["player_id_1"],
            "their_players": ["player_id_2"]
        }
    }

    result = await orchestrator.run(initial_state)

    assert result["current_step"] == "completed"
    print("✅ Trade analysis test passed!")

@pytest.mark.asyncio
async def test_database_operations():
    """Test database CRUD operations"""

    await init_db()

    async with AsyncSessionLocal() as session:
        from app.crud.user import create_user, get_user_by_sleeper_id

        # Create user
        user = await create_user(
            session,
            sleeper_user_id="test123",
            sleeper_username="testuser",
            display_name="Test User"
        )

        assert user is not None
        assert user.sleeper_user_id == "test123"

        # Retrieve user
        retrieved = await get_user_by_sleeper_id(session, "test123")
        assert retrieved.id == user.id

    print("✅ Database tests passed!")

@pytest.mark.asyncio
async def test_agent_tools():
    """Test individual agent tools"""

    from app.tools import (
        web_search_tool,
        reddit_tool,
        projection_tool,
        injury_tool
    )

    # Test web search
    news = await web_search_tool.search_player_news("Patrick Mahomes")
    print(f"Web search: {len(news)} results")

    # Test Reddit sentiment
    sentiment = await reddit_tool.get_player_sentiment("Christian McCaffrey")
    print(f"Reddit sentiment: {sentiment['sentiment_score']}")

    # Test projections
    projection = await projection_tool.get_player_projection("Josh Allen", "QB")
    print(f"Projection: {projection['projected_points']} points")

    # Test injury monitor
    injury = await injury_tool.check_player_injury_status("4881", "Justin Jefferson")
    print(f"Injury status: {injury['injury_status']}")

    print("✅ Agent tools tests passed!")

def run_all_tests():
    """Run all tests"""
    asyncio.run(test_sit_start_workflow())
    asyncio.run(test_trade_analysis_workflow())
    asyncio.run(test_database_operations())
    asyncio.run(test_agent_tools())

if __name__ == "__main__":
    run_all_tests()
```

### Task 9.2: Frontend Testing

#### frontend/__tests__/components.test.tsx

```typescript
import { render, screen } from '@testing-library/react';
import { PlayerCard } from '@/components/player-card';
import { RecommendationCard } from '@/components/recommendation-card';

describe('PlayerCard', () => {
  it('renders player information', () => {
    const player = {
      player_id: '1',
      full_name: 'Patrick Mahomes',
      position: 'QB',
      team: 'KC',
    };

    render(<PlayerCard player={player} />);

    expect(screen.getByText('Patrick Mahomes')).toBeInTheDocument();
    expect(screen.getByText('QB')).toBeInTheDocument();
    expect(screen.getByText('KC')).toBeInTheDocument();
  });
});

describe('RecommendationCard', () => {
  it('renders recommendation with confidence', () => {
    const recommendation = {
      player_id: '1',
      player_name: 'Josh Allen',
      position: 'QB',
      recommendation: 'START',
      confidence: 85,
      reasoning: 'Great matchup this week',
      supporting_data: {
        projection: 22.5,
        matchup_rating: 8.5,
        injury_status: 'Healthy',
        sentiment_score: 0.7,
      },
    };

    render(<RecommendationCard recommendation={recommendation} />);

    expect(screen.getByText('Josh Allen')).toBeInTheDocument();
    expect(screen.getByText('START')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });
});
```

### Task 9.3: Error Handling

#### backend/app/core/error_handlers.py

```python
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app: FastAPI):
    """Register global error handlers"""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger.error(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation Error",
                "detail": exc.errors(),
                "body": exc.body
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors"""
        logger.error(f"Database error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database Error",
                "detail": "An error occurred while accessing the database"
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "detail": str(exc) if app.debug else "An unexpected error occurred"
            }
        )
```

Add to `main.py`:
```python
from app.core.error_handlers import register_error_handlers

register_error_handlers(app)
```

### Task 9.4: Performance Optimization

#### backend/app/core/cache_decorator.py

```python
from functools import wraps
from app.core.redis_client import redis_cache
import hashlib
import json

def cached(expire: int = 3600):
    """Decorator to cache function results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": str(kwargs)
            }
            key_string = json.dumps(key_data, sort_keys=True)
            cache_key = f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"

            # Try to get from cache
            cached_result = await redis_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await redis_cache.set(cache_key, result, expire=expire)

            return result

        return wrapper
    return decorator
```

Usage example:
```python
from app.core.cache_decorator import cached

@cached(expire=7200)  # Cache for 2 hours
async def get_player_projections(player_id: str, week: int):
    # Expensive operation
    return await fetch_projections(player_id, week)
```

### Task 9.5: Rate Limiting

#### backend/app/middleware/rate_limit.py

```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.redis_client import redis_cache
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host

        # Check rate limit
        key = f"rate_limit:{client_ip}"

        if await redis_cache.redis:
            current_count = await redis_cache.redis.get(key)

            if current_count and int(current_count) >= self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )

            # Increment counter
            if current_count:
                await redis_cache.redis.incr(key)
            else:
                await redis_cache.redis.setex(key, 60, 1)

        response = await call_next(request)
        return response
```

Add to `main.py`:
```python
from app.middleware.rate_limit import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
```

### Task 9.6: UI/UX Polish

#### frontend/components/loading-skeleton.tsx

```typescript
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

export function DashboardSkeleton() {
  return (
    <div className="container mx-auto p-6">
      <Skeleton className="h-12 w-64 mb-8" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-24 mt-2" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function RecommendationSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-24 mt-2" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-20 w-full" />
      </CardContent>
    </Card>
  );
}
```

#### frontend/components/error-boundary.tsx

```typescript
'use client';

import { Component, ReactNode } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container mx-auto p-6 flex items-center justify-center min-h-screen">
          <Card className="max-w-md">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertCircle className="h-6 w-6 text-destructive" />
                <CardTitle>Something went wrong</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
              <Button
                onClick={() => this.setState({ hasError: false })}
                className="w-full"
              >
                Try Again
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Task 9.7: Environment Variable Validation

#### backend/app/core/config.py (updated)

```python
from pydantic_settings import BaseSettings
from typing import Optional
import sys

class Settings(BaseSettings):
    # ... existing settings ...

    def validate_required_settings(self):
        """Validate that required settings are configured"""
        errors = []

        if not self.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required for AI features")

        if not self.SLEEPER_USERNAME:
            errors.append("SLEEPER_USERNAME is required for Sleeper integration")

        if errors:
            print("❌ Configuration Errors:")
            for error in errors:
                print(f"  - {error}")
            print("\nPlease check your .env file and ensure all required variables are set.")
            sys.exit(1)

        print("✅ All required configuration validated")

settings = Settings()

# Validate on import (but allow testing without full config)
if not sys.argv[0].endswith('pytest'):
    settings.validate_required_settings()
```

### Task 9.8: Logging Configuration

#### backend/app/core/logging_config.py

```python
import logging
import sys
from app.core.config import settings

def setup_logging():
    """Configure application logging"""

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.info("Logging configured")
```

Add to `main.py`:
```python
from app.core.logging_config import setup_logging

setup_logging()
```

### Task 9.9: Documentation

#### Create comprehensive README sections

Update main README.md with:
- Quick start guide
- Environment variable reference
- API documentation links
- Troubleshooting section
- FAQ

#### Create CONTRIBUTING.md

```markdown
# Contributing to Fantasy Football AI Manager

## Development Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run `docker-compose up -d`
4. Access application at http://localhost:3000

## Running Tests

```bash
# Backend tests
docker exec -it fantasy-backend pytest

# Frontend tests
cd frontend && npm test
```

## Code Style

- Python: Follow PEP 8, use Black for formatting
- TypeScript: Use Prettier, follow ESLint rules

## Pull Request Process

1. Create feature branch
2. Make changes with tests
3. Ensure all tests pass
4. Submit PR with description
```

### Task 9.10: Deployment Checklist

Create `DEPLOYMENT.md`:

```markdown
# Deployment Checklist

## Pre-Deployment

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations up to date
- [ ] Redis configured
- [ ] Celery workers configured

## Security

- [ ] API keys stored securely
- [ ] CORS configured for production domain
- [ ] Rate limiting enabled
- [ ] HTTPS enabled

## Performance

- [ ] Redis caching enabled
- [ ] Database indexes created
- [ ] Static files optimized
- [ ] CDN configured (if applicable)

## Monitoring

- [ ] Logging configured
- [ ] Error tracking (Sentry, etc.)
- [ ] Performance monitoring
- [ ] Health check endpoints

## Post-Deployment

- [ ] Verify all endpoints working
- [ ] Test WebSocket connections
- [ ] Monitor logs for errors
- [ ] Test agent workflows
```

## Running Final Tests

```bash
# Backend comprehensive test
docker exec -it fantasy-backend python tests/test_end_to_end.py

# Frontend tests
cd frontend && npm test

# Load testing (optional)
docker exec -it fantasy-backend locust -f tests/load_test.py

# Check code quality
docker exec -it fantasy-backend flake8 app/
cd frontend && npm run lint
```

## Success Criteria

After Phase 9:

1. ✅ All tests passing
2. ✅ Error handling comprehensive
3. ✅ Performance optimized
4. ✅ UI polished with loading states
5. ✅ Documentation complete
6. ✅ Ready for deployment

## Production Deployment (Future)

When ready to deploy:

1. **Choose hosting platform**: Vercel (frontend), Railway/Render (backend)
2. **Set up environment variables** in hosting platform
3. **Configure database**: Use managed PostgreSQL (Supabase, Railway)
4. **Set up Redis**: Use managed Redis (Upstash, Redis Cloud)
5. **Deploy backend and frontend**
6. **Set up monitoring**: Sentry, LogRocket, etc.

## Next Steps

🎉 **Congratulations!** Your Fantasy Football AI Manager is complete!

You can now:
- Start managing your fantasy team with AI
- Customize agents for your league
- Add new features as needed
- Deploy to production when ready

## Resources

- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Next.js Testing](https://nextjs.org/docs/testing)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
