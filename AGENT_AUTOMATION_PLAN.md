# GPT Agent-Style Browser Automation Implementation Plan

## Overview
Build a ChatGPT Agents-style interface with browser automation capabilities to navigate Sleeper, login with saved credentials, and adjust lineups automatically using Claude 4.5 and Playwright.

**Target User Experience**: User opens Agent Window → Tells agent "Set my optimal lineup for week 10" → Agent logs into Sleeper, navigates to lineup page, swaps players based on projections → Shows screenshots of changes → User confirms → Lineup is updated

---

## Current System Architecture (As-Is)

### Backend
- **Framework**: FastAPI with async support
- **Agent**: LangGraph with PostgreSQL checkpointer for conversation persistence
- **Model**: Claude 3.5 Haiku with tool binding
- **Graph Flow**: fetch_context_node → agent_node → tools_node → (loop) → END
- **Streaming**: Server-Sent Events (SSE) for real-time updates
- **Tools**: 13 tools across 3 categories (Research, Roster, Analysis)
- **Database**: PostgreSQL for conversations/messages, Redis for caching

### Frontend
- **Framework**: Next.js 14 with App Router, TypeScript
- **UI**: Tailwind CSS + shadcn/ui components
- **State**: Redux Toolkit for global state, React Query for data fetching
- **Chat Components**: ChatInterface (embedded) and ChatFullscreenModal
- **Streaming**: Fetch API with SSE parsing

### Current Agent Flow
1. User sends message via chat interface
2. Frontend POST to `/api/v1/agents/chat/stream` with thread_id
3. Backend LangGraph executes:
   - fetch_context_node: Gets roster/player data from Sleeper API
   - agent_node: Claude decides which tools to use
   - tools_node: Executes tools (search_web, get_projections, etc.)
   - Loop back to agent for tool result interpretation
4. SSE events stream back: metadata, status, response, done
5. Frontend displays with typewriter effect
6. Conversation saved to PostgreSQL

### Current Limitations
- No browser automation (relies on Sleeper API only)
- No visual confirmation (no screenshots)
- Cannot execute lineup changes (OAuth restriction)
- No step-by-step visual progress
- No autopilot mode
- No credential storage

---

## Proposed Architecture (To-Be)

### New Backend Components

#### 1. Browser Automation Layer (`backend/app/tools/browser/`)
```
browser/
├── __init__.py                    # Package exports
├── playwright_manager.py          # Session lifecycle, browser context management
├── browser_tools.py               # LangChain @tool decorated functions
├── screenshot_storage.py          # Save/serve screenshots with URLs
├── selectors.py                   # Centralized Sleeper CSS/XPath selectors
└── session_store.py               # In-memory active session tracking
```

**Playwright Manager Features**:
- Persistent browser context per user (stays logged in)
- Headful mode for visibility
- Profile storage in `backend/data/browser_profiles/{user_id}/`
- Auto-cleanup on errors or timeout
- Rate limiting with random delays (50-150ms)
- Domain allow-list: `*.sleeper.app`, `accounts.google.com`

**Browser Tools** (9 new tools):
1. `open_page(url: str)` - Navigate with validation
2. `click(selector: str)` - Click with retry logic
3. `type_text(selector: str, text: str, secure: bool)` - Type input
4. `press_key(key: str)` - Keyboard actions (Enter, Tab, etc.)
5. `wait_for(selector: str, timeout_ms: int)` - Wait for element
6. `screenshot(tag: str)` - Capture and save
7. `sleep(ms: int)` - Delay
8. `sleeper_login(use_sso: bool)` - Execute login flow
9. `navigate_to_lineup(league_id: str, week: int)` - Navigate to specific lineup

**Screenshot Storage**:
- Save to `backend/uploads/screenshots/{thread_id}/{timestamp}_{tag}.png`
- Serve via FastAPI StaticFiles at `/uploads/screenshots/`
- Return URL in tool response for frontend display

