# Fantasy Football AI Manager

An intelligent, agentic AI application for managing your fantasy football team on Sleeper. Built with LangGraph multi-agent orchestration, this application analyzes player performance, provides sit/start recommendations, suggests trades, monitors the waiver wire, and can autonomously manage your team.

## Features

- **AI-Powered Sit/Start Decisions**: Analyzes player stats, sentiment from Reddit/Twitter, projections, and matchups
- **Trade Analyzer**: Evaluates trade opportunities and suggests counter-offers
- **Waiver Wire Monitor**: Identifies breakout candidates and priority pickups
- **Lineup Optimizer**: Makes matchup-based lineup decisions
- **Injury Monitoring**: Real-time injury alerts and replacement suggestions
- **Autonomous Management**: Optional full AI management with human-in-the-loop approval

## Tech Stack

### Frontend
- **Next.js 14** (App Router) with TypeScript
- **Tailwind CSS** + **Shadcn/ui** for styling
- **React Query** for data fetching
- **Recharts** for data visualization
- **WebSockets** for real-time updates

### Backend
- **FastAPI** (Python) for API server
- **LangGraph** for multi-agent orchestration
- **Anthropic Claude** for AI reasoning
- **PostgreSQL** for data persistence
- **Redis** for caching and pub/sub
- **Celery** for background jobs

### Data Sources
- **Sleeper API** for fantasy data
- **Reddit (PRAW)** for player sentiment
- **Twitter/X scrapers** for breaking news
- **Tavily/SerpAPI** for web search
- **FantasyPros** for consensus projections

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Next.js Frontend                       │
│  (Dashboard, Lineup Optimizer, Trade Analyzer, Waiver Wire) │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         LangGraph Agent Orchestrator                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │   │
│  │  │ Sit/Start    │  │ Trade        │  │ Waiver   │  │   │
│  │  │ Agent        │  │ Analyzer     │  │ Wire     │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────┘  │   │
│  │  ┌──────────────┐  ┌──────────────┐                │   │
│  │  │ Lineup       │  │ Monitoring   │                │   │
│  │  │ Manager      │  │ Agent        │                │   │
│  │  └──────────────┘  └──────────────┘                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    PostgreSQL         Redis           Celery
    (Data Store)     (Cache/Jobs)    (Background)
```

## Project Structure

```
fantasy-football-agent/
├── frontend/                    # Next.js application
│   ├── app/                    # App router pages
│   ├── components/             # Reusable components
│   ├── lib/                    # Utilities and API clients
│   └── types/                  # TypeScript definitions
│
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── api/                # REST endpoints
│   │   ├── agents/             # LangGraph agents
│   │   ├── tools/              # Agent tools
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── core/               # Config, DB connection
│   └── main.py                 # FastAPI entry point
│
├── docs/                        # Phase-by-phase implementation guides
├── docker-compose.yml          # Local development environment
└── .env.example                # Environment variables template
```

## Implementation Phases

This project is organized into 9 implementation phases. Each phase has detailed documentation:

1. **[Phase 1: Project Foundation](./docs/phase-1-foundation.md)** - Initial setup and Docker environment
2. **[Phase 2: Backend Core](./docs/phase-2-backend-core.md)** - FastAPI server and Sleeper API integration
3. **[Phase 3: Database & Models](./docs/phase-3-database.md)** - PostgreSQL setup with SQLAlchemy
4. **[Phase 4: Agent Tools](./docs/phase-4-agent-tools.md)** - Build individual tools for agents
5. **[Phase 5: LangGraph Agents](./docs/phase-5-langgraph-agents.md)** - Multi-agent orchestration
6. **[Phase 6: Frontend Foundation](./docs/phase-6-frontend.md)** - Next.js UI components
7. **[Phase 7: Real-time Integration](./docs/phase-7-realtime.md)** - WebSocket connections
8. **[Phase 8: Feature Completion](./docs/phase-8-features.md)** - End-to-end feature implementation
9. **[Phase 9: Testing & Polish](./docs/phase-9-testing.md)** - Testing and refinements

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- Sleeper account with an active fantasy football league
- Anthropic API key (for Claude)

### Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd fantasy-football-agent
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Add your API keys to `.env`:
```
ANTHROPIC_API_KEY=your_key_here
SLEEPER_USERNAME=your_sleeper_username
```

4. Start all services:
```bash
docker-compose up -d
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Development Workflow

See individual phase documentation for detailed implementation steps. Recommended order:

**Week 1**: Phases 1-3 (Infrastructure)
**Week 2**: Phases 4-5 (AI Agents)
**Week 3**: Phases 6-7 (Frontend & Real-time)
**Week 4**: Phases 8-9 (Features & Polish)

## API Keys Required

- **Anthropic API Key** (required) - Get from https://console.anthropic.com/
- **Tavily API Key** (optional) - For web search - https://tavily.com/
- **Reddit API Credentials** (optional) - For sentiment analysis - https://www.reddit.com/prefs/apps
- **Twitter/X** (optional) - Can use free scrapers like nitter

## Contributing

This is a personal project, but contributions are welcome! Please see individual phase docs for areas that need work.

## License

MIT

## Roadmap

### V1.0 (Current)
- Sleeper integration
- Multi-agent AI orchestration
- Sit/start recommendations
- Trade analysis
- Waiver wire monitoring

### V2.0 (Future)
- Support for ESPN, Yahoo platforms
- Mobile app (React Native)
- League commissioner tools
- Social features (league chat analysis)
- Advanced ML models for predictions

## Support

For issues or questions:
1. Check the phase documentation in `/docs`
2. Review API documentation at http://localhost:8000/docs
3. Open an issue on GitHub

---

Built with Claude AI and LangGraph
