# Phase 7: Real-time Integration

**Goal**: Add WebSocket connections for real-time agent status updates and notifications

**Estimated Time**: 4-6 hours

**Dependencies**: Phases 1-6

## Overview

Implement real-time features:
- WebSocket connection between frontend and backend
- Live agent task progress updates
- Real-time notifications for injuries, waiver pickups, etc.
- Background job scheduling with Celery

## Tasks Breakdown

### Task 7.1: WebSocket Backend

#### backend/app/api/websocket.py

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    disconnected.add(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, user_id)

    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Receive messages from client (if needed)
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif message.get("type") == "subscribe":
                # Subscribe to specific updates (e.g., task updates)
                task_id = message.get("task_id")
                # Store subscription (in production, use Redis)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)

async def send_agent_update(
    user_id: str,
    task_id: str,
    status: str,
    progress: int,
    current_step: str,
    data: dict = None
):
    """Send agent task update to user"""
    message = {
        "type": "agent_update",
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "current_step": current_step,
        "data": data or {}
    }
    await manager.send_personal_message(message, user_id)

async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
):
    """Send notification to user"""
    notification = {
        "type": "notification",
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(notification, user_id)
```

### Task 7.2: Agent API Endpoints

#### backend/app/api/agents.py

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.agent import AgentTask, AgentTaskType, AgentTaskStatus
from app.agents.orchestrator import orchestrator
from app.api.websocket import send_agent_update
from pydantic import BaseModel
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

class SitStartRequest(BaseModel):
    league_id: str
    roster_id: int
    week: Optional[int] = None

class TradeAnalysisRequest(BaseModel):
    league_id: str
    my_players: list[str]
    their_players: list[str]

async def run_agent_task(
    task_id: str,
    user_id: str,
    task_type: str,
    input_data: dict,
    db: AsyncSession
):
    """Run agent task in background"""
    try:
        # Update task status
        result = await db.execute(
            select(AgentTask).where(AgentTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = AgentTaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        await db.commit()

        # Send initial update
        await send_agent_update(
            user_id, task_id, "in_progress", 10, "Initializing..."
        )

        # Run orchestrator
        initial_state = {
            "user_id": user_id,
            "task_id": task_id,
            "task_type": task_type,
            **input_data
        }

        # Send progress updates at different stages
        await send_agent_update(
            user_id, task_id, "in_progress", 30, "Fetching data..."
        )

        result = await orchestrator.run(initial_state)

        # Update task with results
        task.status = AgentTaskStatus.COMPLETED
        task.result = result.get("recommendations", [])
        task.progress_percentage = 100
        task.completed_at = datetime.utcnow()
        await db.commit()

        # Send final update
        await send_agent_update(
            user_id,
            task_id,
            "completed",
            100,
            "Analysis complete",
            {"recommendations": task.result}
        )

    except Exception as e:
        logger.error(f"Agent task error: {e}")

        # Update task with error
        if task:
            task.status = AgentTaskStatus.FAILED
            task.error_message = str(e)
            await db.commit()

        # Send error update
        await send_agent_update(
            user_id, task_id, "failed", 0, "Error occurred"
        )

@router.post("/sit-start")
async def run_sit_start_analysis(
    request: SitStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Run sit/start analysis"""

    # Create task record
    task_id = str(uuid.uuid4())
    user_id = "test_user"  # Would come from auth

    task = AgentTask(
        id=task_id,
        user_id=user_id,
        league_id=request.league_id,
        task_type=AgentTaskType.SIT_START,
        status=AgentTaskStatus.PENDING,
        input_data={
            "league_id": request.league_id,
            "roster_id": request.roster_id,
            "week": request.week
        }
    )

    db.add(task)
    await db.commit()

    # Run in background
    background_tasks.add_task(
        run_agent_task,
        task_id,
        user_id,
        "sit_start",
        task.input_data,
        db
    )

    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Analysis started"
    }

@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent task status"""

    result = await db.execute(
        select(AgentTask).where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress_percentage,
        "current_step": task.current_step,
        "result": task.result,
        "error": task.error_message
    }

@router.post("/trade-analysis")
async def run_trade_analysis(
    request: TradeAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Run trade analysis"""

    task_id = str(uuid.uuid4())
    user_id = "test_user"

    task = AgentTask(
        id=task_id,
        user_id=user_id,
        league_id=request.league_id,
        task_type=AgentTaskType.TRADE_ANALYSIS,
        status=AgentTaskStatus.PENDING,
        input_data={
            "league_id": request.league_id,
            "my_players": request.my_players,
            "their_players": request.their_players
        }
    )

    db.add(task)
    await db.commit()

    background_tasks.add_task(
        run_agent_task,
        task_id,
        user_id,
        "trade_analysis",
        task.input_data,
        db
    )

    return {
        "task_id": task_id,
        "status": "pending"
    }
```

### Task 7.3: Update main.py

```python
from app.api import sleeper, agents, websocket

# Include WebSocket router
app.include_router(sleeper.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(websocket.router)
```

### Task 7.4: Frontend WebSocket Client

#### frontend/lib/websocket-client.ts

```typescript
type MessageHandler = (message: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private userId: string;
  private messageHandlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(userId: string) {
    this.userId = userId;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = process.env.NEXT_PUBLIC_WS_URL || 'localhost:8000';
    this.url = `${wsProtocol}//${wsHost}/ws/${userId}`;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.messageHandlers.forEach((handler) => handler(message));
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  subscribe(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    }
  }
}
```

#### frontend/hooks/use-websocket.ts

```typescript
'use client';

