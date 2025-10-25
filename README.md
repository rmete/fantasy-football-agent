# Fantasy Football AI Manager

An intelligent, agentic AI application for managing your fantasy football team on Sleeper. Built with LangGraph multi-agent orchestration, this application features real-time web search, defensive matchup analysis, streaming chat with agent thinking visualization, and autonomous lineup management.

<img width="1455" height="875" alt="image" src="https://github.com/user-attachments/assets/d2985931-b975-42bd-9cab-a3d3438111e9" />


## Core Features

### **Intelligent Chat Assistant**
- **Streaming responses** with real-time agent status updates
- **Typewriter effect** showing agent thinking process:
  - "Fetching your roster data..."
  - "Searching the web..."
  - "Analyzing defensive matchups..."
  - "Summarizing insights..."
  - "Cooking up your answer..."
- **Natural language queries** - Ask questions like:
  - "Search for best waiver wire pickups"
  - "Which of my players have the best matchups?"
  - "Who should I start this week?"
  - "How is the Giants defense against the pass this year?"

### **Web Search Integration**
- **Dual search strategy**: Tavily API (primary) + DuckDuckGo (fallback)
- **Automatic activation** when you ask questions like:
  - "Search for..." / "Find..." / "Look up..."
  - "What are the best waiver wire pickups?"
  - "Latest news on [player]"
- **Real results** from FantasyPros, Yahoo Sports, ESPN, etc.
- **Year-specific queries** (always includes "2025" for accuracy)

### **Defense vs Position Matchup Analysis**
- **Intelligent matchup ratings** for your players
- **Position-specific analysis**:
  - RBs → "How are the [Team] against the run?"
  - QBs/WRs → "How is the [Team] defense against the pass?"
  - TEs → "How are the [Team] against tight ends?"
- **Automatic activation** when you ask:
  - "Which players have the best matchups?"
  - "Who has a favorable matchup this week?"
  - "Best matchup to exploit?"
- **Web-powered ratings**: Searches for current defensive rankings

### **Sit/Start Analysis**
- Analyzes player stats, projections, and matchups
- Provides confidence levels and reasoning
- Considers injuries, recent performance, and opponent strength

### **Dynamic NFL Week Detection**
- Automatically calculates current NFL week based on season start date
- No manual updates needed - always uses the correct week
- Shows week information in UI and uses it for all analyses

## Tech Stack

### Frontend
- **Next.js 14** (App Router) with TypeScript
- **Tailwind CSS** + **Shadcn/ui** for styling
- **React Query (TanStack Query)** for data fetching and caching
- **Server-Sent Events (SSE)** for streaming chat
- **Custom typewriter effect** for agent status visualization

### Backend
- **FastAPI** (Python 3.11+) for high-performance async API
- **LangGraph** for multi-agent orchestration
- **Multi-LLM Support**:
  - **Anthropic Claude** (primary - Haiku 3.5 for speed)
  - **OpenAI GPT** (optional alternative)
  - **Google Gemini** (optional alternative)
- **PostgreSQL** for data persistence
- **Redis** for caching and pub/sub
- **Async PRAW** for Reddit sentiment analysis

### AI Agent Tools

#### 1. **Web Search Tool** (`app/tools/web_search.py`)
Searches the web for fantasy football information using dual providers.

**Methods:**
- `search_player_news(player_name, context)` - Find latest player news
- `search_matchup_analysis(team1, team2, week)` - Find matchup insights
- `general_search(query, max_results)` - General web search

**Example Usage:**
```python
# Agent automatically calls when user asks:
# "Search for best waiver wire pickups week 8 2025"
results = await web_search_tool.general_search(
    "best fantasy football waiver wire pickups week 8 2025",
    max_results=5
)
```

**Providers:**
- **Tavily** (primary) - High-quality, AI-optimized search results
- **DuckDuckGo** (fallback) - Free, unlimited searches

#### 2. **Defense Matchup Analyzer** (`app/tools/defense_matchup.py`)
Analyzes how defenses perform against specific positions using web search.

**Methods:**
- `analyze_defense_vs_position(defense_team, position, week, year)` - Get defense rating
- `analyze_player_matchup(player_name, player_team, position, opponent, week)` - Full player matchup analysis