**Selectors Registry** (`selectors.py`):
```python
SLEEPER_SELECTORS = {
    "login_email": "input[type='email']",
    "login_password": "input[type='password']",
    "login_button": "button:has-text('Log In')",
    "leagues_menu": "a:has-text('Leagues')",
    "edit_lineup_button": "button:has-text('Edit Lineup')",
    "save_lineup_button": "button:has-text('Save')",
    # ... more selectors
}
```

#### 2. Credential Storage (`backend/app/services/credential_service.py`)
- Use Python `keyring` library for OS-level credential storage
- Store: email, password (encrypted), use_sso flag
- Methods: `save_credentials()`, `get_credentials()`, `delete_credentials()`
- Per-user storage using user_id as key

#### 3. New API Endpoints (`backend/app/api/browser.py`)
```python
POST   /api/v1/browser/start-session     # Initialize browser, returns session_id
POST   /api/v1/browser/stop-session      # Cleanup browser
GET    /api/v1/browser/status/{id}       # Get session status
POST   /api/v1/browser/autopilot         # Enable/disable autopilot mode
```

#### 4. WebSocket Upgrade (`backend/app/api/agents.py`)
Replace SSE with WebSocket for bidirectional communication:

**New Endpoint**: `WS /api/v1/agents/chat/ws`

**Event Protocol**:
```json
// Client → Server
{"type": "user_message", "message": "Set my lineup", "thread_id": "..."}
{"type": "control", "action": "stop|pause|resume|confirm"}
{"type": "autopilot", "enabled": true}

// Server → Client
{"type": "status", "status": "idle|running|paused"}
{"type": "generation", "role": "assistant", "text": "..."}
{"type": "tool_call", "id": "t_123", "name": "browser.click", "args": {...}}
{"type": "tool_result", "id": "t_123", "ok": true, "data": {...}}
{"type": "screenshot", "url": "/uploads/screenshots/...", "tag": "login"}
{"type": "step", "label": "Navigate to Sleeper", "note": "Opening browser"}
{"type": "confirmation_required", "action": {...}, "reason": "..."}
{"type": "done"}
```

#### 5. Enhanced Agent System Prompt
Add browser automation instructions to `langgraph_chat_agent.py`:

```python
BROWSER_AUTOMATION_PROMPT = """
You are "Fantasy Agent", a web-automation assistant for Sleeper fantasy football.

BROWSER TOOLS AVAILABLE:
- Navigation: open_page, wait_for, sleep
- Interaction: click, type_text, press_key
- Observation: screenshot
- Workflows: sleeper_login, navigate_to_lineup

LINEUP CHANGE WORKFLOW:
1. **Analyze**: Get projections for all starters and bench
2. **Recommend**: Show user optimal swaps with reasoning
3. **Confirm**: If autopilot=false, wait for user confirmation
4. **Execute**:
   a. sleeper_login()
   b. navigate_to_lineup(league_id, week)
   c. screenshot("before_changes")
   d. For each swap: click/drag players
   e. screenshot("after_changes")
   f. click save_lineup_button
   g. screenshot("saved")
5. **Verify**: Summarize changes made

SAFETY RULES:
- Only access *.sleeper.app and accounts.google.com
- Take screenshot BEFORE destructive actions
- If autopilot=false, request confirmation before saving
- Never echo credentials in responses
- Use random delays between actions (50-150ms)
"""
```

### New Frontend Components

#### 1. Agent Window (`frontend/components/agent-window/`)
```
agent-window/
├── index.tsx                    # Main container with layout
├── chat-panel.tsx               # Left panel: messages + tool cards
├── tool-call-card.tsx           # Visual card for each tool execution
├── step-timeline.tsx            # Right panel: step progress
├── screenshot-strip.tsx         # Horizontal screenshot gallery
├── control-panel.tsx            # Top bar: Run/Stop/Autopilot
└── agent-status-badge.tsx       # Status indicator (idle/running/paused)
```