import { useEffect, useState, useRef } from 'react';
import { WebSocketClient } from '@/lib/websocket-client';

export function useWebSocket(userId: string) {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const clientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    if (!userId) return;

    const client = new WebSocketClient(userId);
    clientRef.current = client;

    const unsubscribe = client.subscribe((message) => {
      setMessages((prev) => [...prev, message]);

      // Handle different message types
      if (message.type === 'agent_update') {
        // Trigger UI updates
        console.log('Agent update:', message);
      } else if (message.type === 'notification') {
        // Show notification
        console.log('Notification:', message);
      }
    });

    client.connect();
    setIsConnected(true);

    return () => {
      unsubscribe();
      client.disconnect();
      setIsConnected(false);
    };
  }, [userId]);

  const sendMessage = (message: any) => {
    clientRef.current?.send(message);
  };

  return {
    isConnected,
    messages,
    sendMessage,
  };
}
```

### Task 7.5: Real-time Progress Component

#### frontend/components/agent-progress.tsx

```typescript
'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useWebSocket } from '@/hooks/use-websocket';

interface AgentProgressProps {
  taskId: string;
  userId: string;
  onComplete?: (result: any) => void;
}

export function AgentProgress({ taskId, userId, onComplete }: AgentProgressProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('pending');
  const [currentStep, setCurrentStep] = useState('');
  const { messages } = useWebSocket(userId);

  useEffect(() => {
    // Listen for updates for this specific task
    const update = messages.find(
      (m) => m.type === 'agent_update' && m.task_id === taskId
    );

    if (update) {
      setProgress(update.progress);
      setStatus(update.status);
      setCurrentStep(update.current_step);

      if (update.status === 'completed' && onComplete) {
        onComplete(update.data);
      }
    }
  }, [messages, taskId, onComplete]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Analysis in Progress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={progress} />
        <div className="text-sm text-muted-foreground">
          {currentStep || 'Initializing...'}
        </div>
        <div className="text-xs">
          Status: <span className="font-semibold capitalize">{status}</span>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 7.6: Celery Setup for Background Jobs

#### backend/celery_worker.py

```python
from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "fantasy_football",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task(name="monitor_injuries")
def monitor_injuries():
    """Scheduled task to monitor player injuries"""
    logger.info("Running injury monitoring task")
    # Implementation here

@celery_app.task(name="check_waiver_wire")
def check_waiver_wire():
    """Scheduled task to check waiver wire"""
    logger.info("Running waiver wire check")
    # Implementation here

@celery_app.task(name="optimize_lineups")
def optimize_lineups():
    """Scheduled task to optimize lineups before games"""
    logger.info("Running lineup optimization")
    # Implementation here

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    'monitor-injuries-every-hour': {
        'task': 'monitor_injuries',
        'schedule': 3600.0,  # Every hour
    },
    'check-waiver-every-6-hours': {
        'task': 'check_waiver_wire',
        'schedule': 21600.0,  # Every 6 hours
    },
    'optimize-lineups-before-games': {
        'task': 'optimize_lineups',
        'schedule': 1800.0,  # Every 30 minutes
    },
}
```

#### Add Celery to docker-compose.yml

```yaml
  celery-worker:
    build: ./backend
    container_name: fantasy-celery-worker
    command: celery -A celery_worker worker --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
    env_file:
      - .env
    depends_on:
      - redis
      - postgres

  celery-beat:
    build: ./backend
    container_name: fantasy-celery-beat
    command: celery -A celery_worker beat --loglevel=info
    volumes:
      - ./backend:/app
    environment:
      - REDIS_HOST=redis
    env_file:
      - .env
    depends_on:
      - redis
```

## Testing

```bash
# Test WebSocket connection
# Open browser console at http://localhost:3000
const ws = new WebSocket('ws://localhost:8000/ws/test_user');
ws.onmessage = (event) => console.log(JSON.parse(event.data));

# Start Celery worker
docker-compose up celery-worker celery-beat
```

## Success Criteria

After Phase 7:

1. ✅ WebSocket server running
2. ✅ Frontend can connect to WebSocket
3. ✅ Agent updates sent in real-time
4. ✅ Progress bar updates during analysis
5. ✅ Celery workers running
6. ✅ Background jobs scheduled

## Next Steps

Proceed to **[Phase 8: Feature Completion](./phase-8-features.md)** to implement all end-to-end features.

## Resources

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