**Example Usage:**
```python
# Automatically triggered when user asks:
# "Which of my players have the best matchups?"
matchup = await defense_matchup_analyzer.analyze_defense_vs_position(
    defense_team="Falcons",
    position="RB",  # or "QB", "WR", "TE"
    week=8,
    year=2025
)
# Returns: {"recommendation": "favorable" | "neutral" | "unfavorable", ...}
```

**Queries Generated:**
- RBs: "How are the Falcons defense against the run 2025 week 8"
- QBs/WRs: "How is the Falcons defense against the pass 2025 week 8"
- TEs: "How are the Falcons defense against tight ends 2025 week 8"

#### 3. **NFL Schedule Tool** (`app/tools/nfl_schedule.py`)
Determines team opponents for specific weeks.

**Methods:**
- `get_team_opponent(team_abbr, week, season)` - Get opponent for a team
- `get_team_full_name(team_abbr)` - Convert abbreviation to full name

**Example Usage:**
```python
opponent = await nfl_schedule_tool.get_team_opponent("KC", week=8)
# Returns: "LV" (Las Vegas Raiders)
```

#### 4. **Sleeper Client** (`app/tools/sleeper_client.py`)
Interfaces with Sleeper API for league and player data.

**Methods:**
- `get_user(username)` - Get user info
- `get_user_leagues(user_id, season)` - Get user's leagues
- `get_league(league_id)` - Get league details
- `get_league_rosters(league_id)` - Get all rosters
- `get_players()` - Get all NFL players (cached)

#### 5. **Projection Tool** (`app/tools/projections.py`)
Fetches and calculates player projections.

**Methods:**
- `get_player_projection(player_name, position, week)` - Get fantasy point projection

#### 6. **Injury Tool** (`app/tools/injuries.py`)
Monitors player injury status.

**Methods:**
- `check_player_injury_status(player_id, player_name)` - Check injury status

#### 7. **Reddit Sentiment Tool** (`app/tools/reddit_scraper.py`)
Analyzes community sentiment from r/fantasyfootball.

**Methods:**
- `get_player_sentiment(player_name)` - Analyze Reddit discussions

### Data Sources
- **Sleeper API** - Primary fantasy data source
- **Tavily** - AI-optimized web search
- **DuckDuckGo** - Fallback web search
- **Reddit (Async PRAW)** - Community sentiment
- **FantasyPros** - Consensus projections (via web search)

## 🏗️ Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Frontend (Port 3000)              │
│                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────┐│
│  │  Lineup Page    │  │  Chat Interface  │  │  Roster     ││
│  │  (Dashboard)    │  │  (Streaming SSE) │  │  Display    ││
│  └─────────────────┘  └──────────────────┘  └─────────────┘│
└────────────────────────┬──────────────────────────────────────┘
                         │ REST API + SSE Streaming
┌────────────────────────▼──────────────────────────────────────┐
│                 FastAPI Backend (Port 8000)                    │
│                                                                │
│              /api/v1/agents/chat/stream                        │
│                          │                                     │
│                          ▼                                     │
│              ┌───────────────────────────┐                    │
│              │  LangGraph Chat Agent     │                    │
│              │  (langgraph_chat_agent)   │                    │
│              └───────────────────────────┘                    │
│                          │                                     │
│          [See detailed diagram below]                          │
│                                                                │
└─────────────────────────┬──────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
    PostgreSQL         Redis        External APIs
  (User Data,      (Caching,      (Sleeper, Tavily,
   Preferences)     Sessions)      DuckDuckGo, Reddit)
