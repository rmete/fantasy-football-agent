/**
 * Redux slice for Agent Window state management
 * Handles browser automation, tool calls, screenshots, and steps
 */
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import type {
  AgentState,
  AgentStatus,
  ToolCall,
  Screenshot,
  Step,
  BrowserSession,
  SessionResponse,
  CredentialsResponse,
  SleeperCredentials,
} from '@/types/agent';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Initial state
const initialState: AgentState = {
  status: 'idle',
  autopilot: false,
  currentStep: null,
  steps: [],
  toolCalls: [],
  screenshots: [],
  browserSessionId: null,
  error: null,
  threadId: null,
};

// Async thunks
export const startBrowserSession = createAsyncThunk<SessionResponse, string>(
  'agent/startBrowserSession',
  async (userId: string) => {
    const response = await fetch(`${API_URL}/api/v1/browser/start-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return response.json();
  }
);

export const stopBrowserSession = createAsyncThunk<void, string>(
  'agent/stopBrowserSession',
  async (sessionId: string) => {
    await fetch(`${API_URL}/api/v1/browser/stop-session/${sessionId}`, {
      method: 'POST',
    });
  }
);

export const getBrowserSessionStatus = createAsyncThunk<BrowserSession, string>(
  'agent/getBrowserSessionStatus',
  async (sessionId: string) => {
    const response = await fetch(`${API_URL}/api/v1/browser/status/${sessionId}`);
    return response.json();
  }
);

export const saveCredentials = createAsyncThunk<
  CredentialsResponse,
  { userId: string; credentials: SleeperCredentials }
>('agent/saveCredentials', async ({ userId, credentials }) => {
  const response = await fetch(`${API_URL}/api/v1/browser/credentials`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      ...credentials,
    }),
  });
  return response.json();
});

export const getCredentials = createAsyncThunk<CredentialsResponse, string>(
  'agent/getCredentials',
  async (userId: string) => {
    const response = await fetch(`${API_URL}/api/v1/browser/credentials/${userId}`);
    return response.json();
  }
);

export const deleteCredentials = createAsyncThunk<void, string>(
  'agent/deleteCredentials',
  async (userId: string) => {
    await fetch(`${API_URL}/api/v1/browser/credentials/${userId}`, {
      method: 'DELETE',
    });
  }
);

// Slice
const agentSlice = createSlice({
  name: 'agent',
  initialState,
  reducers: {
    // Status management
    setStatus: (state, action: PayloadAction<AgentStatus>) => {
      state.status = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      if (action.payload) {
        state.status = 'error';
      }
    },
    clearError: (state) => {
      state.error = null;
      if (state.status === 'error') {
        state.status = 'idle';
      }
    },

    // Autopilot
    setAutopilot: (state, action: PayloadAction<boolean>) => {
      state.autopilot = action.payload;
    },

    // Thread ID
    setThreadId: (state, action: PayloadAction<string>) => {
      state.threadId = action.payload;
    },

    // Steps management
    addStep: (state, action: PayloadAction<Omit<Step, 'id' | 'timestamp'>>) => {
      const step: Step = {
        ...action.payload,
        id: `step_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      };
      state.steps.push(step);
      state.currentStep = step.label;
    },

    updateStep: (state, action: PayloadAction<{ id: string; updates: Partial<Step> }>) => {
      const step = state.steps.find((s) => s.id === action.payload.id);
      if (step) {
        Object.assign(step, action.payload.updates);
        if (action.payload.updates.status === 'active') {
          state.currentStep = step.label;
        }
      }
    },

    updateStepByLabel: (
      state,
      action: PayloadAction<{ label: string; updates: Partial<Step> }>
    ) => {
      const step = state.steps.find((s) => s.label === action.payload.label);
      if (step) {
        Object.assign(step, action.payload.updates);
        if (action.payload.updates.status === 'active') {
          state.currentStep = step.label;
        }
      }
    },

    clearSteps: (state) => {
      state.steps = [];
      state.currentStep = null;
    },

    // Tool calls management
    addToolCall: (state, action: PayloadAction<Omit<ToolCall, 'id' | 'timestamp'>>) => {
      const toolCall: ToolCall = {
        ...action.payload,
        id: action.payload.id || `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      };
      state.toolCalls.push(toolCall);
    },

    updateToolCall: (
      state,
      action: PayloadAction<{ id: string; updates: Partial<ToolCall> }>
    ) => {
      const toolCall = state.toolCalls.find((tc) => tc.id === action.payload.id);
      if (toolCall) {
        Object.assign(toolCall, action.payload.updates);
      }
    },

    clearToolCalls: (state) => {
      state.toolCalls = [];
    },

    // Screenshots management
    addScreenshot: (state, action: PayloadAction<Omit<Screenshot, 'id' | 'timestamp'>>) => {
      const screenshot: Screenshot = {
        ...action.payload,
        id: `screenshot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      };
      state.screenshots.push(screenshot);
    },

    clearScreenshots: (state) => {
      state.screenshots = [];
    },

    // Reset agent state
    resetAgent: (state) => {
      state.status = 'idle';
      state.currentStep = null;
      state.steps = [];
      state.toolCalls = [];
      state.screenshots = [];
      state.error = null;
      // Keep threadId and browserSessionId
    },

    // Complete reset
    completeReset: () => initialState,
  },

  extraReducers: (builder) => {
    // Start browser session
    builder.addCase(startBrowserSession.pending, (state) => {
      state.status = 'running';
      state.error = null;
    });
    builder.addCase(startBrowserSession.fulfilled, (state, action) => {
      if (action.payload.success && action.payload.session_id) {
        state.browserSessionId = action.payload.session_id;
        state.status = 'idle';
      } else {
        state.error = action.payload.error || 'Failed to start browser session';
        state.status = 'error';
      }
    });
    builder.addCase(startBrowserSession.rejected, (state, action) => {
      state.error = action.error.message || 'Failed to start browser session';
      state.status = 'error';
    });

    // Stop browser session
    builder.addCase(stopBrowserSession.fulfilled, (state) => {
      state.browserSessionId = null;
      state.status = 'idle';
    });

    // Save credentials
    builder.addCase(saveCredentials.fulfilled, (state, action) => {
      if (!action.payload.success) {
        state.error = action.payload.error || 'Failed to save credentials';
      }
    });

    // Delete credentials
    builder.addCase(deleteCredentials.fulfilled, (state) => {
      // Credentials deleted successfully
    });
  },
});

export const {
  setStatus,
  setError,
  clearError,
  setAutopilot,
  setThreadId,
  addStep,
  updateStep,
  updateStepByLabel,
  clearSteps,
  addToolCall,
  updateToolCall,
  clearToolCalls,
  addScreenshot,
  clearScreenshots,
  resetAgent,
  completeReset,
} = agentSlice.actions;

export default agentSlice.reducer;
