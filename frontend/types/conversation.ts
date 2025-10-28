export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: string[];
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_preview: string;
}

export interface ConversationDetail {
  id: string;
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  league_id?: string;
  extra_data: Record<string, any>;
  messages: ConversationMessage[];
}

export interface ChatStreamEvent {
  type: 'status' | 'response' | 'metadata' | 'error' | 'done';
  message?: string;
  thread_id?: string;
  conversation_id?: string;
  is_new_conversation?: boolean;
}
