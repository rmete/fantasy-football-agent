import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { apiClient } from '@/lib/api-client';
import { ConversationSummary, ConversationDetail } from '@/types/conversation';
import { v4 as uuidv4 } from 'uuid';

interface ConversationState {
  // List of conversations
  conversations: ConversationSummary[];
  conversationsLoading: boolean;
  conversationsError: string | null;

  // Current active conversation
  currentConversation: ConversationDetail | null;
  currentConversationLoading: boolean;
  currentConversationError: string | null;

  // Thread ID for current chat session
  currentThreadId: string;

  // Context for chat requests
  chatContext: {
    league_id: string;
    roster_id: number;
    week: number;
  } | null;
}

const initialState: ConversationState = {
  conversations: [],
  conversationsLoading: false,
  conversationsError: null,
  currentConversation: null,
  currentConversationLoading: false,
  currentConversationError: null,
  currentThreadId: uuidv4(),
  chatContext: null,
};

// Load initial state from localStorage
const loadInitialState = (): ConversationState => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('conversation-state');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Only restore thread ID and context, not conversations (they'll be fetched)
        return {
          ...initialState,
          currentThreadId: parsed.currentThreadId || uuidv4(),
          chatContext: parsed.chatContext || null,
        };
      }
    } catch (e) {
      console.error('Failed to load conversation state from localStorage', e);
    }
  }
  return initialState;
};

// Async thunks
export const fetchConversations = createAsyncThunk(
  'conversations/fetchAll',
  async (userId: string = 'default') => {
    const data = await apiClient.getConversations(userId);
    return data as ConversationSummary[];
  }
);

export const fetchConversation = createAsyncThunk(
  'conversations/fetchOne',
  async (conversationId: string) => {
    const data = await apiClient.getConversation(conversationId);
    return data as ConversationDetail;
  }
);

export const deleteConversation = createAsyncThunk(
  'conversations/delete',
  async (conversationId: string) => {
    await apiClient.deleteConversation(conversationId);
    return conversationId;
  }
);

export const updateConversationTitle = createAsyncThunk(
  'conversations/updateTitle',
  async ({ conversationId, title }: { conversationId: string; title: string }) => {
    await apiClient.updateConversationTitle(conversationId, title);
    return { conversationId, title };
  }
);

const conversationSlice = createSlice({
  name: 'conversation',
  initialState: loadInitialState(),
  reducers: {
    // Set chat context (league, roster, week)
    setChatContext: (
      state,
      action: PayloadAction<{ league_id: string; roster_id: number; week: number }>
    ) => {
      state.chatContext = action.payload;
      saveToLocalStorage(state);
    },

    // Start a new conversation
    startNewConversation: (state) => {
      state.currentThreadId = uuidv4();
      state.currentConversation = null;
      saveToLocalStorage(state);
    },

    // Load an existing conversation
    loadConversation: (state, action: PayloadAction<string>) => {
      // Set thread_id from the conversation we're loading
      const conversation = state.conversations.find((c) => c.id === action.payload);
      if (conversation) {
        state.currentThreadId = conversation.thread_id;
        saveToLocalStorage(state);
      }
    },

    // Clear current conversation
    clearCurrentConversation: (state) => {
      state.currentConversation = null;
      state.currentThreadId = uuidv4();
      saveToLocalStorage(state);
    },

    // Clear errors
    clearErrors: (state) => {
      state.conversationsError = null;
      state.currentConversationError = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch conversations
    builder.addCase(fetchConversations.pending, (state) => {
      state.conversationsLoading = true;
      state.conversationsError = null;
    });
    builder.addCase(fetchConversations.fulfilled, (state, action) => {
      state.conversationsLoading = false;
      state.conversations = action.payload;
    });
    builder.addCase(fetchConversations.rejected, (state, action) => {
      state.conversationsLoading = false;
      state.conversationsError = action.error.message || 'Failed to fetch conversations';
    });

    // Fetch single conversation
    builder.addCase(fetchConversation.pending, (state) => {
      state.currentConversationLoading = true;
      state.currentConversationError = null;
    });
    builder.addCase(fetchConversation.fulfilled, (state, action) => {
      state.currentConversationLoading = false;
      state.currentConversation = action.payload;
      state.currentThreadId = action.payload.thread_id;
      saveToLocalStorage(state);
    });
    builder.addCase(fetchConversation.rejected, (state, action) => {
      state.currentConversationLoading = false;
      state.currentConversationError = action.error.message || 'Failed to fetch conversation';
    });

    // Delete conversation
    builder.addCase(deleteConversation.fulfilled, (state, action) => {
      // Remove from list
      state.conversations = state.conversations.filter((c) => c.id !== action.payload);
      // Clear current if it was deleted
      if (state.currentConversation?.id === action.payload) {
        state.currentConversation = null;
        state.currentThreadId = uuidv4();
        saveToLocalStorage(state);
      }
    });

    // Update title
    builder.addCase(updateConversationTitle.fulfilled, (state, action) => {
      const { conversationId, title } = action.payload;
      // Update in list
      const conversation = state.conversations.find((c) => c.id === conversationId);
      if (conversation) {
        conversation.title = title;
      }
      // Update current if it matches
      if (state.currentConversation?.id === conversationId) {
        state.currentConversation.title = title;
      }
    });
  },
});

function saveToLocalStorage(state: ConversationState) {
  if (typeof window !== 'undefined') {
    // Only save thread ID and context, not full conversations
    const toSave = {
      currentThreadId: state.currentThreadId,
      chatContext: state.chatContext,
    };
    localStorage.setItem('conversation-state', JSON.stringify(toSave));
  }
}

export const {
  setChatContext,
  startNewConversation,
  loadConversation,
  clearCurrentConversation,
  clearErrors,
} = conversationSlice.actions;

export default conversationSlice.reducer;