**Layout**:
```
┌──────────────────────────────────────────────────────────┐
│ [Status] [Autopilot Toggle] [Stop]            [Close]    │ Control Panel
├─────────────────────────┬────────────────────────────────┤
│                         │                                │
│   Chat Messages         │   Step Timeline                │
│   ┌─────────────────┐   │   ✓ Login to Sleeper           │
│   │ Tool Call Card  │   │   ✓ Navigate to lineup         │
│   │ browser.login   │   │   → Analyzing roster           │
│   │ ✓ Success       │   │   • Make swaps                 │
│   └─────────────────┘   │   • Save changes               │
│                         │                                │
│   [User message...]     │   Screenshot Strip:            │
│   [Assistant reply...]  │   [📷][📷][📷]                  │
│                         │                                │
├─────────────────────────┴────────────────────────────────┤
│ [Message input...........................] [Send]         │
└──────────────────────────────────────────────────────────┘
```

#### 2. Tool Call Card Component
```tsx
interface ToolCall {
  id: string;
  name: string;
  args: Record<string, any>;
  status: 'pending' | 'running' | 'success' | 'error';
  result?: any;
  error?: string;
  duration?: number;
}

// Visual card showing:
// - Tool name with icon
// - Arguments (collapsed by default)
// - Status indicator (spinner/checkmark/error)
// - Result preview
// - Timestamp/duration
```

#### 3. Step Timeline Component
```tsx
interface Step {
  label: string;
  note?: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  timestamp?: Date;
}

// Visual timeline:
// ✓ Completed step (green)
// → Active step (blue, animated)
// • Pending step (gray)
// ✗ Error step (red)
```

#### 4. Screenshot Strip Component
```tsx
interface Screenshot {
  url: string;
  tag: string;
  timestamp: Date;
}

// Horizontal scrollable gallery
// Click to enlarge
// Tag labels
// Timestamp info
```

#### 5. WebSocket Client (`frontend/lib/websocket-client.ts`)
```typescript
class AgentWebSocketClient {
  connect(url: string, onMessage: (event: AgentEvent) => void)
  send(message: ClientMessage)
  disconnect()
  // Auto-reconnect logic
  // Heartbeat/ping
}
```

#### 6. Redux Agent Slice (`frontend/store/slices/agentSlice.ts`)
```typescript
interface AgentState {
  status: 'idle' | 'running' | 'paused';
  autopilot: boolean;
  currentStep: string | null;
  steps: Step[];
  toolCalls: ToolCall[];
  screenshots: Screenshot[];
  browserSessionId: string | null;
  error: string | null;
}

// Actions:
// - setStatus, setAutopilot
// - addStep, updateStep
// - addToolCall, updateToolCall
// - addScreenshot
// - resetAgent
```

#### 7. Settings Page Enhancement (`app/settings/page.tsx`)
Add new section:
```tsx
<Card>
  <CardHeader>Sleeper Credentials</CardHeader>
  <CardContent>
    <Label>Email</Label>
    <Input type="email" />

    <Label>Password</Label>
    <Input type="password" />

    <Checkbox>Use SSO (Google)</Checkbox>

    <Button>Save Credentials</Button>
    <Button variant="outline">Test Connection</Button>
  </CardContent>
</Card>
```

---

## Implementation Phases

### Phase 1: Backend Browser Infrastructure (6-8 hours)

**Tasks**:
1. ✅ Install Playwright + keyring dependencies
2. Create `backend/app/tools/browser/` directory structure
3. Implement `playwright_manager.py`:
   - BrowserSessionManager class
   - Context creation with persistent profile
   - Session tracking (in-memory dict)
   - Cleanup methods
4. Implement `selectors.py`:
   - Define all Sleeper selectors
   - Helper methods for selector building
5. Implement `screenshot_storage.py`:
   - Save screenshot to file system
   - Generate unique filename
   - Return public URL
