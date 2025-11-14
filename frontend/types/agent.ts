/**
 * TypeScript types for Agent Window and Browser Automation
 */

// Agent execution status
export type AgentStatus = 'idle' | 'running' | 'paused' | 'error';

// Tool call status
export type ToolCallStatus = 'pending' | 'running' | 'success' | 'error';

// Step status
export type StepStatus = 'pending' | 'active' | 'completed' | 'error';

// Tool call interface
export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, any>;
  status: ToolCallStatus;
  result?: any;
  error?: string;
  duration?: number;
  timestamp: Date;
}

// Screenshot interface
export interface Screenshot {
  id: string;
  url: string;
  tag?: string;
  timestamp: Date;
  filename?: string;
}

// Step interface
export interface Step {
  id: string;
  label: string;
  note?: string;
  status: StepStatus;
  timestamp: Date;
}

// Agent state interface
export interface AgentState {
  status: AgentStatus;
  autopilot: boolean;
  currentStep: string | null;
  steps: Step[];
  toolCalls: ToolCall[];
  screenshots: Screenshot[];
  browserSessionId: string | null;
  error: string | null;
  threadId: string | null;
}

// Browser session interface
export interface BrowserSession {
  session_id: string;
  user_id: string;
  created_at: string;
  last_activity: string;
  is_active: boolean;
  age_minutes: number;
}

// Credentials interface
export interface SleeperCredentials {
  email: string;
  password: string;
  use_sso: boolean;
}

// Agent event types (for WebSocket/SSE)
export type AgentEventType =
  | 'status'
  | 'generation'
  | 'tool_call'
  | 'tool_result'
  | 'screenshot'
  | 'step'
  | 'confirmation_required'
  | 'response'
  | 'metadata'
  | 'error'
  | 'done';

// Base agent event
export interface AgentEvent {
  type: AgentEventType;
  timestamp?: string;
}

// Specific event interfaces
export interface StatusEvent extends AgentEvent {
  type: 'status';
  status: AgentStatus;
  message?: string;
}

export interface GenerationEvent extends AgentEvent {
  type: 'generation';
  role: 'user' | 'assistant';
  text: string;
}

export interface ToolCallEvent extends AgentEvent {
  type: 'tool_call';
  id: string;
  name: string;
  args: Record<string, any>;
}

export interface ToolResultEvent extends AgentEvent {
  type: 'tool_result';
  id: string;
  ok: boolean;
  data?: any;
  error?: string;
  duration?: number;
}

export interface ScreenshotEvent extends AgentEvent {
  type: 'screenshot';
  url: string;
  tag?: string;
}

export interface StepEvent extends AgentEvent {
  type: 'step';
  label: string;
  note?: string;
  status?: StepStatus;
}

export interface ConfirmationEvent extends AgentEvent {
  type: 'confirmation_required';
  action: any;
  reason: string;
}

export interface ResponseEvent extends AgentEvent {
  type: 'response';
  message: string;
}

export interface MetadataEvent extends AgentEvent {
  type: 'metadata';
  thread_id?: string;
  conversation_id?: string;
  is_new_conversation?: boolean;
  [key: string]: any;
}

export interface ErrorEvent extends AgentEvent {
  type: 'error';
  message: string;
  details?: any;
}

export interface DoneEvent extends AgentEvent {
  type: 'done';
}

// Union type of all events
export type AnyAgentEvent =
  | StatusEvent
  | GenerationEvent
  | ToolCallEvent
  | ToolResultEvent
  | ScreenshotEvent
  | StepEvent
  | ConfirmationEvent
  | ResponseEvent
  | MetadataEvent
  | ErrorEvent
  | DoneEvent;

// Client message types (sent to server)
export type ClientMessageType = 'user_message' | 'control' | 'autopilot' | 'confirm';

export interface ClientMessage {
  type: ClientMessageType;
  timestamp?: string;
}

export interface UserMessage extends ClientMessage {
  type: 'user_message';
  message: string;
  thread_id?: string;
  league_id?: string;
  roster_id?: number;
  week?: number;
}

export interface ControlMessage extends ClientMessage {
  type: 'control';
  action: 'stop' | 'pause' | 'resume';
}

export interface AutopilotMessage extends ClientMessage {
  type: 'autopilot';
  enabled: boolean;
}

export interface ConfirmMessage extends ClientMessage {
  type: 'confirm';
  confirmed: boolean;
  action_id?: string;
}

// Union type of all client messages
export type AnyClientMessage = UserMessage | ControlMessage | AutopilotMessage | ConfirmMessage;

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  error?: string;
  data?: T;
}

export interface SessionResponse extends ApiResponse {
  session_id?: string;
}

export interface CredentialsResponse extends ApiResponse {
  email?: string;
  use_sso?: boolean;
  has_password?: boolean;
}

export interface ScreenshotsResponse extends ApiResponse {
  thread_id?: string;
  count?: number;
  screenshots?: Screenshot[];
}