```

### LangGraph Agent Orchestration

The chat agent uses **LangGraph** for intelligent, LLM-driven tool selection. The agent autonomously decides which tools to use based on the user's query.

```
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph Chat Agent Workflow                  │
└──────────────────────────────────────────────────────────────────┘

    User Message: "Search for waiver wire RBs. Check injuries."
           │
           ▼
    ┌──────────────────┐
    │  fetch_context   │  ← Load roster & player data from Sleeper
    │     (Node 1)     │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │   agent (Node 2) │  ← Claude LLM with .bind_tools(ALL_TOOLS)
    │                  │    Reads tool descriptions and decides:
    │  Bound Tools:    │    "I need search_web AND check_injury_status"
    │  • search_web    │
    │  • get_news      │    Returns: tool_calls = [
    │  • analyze_def   │      {name: "search_web", args: {...}},
    │  • get_roster    │      {name: "check_injury_status", args: {...}}
    │  • check_injury  │    ]
    │  • get_proj      │
    │  • (10 tools)    │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ _should_continue │  ← Check: Does last message have tool_calls?
    │  (Conditional)   │
    └─────┬───────┬────┘
          │       │
    Yes   │       │ No
          │       └──────────────────────┐
          ▼                              ▼
    ┌──────────────────┐           ┌─────────┐
    │  tools (Node 3)  │           │   END   │ ← Return final response to user
    │                  │           └─────────┘
    │  ToolNode:       │
    │  Automatically   │
    │  executes tools  │
    │  requested by    │
    │  the LLM         │
    └────────┬─────────┘
             │
             │ Tool results appended to messages
             │
             └─────────────┐
                           │
                           ▼
                    ┌──────────────────┐
                    │   agent (Node 2) │  ← LLM sees tool results
                    │                  │    Decides: synthesize answer or call more tools
                    │  "I have search  │
                    │  results & injury│
                    │  data. Ready to  │
                    │  respond."       │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ _should_continue │
                    └─────────┬────────┘
                              │
                         No   │
                              ▼
                        ┌─────────┐
                        │   END   │ ← Stream final response
                        └─────────┘
```

### Agent Hierarchy & Tool Organization

The system uses a **LangGraph supervisor pattern** where a single intelligent agent coordinates all tools with conversational memory. The agent autonomously decides which tools to use based on the user's query.

```
                      ┌─────────────────────────────────┐
                      │   LangGraph Chat Agent          │
                      │   (Claude 3.5 Haiku)            │
                      │                                 │
                      │   Features:                     │
                      │   • LLM-driven tool selection   │
                      │   • Conversational memory       │
                      │   • Streaming responses         │
                      │   • Smart swap suggestions      │
                      └──────────┬──────────────────────┘
                                 │
                  ┌──────────────┼──────────────┐
                  │              │              │
          ┌───────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
          │  Research    │ │ Roster   │ │ Analysis   │
          │  Tools (4)   │ │ Tools(3) │ │ Tools (4)  │
          └──────┬───────┘ └────┬─────┘ └─────┬──────┘
                 │              │              │
         ┌───────▼───────┐  ┌───▼──────┐  ┌───▼─────────┐
         │ • search_web  │  │ • get_   │  │ • get_player│
         │ • get_player_ │  │   roster │  │   _projection│
         │   news        │  │ • identify│  │ • check_    │
         │ • analyze_    │  │   _player_│  │   injury_   │
         │   defense_vs_ │  │   by_name│  │   status    │
         │   position    │  │ • swap_  │  │ • get_      │
         │ • get_team_   │  │   players│  │   community_│
         │   opponent    │  │          │  │   sentiment │
         │               │  │          │  │ • analyze_  │
         │               │  │          │  │   player_   │
         │               │  │          │  │   matchup   │
         └───────────────┘  └──────────┘  └─────────────┘