6. Implement `browser_tools.py`:
   - 9 browser tools with @tool decorator
   - Error handling and retries
   - Integration with playwright_manager
7. Implement `credential_service.py`:
   - Save/get/delete using keyring
   - Encryption helpers
8. Create `backend/app/api/browser.py`:
   - Session management endpoints
   - Status tracking
9. Add browser tools to `ALL_TOOLS` in `tools_schema.py`
10. Create FastAPI static files mount for screenshots

**Acceptance Criteria**:
- Browser can be started/stopped via API
- Screenshots are captured and accessible via URL
- Credentials are stored securely in OS keychain
- All browser tools are callable from agent

### Phase 2: WebSocket Infrastructure (3-4 hours)

**Tasks**:
1. Create WebSocket endpoint `/api/v1/agents/chat/ws`
2. Implement bidirectional event handling
3. Integrate with LangGraph streaming
4. Add tool call/result event emission
5. Add step event emission
6. Add confirmation flow for non-autopilot mode

**Acceptance Criteria**:
- WebSocket connects and maintains connection
- All event types are emitted correctly
- Client can send control messages (stop/pause/confirm)
- Connection survives network hiccups (reconnect)

### Phase 3: Frontend Agent Window (6-8 hours)

**Tasks**:
1. Create `frontend/components/agent-window/` directory
2. Implement AgentWindow main component with layout
3. Implement ChatPanel with tool call cards
4. Implement ToolCallCard component
5. Implement StepTimeline component
6. Implement ScreenshotStrip component
7. Implement ControlPanel with Run/Stop/Autopilot
8. Create WebSocket client (`websocket-client.ts`)
9. Create Redux agentSlice
10. Wire WebSocket events to Redux state
11. Create agent page route (`/app/agent/page.tsx`)
12. Add navigation to agent window from main app

**Acceptance Criteria**:
- Agent window displays with proper layout
- Tool calls appear as cards in real-time
- Screenshots display in gallery
- Step timeline updates as agent progresses
- Run/Stop/Autopilot controls work
- WebSocket connection managed properly

### Phase 4: Settings & Credentials (2-3 hours)

**Tasks**:
1. Add credentials section to settings page
2. Create API client methods for credentials
3. Implement save/test credentials flow
4. Add visual feedback for credential status
5. Add credential validation

**Acceptance Criteria**:
- User can save Sleeper credentials
- Credentials are encrypted and stored in OS keychain
- Test connection button validates credentials
- Visual indicator shows credential status

### Phase 5: Agent Enhancement (3-4 hours)

**Tasks**:
1. Update system prompt in `langgraph_chat_agent.py`
2. Add browser automation workflow logic
3. Implement autopilot mode handling
4. Add confirmation flow for non-autopilot
5. Test agent can execute full workflow:
   - Login to Sleeper
   - Navigate to lineup
   - Analyze roster
   - Recommend swaps
   - Execute swaps (with confirmation)
   - Save lineup

**Acceptance Criteria**:
- Agent can login to Sleeper automatically
- Agent navigates to correct lineup page
- Agent executes swaps correctly
- Autopilot mode works (no confirmations)
- Non-autopilot pauses for confirmations
- Screenshots captured at key points

### Phase 6: Integration & Polish (2-3 hours)

**Tasks**:
1. End-to-end testing
2. Error handling improvements
3. Loading states and animations
4. Mobile responsiveness
5. Documentation
6. Cleanup and code review

**Acceptance Criteria**:
- Full workflow works end-to-end
- Error states are handled gracefully
- UI is responsive and polished
- All features documented

---

## Technical Specifications

### Browser Session Management

**Session Lifecycle**:
1. `start_session(user_id)` → Creates persistent context, returns session_id
2. Session stored in memory: `{session_id: {context, page, user_id, created_at}}`
3. `stop_session(session_id)` → Closes context, removes from store
4. Auto-cleanup after 30 minutes of inactivity