```

### Tool Distribution

The agent has access to **11 tools** organized into 3 categories:

**Research Tools** (web search, news, matchups)
- `search_web` - General web search for fantasy info
- `get_player_news` - Latest player news articles
- `analyze_defense_vs_position` - Defensive matchup ratings
- `get_team_opponent` - Find weekly opponent

**Roster Tools** (lineup management)
- `get_roster` - View current lineup
- `identify_player_by_name` - Find player IDs
- `swap_players` - 🆕 Propose lineup changes (start/bench players)

**Analysis Tools** (projections, injuries, sentiment)
- `get_player_projection` - Fantasy point projections
- `check_injury_status` - Injury reports
- `get_community_sentiment` - Reddit sentiment analysis
- `analyze_player_matchup` - Complete matchup analysis

### Key Agent Features

#### 1. **LLM-Driven Tool Selection**
No hardcoded keyword matching. Claude reads tool descriptions and autonomously decides which tools to use based on context.

**Example:**
- User: *"Who should I start at RB?"*
- Agent thinks: "I need projections, matchups, and injury data" → Calls 3 tools automatically

#### 2. **Conversational Memory**
The agent remembers previous messages in the conversation, enabling natural follow-up questions.

**Example:**
- User: *"Tell me about Ricky Pearsall"*
- Agent: *"Ricky is projected for 11.8 points..."*
- User: *"What's his injury status?"* ← Agent knows "his" = Ricky
- Agent: *"Ricky is healthy with no injury concerns"*

#### 3. **Smart Swap Suggestions**
When you ask to start a player, the agent automatically:
- Identifies all current starters at that position
- Gets projections for each player
- Suggests who to bench (lowest projection)
- Asks for confirmation before proposing the swap

**Example:**
- User: *"Start Christian McCaffrey"*
- Agent: *"You have Derrick Henry (10 pts) and Saquon (12 pts) starting. I recommend benching Henry to start CMC (14 pts). Should I propose this swap?"*

#### 4. **Multi-Tool Execution**
Agent can call multiple tools in one decision for comprehensive analysis.

**Example:**
- User: *"Can you start Josh Allen over Dak Prescott?"*
- Agent calls: `get_player_projection` (2x) + `get_team_opponent` (2x) + `search_web` + `swap_players`

#### 5. **Streaming Status Updates**
Frontend receives real-time updates showing agent's thinking process:
- "Fetching your roster data..."
- "Context loaded"
- "Using tools: search_web, check_injury_status..."
- "Agent responded"

#### 6. **Iterative Reasoning**
Agent can call tools, see results, then decide to call more tools or respond.

**Flow:**
1. User asks question
2. Agent calls initial tools
3. Reviews results
4. Decides: "I need more data" → Calls additional tools
5. Synthesizes final answer

#### 7. **Graceful Fallbacks**
Handles missing data, API errors, and empty rosters intelligently. Always asks clarifying questions when needed.

### Example: Agent in Action

**User Query:** *"Who should I start at RB this week? Check injuries and matchups."*

**LangGraph Workflow:**

1. **fetch_context** node loads roster from Sleeper
2. **agent** node (Claude LLM) reads the query and tool descriptions:
   - Recognizes need for multiple tools
   - Decides: `search_web` + `check_injury_status` + `get_team_opponent` + `get_player_projection`
3. **tools** node executes all 4 tools in parallel
4. **agent** node receives results, analyzes, and decides if more tools needed
5. Claude synthesizes final recommendation with reasoning

**Frontend sees:**
```
🔄 Fetching your roster data...
🔄 Context loaded
🔄 Agent responded
🔄 Using tools: search_web...
🔄 Agent responded
🔄 Using tools: check_injury_status...
🔄 Agent responded
🔄 Using tools: get_team_opponent...
🔄 Agent responded
🔄 Using tools: get_player_projection...
🔄 Agent responded
✅ Response: Based on the research, here are my top RB recommendations...
   - Bijan Robinson (healthy, favorable matchup, projected 12.3 pts)
   - Jonathan Taylor (healthy, ranked #2, projected 12.3 pts)
   ...
```

**Key Insight:** The agent autonomously decided which tools to use and how many times to call them—no hardcoded logic!

### Why This Architecture is Powerful

**Traditional Chatbots:**
```
User: "Start CMC"
Bot: Keyword match "start" → Call swap function
Bot: "Error: Need to specify who to bench"
```

**This LangGraph Agent:**
```
User: "Start CMC"
Agent: Analyzes roster → Sees current RB starters
Agent: Calls get_player_projection for CMC + all starting RBs
Agent: Compares: CMC (14 pts), Henry (10 pts), Saquon (12 pts)
Agent: "I recommend benching Henry (lowest). Should I swap?"
User: "Yes"
Agent: Calls swap_players with reasoning
```

## Project Structure

```
fantasy-football-agent/
├── frontend/                      # Next.js application
│   ├── app/
│   │   └── league/[leagueId]/
│   │       └── lineup/
│   │           └── page.tsx      # Main lineup optimizer page
│   ├── components/
│   │   ├── chat-interface.tsx    # Streaming chat with SSE
│   │   ├── typewriter-status.tsx # Agent status visualization
│   │   ├── roster-display.tsx    # Player roster view
│   │   └── ui/                   # Shadcn components
│   └── lib/
│       └── api-client.ts         # API client utilities
│
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   │   ├── agents.py         # Agent endpoints (chat/stream)
│   │   │   └── sleeper.py        # Sleeper API proxy
│   │   ├── agents/
│   │   │   ├── langgraph_chat_agent.py  # 🆕 LangGraph agent with StateGraph
│   │   │   ├── tools_schema.py          # 🆕 LangChain tool wrappers
│   │   │   ├── state.py                 # 🆕 ChatAgentState for LangGraph
│   │   │   ├── chat_agent.py            # Legacy chat agent (deprecated)
│   │   │   ├── sit_start_agent.py
│   │   │   ├── orchestrator.py
│   │   │   └── llm_client.py            # Multi-LLM support
│   │   ├── tools/
│   │   │   ├── web_search.py            # Tavily + DuckDuckGo
│   │   │   ├── defense_matchup.py       # Defense vs position analysis
│   │   │   ├── nfl_schedule.py          # Opponent lookup
│   │   │   ├── sleeper_client.py        # Sleeper API wrapper
│   │   │   ├── projection_tool.py       # Player projections
│   │   │   ├── injury_tool.py           # Injury monitoring
│   │   │   └── reddit_tool.py           # Sentiment analysis
│   │   ├── utils/
│   │   │   └── nfl_week.py              # Dynamic week calculation
│   │   └── core/
│   │       └── config.py                # Environment config
│   └── tests/
│       ├── test_web_search.py           # Web search API tests
│       └── test_langgraph_agent.py      # 🆕 LangGraph agent tests
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Sleeper account with active fantasy league
- **Anthropic API key** (required) - Get from https://console.anthropic.com/
- **Tavily API key** (optional, recommended) - Get from https://tavily.com/

### Setup

1. **Clone and configure:**
```bash
git clone <repository-url>
cd fantasy-football-agent
cp .env.example .env
```

2. **Add your API keys to `.env`:**
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxx
SLEEPER_USERNAME=your_sleeper_username

# Optional but recommended
TAVILY_API_KEY=tvly-xxx

# Optional for sentiment analysis
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT="Fantasy Football Agent"

# Optional - choose LLM provider (defaults to anthropic)
LLM_PROVIDER=anthropic  # or "openai" or "gemini"
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Access the application:**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 💡 Usage Examples

### Chat Interface

Navigate to http://localhost:3000 and select your league. In the chat:

**Search for waiver wire pickups:**
```
User: "Search for best waiver wire pickups week 8"

Agent:
[Typewriter: "Fetching your roster data..."]
[Typewriter: "Searching the web..."]
[Typewriter: "Summarizing insights..."]
[Typewriter: "Cooking up your answer..."]

Response: Based on current waiver wire analysis for Week 8:

Top Pickups:
1. Oronde Gadsden II (WR, LAC) - Emerging target in passing offense
2. Isaac Guerendo (RB, SF) - Potential McCaffrey handcuff value
3. Ty Johnson (RB, BUF) - Increased touches with injuries

[Full analysis with web search results from FantasyPros, Yahoo, etc.]
```

**Analyze matchups:**
```
User: "Which of my players have the best matchups this week?"

Agent:
[Typewriter: "Fetching your roster data..."]
[Typewriter: "Analyzing defensive matchups..."]
[Typewriter: "Summarizing insights..."]

Response: Here are your matchup advantages for Week 8:

FAVORABLE MATCHUPS:
• Derrick Henry (RB) vs CLE - Browns rank 28th against the run
• DJ Moore (WR) vs WAS - Washington's secondary allowing 280+ pass yards/game
• Dak Prescott (QB) vs PHI - Eagles defense vulnerable to mobile QBs

UNFAVORABLE MATCHUPS:
• Josh Jacobs (RB) vs SF - 49ers #2 run defense
```

**General lineup advice:**
```
User: "Who should I start this week?"

Agent:
[Analyzes starters, projections, matchups]

Response: Here are my recommendations for Week 8:

START:
• Dak Prescott over Josh Allen (better matchup)
• Derrick Henry (must-start RB1)
• DJ Moore (WR1 with elite target share)

SIT:
• Jameson Williams (inconsistent target share)
• Consider benching Josh Jacobs if you have alternatives (tough matchup)

[Detailed reasoning for each recommendation]
```

### API Endpoints

#### Streaming Chat (SSE)
```bash
curl -N -X POST http://localhost:8000/api/v1/agents/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for best waiver wire pickups",
    "league_id": "123456",
    "roster_id": 1,
    "week": null
  }'
```

Returns:
```
data: {"type":"status","message":"Fetching your roster data..."}
data: {"type":"status","message":"Searching the web..."}
data: {"type":"status","message":"Summarizing insights..."}
data: {"type":"response","message":"Based on current analysis..."}
data: {"type":"done"}
```

#### Sit/Start Analysis
```bash
curl -X POST http://localhost:8000/api/v1/agents/sit-start \
  -H "Content-Type: application/json" \
  -d '{
    "league_id": "123456",
    "roster_id": 1,
    "week": null
  }'
```

#### Get Current Week
```bash
curl http://localhost:8000/api/v1/agents/week
```

Returns:
```json
{
  "current_week": 8,
  "season_year": 2025,
  "is_preseason": false,
  "is_regular_season": true,
  "days_until_season": 0,
  "season_start_date": "2025-09-04T00:00:00+00:00"
}
```

## 🧪 Testing

### Run Web Search Tests (No Mocks - Real APIs)
```bash
docker exec fantasy-backend bash -c "cd /app && PYTHONPATH=/app python tests/test_web_search.py"
```

This runs comprehensive tests for:
- DuckDuckGo search
- Tavily search (if API key configured)
- Fallback behavior
- General search
- Matchup analysis search
- Player news search

## 🔧 Configuration

### Environment Variables

```bash
# AI/LLM Configuration
ANTHROPIC_API_KEY=sk-ant-xxx           # Required for Claude
OPENAI_API_KEY=sk-xxx                  # Optional for GPT
GOOGLE_API_KEY=xxx                     # Optional for Gemini
LLM_PROVIDER=anthropic                 # anthropic|openai|gemini

# Sleeper Configuration
SLEEPER_USERNAME=your_username         # Your Sleeper username

# Web Search
TAVILY_API_KEY=tvly-xxx               # Optional but recommended
# DuckDuckGo used automatically if Tavily not configured

# Reddit Sentiment (Optional)
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT="Fantasy Football Agent"

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/fantasy
REDIS_URL=redis://redis:6379/0
```

### LLM Provider Configuration

The system supports multiple LLM providers with automatic fallback:

```python
# In .env, set:
LLM_PROVIDER=anthropic  # Primary

# Models used:
# - Anthropic: claude-3-5-haiku-20241022 (fast, cost-effective)
# - OpenAI: gpt-4o-mini (if provider=openai)
# - Gemini: gemini-1.5-flash (if provider=gemini)
```

## 📊 Current Implementation Status

✅ **Complete:**
- Streaming chat with SSE
- Typewriter effect for agent status
- Web search (Tavily + DuckDuckGo)
- Defense vs position matchup analysis
- NFL schedule integration
- Dynamic week calculation
- Multi-LLM support
- Sleeper API integration
- Chat agent with tool calling
- Roster display

🚧 **In Progress:**
- Roster management (swap players via chat)
- Sleeper projections API integration
- Trade analyzer
- Waiver wire monitoring

📋 **Planned:**
- Autonomous team management
- Email/SMS notifications
- Historical performance tracking
- League commissioner tools

## Contributing

Contributions welcome! Areas needing work:
- Additional data sources (ESPN, Yahoo)
- Mobile app development
- Advanced ML models
- Testing and documentation

## License

MIT

## Acknowledgments

- Built with **Claude AI** (Anthropic)
- **LangGraph** for agent orchestration
- **Sleeper API** for fantasy data
- **Tavily** for AI-optimized search
- **Next.js** and **FastAPI** teams

---

**Built for fantasy football managers who want an AI edge**

For issues or questions, check the API docs at http://localhost:8000/docs