**Persistent Context Benefits**:
- Stays logged in between sessions
- Faster subsequent runs
- Preserves cookies/local storage

### Security Considerations

**Credential Storage**:
- Never store plaintext passwords in database
- Use OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Access via Python `keyring` library
- Each user has isolated credential namespace

**Browser Safety**:
- Domain allow-list prevents navigation to malicious sites
- No arbitrary JavaScript execution
- Rate limiting prevents abuse
- Audit log of all browser actions

**API Security**:
- WebSocket authentication via session token
- User-scoped browser sessions (can't access other users' sessions)
- CORS configured properly

### Performance Optimizations

**Screenshot Management**:
- Compress screenshots (PNG → WebP)
- Delete screenshots older than 7 days (background job)
- Lazy load in screenshot strip

**Browser Resource Management**:
- Close idle browser contexts after 30 min
- Limit max concurrent sessions per user (2)
- Reuse context for same user

**Frontend**:
- Virtual scrolling for long tool call lists
- Screenshot thumbnails (full resolution on click)
- Debounce WebSocket sends

---

## Testing Strategy

### Unit Tests
- Browser tools: Mock Playwright, test tool logic
- Credential service: Test encryption/decryption
- WebSocket client: Mock WebSocket, test event handling

### Integration Tests
- Full browser workflow: Login → Navigate → Interact
- WebSocket flow: Connect → Send → Receive → Disconnect
- Agent flow: Message → Tool calls → Response

### Manual Testing Checklist
- [ ] Login with email/password
- [ ] Login with SSO
- [ ] Navigate to league lineup
- [ ] Execute player swap
- [ ] Save lineup
- [ ] Screenshots captured correctly
- [ ] Tool cards display properly
- [ ] Step timeline updates
- [ ] Autopilot mode works
- [ ] Non-autopilot confirmation works
- [ ] Stop button works mid-execution
- [ ] Error handling (wrong credentials, selector not found, etc.)
- [ ] Mobile responsive

---

## File Structure

### Backend New Files
```
backend/
├── app/
│   ├── tools/
│   │   └── browser/
│   │       ├── __init__.py
│   │       ├── playwright_manager.py      # NEW
│   │       ├── browser_tools.py           # NEW
│   │       ├── screenshot_storage.py      # NEW
│   │       ├── selectors.py               # NEW
│   │       └── session_store.py           # NEW
│   ├── api/
│   │   ├── browser.py                     # NEW
│   │   └── settings.py                    # ENHANCED
│   ├── services/
│   │   └── credential_service.py          # NEW
│   └── models/
│       └── browser_session.py             # NEW (if persisting sessions)
├── uploads/
│   └── screenshots/                       # NEW (screenshot storage)
├── data/
│   └── browser_profiles/                  # NEW (persistent browser contexts)
└── requirements.txt                       # ENHANCED (playwright, keyring)
```

### Frontend New Files
```
frontend/
├── components/
│   └── agent-window/
│       ├── index.tsx                      # NEW
│       ├── chat-panel.tsx                 # NEW
│       ├── tool-call-card.tsx             # NEW
│       ├── step-timeline.tsx              # NEW
│       ├── screenshot-strip.tsx           # NEW
│       ├── control-panel.tsx              # NEW
│       └── agent-status-badge.tsx         # NEW
├── lib/
│   └── websocket-client.ts                # NEW
├── store/
│   └── slices/
│       └── agentSlice.ts                  # NEW
├── app/
│   ├── agent/
│   │   └── page.tsx                       # NEW
│   └── settings/
│       └── page.tsx                       # ENHANCED
└── types/
    └── agent.ts                           # NEW
```

---

## Success Criteria

### MVP (Minimum Viable Product)
1. ✅ User can save Sleeper credentials in settings
2. ✅ Agent can login to Sleeper via browser automation
3. ✅ Agent can navigate to specific league/week lineup
4. ✅ Agent can execute player swaps in Sleeper UI
5. ✅ Screenshots are captured and displayed
6. ✅ Tool calls appear as cards in UI
7. ✅ Basic step timeline shows progress
8. ✅ Run/Stop controls work

### V1.0 (Full Feature Set)
1. ✅ All MVP features
2. ✅ Autopilot mode toggle
3. ✅ Non-autopilot confirmation flow
4. ✅ SSO login support
5. ✅ Error handling and recovery
6. ✅ Mobile responsive design
7. ✅ Full audit log of browser actions
8. ✅ Screenshot management (auto-delete old)

### Future Enhancements (V2.0+)
- Multi-platform support (ESPN, Yahoo)
- Scheduled lineup updates (cron-based)
- Bulk operations (set lineup for multiple leagues)
- Browser recording/playback for debugging
- AI-powered selector discovery (if Sleeper changes selectors)
- Voice control integration
- Slack/Discord notifications

---

## Risk Mitigation

### Technical Risks

**Risk**: Sleeper changes UI selectors
- **Mitigation**: Centralized selector registry, easy to update
- **Mitigation**: Multiple selector strategies (CSS, XPath, text matching)
- **Mitigation**: AI-powered selector discovery (future)

**Risk**: Browser automation detected/blocked
- **Mitigation**: Use real browser (not headless) with persistent profile
- **Mitigation**: Random delays, human-like interactions
- **Mitigation**: Rate limiting

**Risk**: Credential security breach
- **Mitigation**: OS keychain (encrypted at rest)
- **Mitigation**: Never log credentials
- **Mitigation**: Allow SSO to avoid password storage

**Risk**: Browser session crashes
- **Mitigation**: Auto-cleanup and recovery
- **Mitigation**: Error boundaries in UI
- **Mitigation**: Session timeout

### Product Risks

**Risk**: Sleeper TOS violation
- **Mitigation**: User's own credentials, user-initiated actions
- **Mitigation**: Rate limiting prevents abuse
- **Mitigation**: Prefer API when available, browser as fallback

**Risk**: User adoption low
- **Mitigation**: Make it feel like ChatGPT Agents (familiar UX)
- **Mitigation**: Show value immediately (screenshots, automation)
- **Mitigation**: Good onboarding

---

## Timeline

### Week 1
- **Days 1-2**: Backend browser infrastructure (Phase 1)
- **Days 3-4**: WebSocket infrastructure (Phase 2)
- **Day 5**: Code review and testing

### Week 2
- **Days 1-3**: Frontend Agent Window (Phase 3)
- **Day 4**: Settings & Credentials (Phase 4)
- **Day 5**: Code review and testing

### Week 3
- **Days 1-2**: Agent Enhancement (Phase 5)
- **Days 3-4**: Integration & Polish (Phase 6)
- **Day 5**: Final testing and documentation

**Total**: ~15 working days for full implementation

---

## Next Steps

1. ✅ Review and approve this plan
2. → Start Phase 1: Backend Browser Infrastructure
3. → Daily standup to track progress
4. → Demo after each phase
5. → Final review and launch

---

## Questions for Clarification

1. **SSO Priority**: Should we implement Google SSO first or focus on email/password?
   - Recommendation: Email/password first (simpler), SSO in V1.1

2. **Autopilot Default**: Should autopilot be ON or OFF by default?
   - Recommendation: OFF for safety, user can toggle

3. **Screenshot Retention**: How long should we keep screenshots?
   - Recommendation: 7 days, then auto-delete

4. **Session Timeout**: How long before browser session is auto-closed?
   - Recommendation: 30 minutes of inactivity

5. **Max Concurrent Sessions**: How many browser sessions per user?
   - Recommendation: 2 (one active, one backup)

---

**Plan Created**: 2025-10-28
**Author**: Claude (Sonnet 4.5)
**Status**: Ready for Implementation
