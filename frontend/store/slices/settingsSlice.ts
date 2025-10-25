import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type LLMProvider = 'anthropic' | 'openai' | 'gemini';

export type ClaudeModel =
  | 'claude-3-5-sonnet-20241022'
  | 'claude-3-5-haiku-20241022'
  | 'claude-3-opus-20240229';

export type OpenAIModel = 'gpt-4o' | 'gpt-4o-mini' | 'gpt-4-turbo';

export type GeminiModel = 'gemini-1.5-pro' | 'gemini-1.5-flash';

export type AIModel = ClaudeModel | OpenAIModel | GeminiModel;

interface SettingsState {
  // User preferences
  sleeperUsername: string;
  defaultScoringFormat: 'PPR' | 'HALF_PPR' | 'STD';

  // AI/LLM settings
  llmProvider: LLMProvider;
  selectedModel: AIModel;
  temperature: number; // 0.0 - 1.0

  // UI preferences
  theme: 'light' | 'dark' | 'system';
  enableNotifications: boolean;
}

const initialState: SettingsState = {
  sleeperUsername: process.env.NEXT_PUBLIC_SLEEPER_USERNAME || 'rmete',
  defaultScoringFormat: 'PPR',
  llmProvider: 'anthropic',
  selectedModel: 'claude-3-5-haiku-20241022',
  temperature: 0.7,
  theme: 'system',
  enableNotifications: true,
};

// Load initial state from localStorage
const loadInitialState = (): SettingsState => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('app-settings');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge with defaults to handle new settings
        return { ...initialState, ...parsed };
      }
    } catch (e) {
      console.error('Failed to load app settings from localStorage', e);
    }
  }
  return initialState;
};

const settingsSlice = createSlice({
  name: 'settings',
  initialState: loadInitialState(),
  reducers: {
    setSleeperUsername: (state, action: PayloadAction<string>) => {
      state.sleeperUsername = action.payload;
      saveToLocalStorage(state);
    },
    setDefaultScoringFormat: (
      state,
      action: PayloadAction<'PPR' | 'HALF_PPR' | 'STD'>
    ) => {
      state.defaultScoringFormat = action.payload;
      saveToLocalStorage(state);
    },
    setLLMProvider: (state, action: PayloadAction<LLMProvider>) => {
      state.llmProvider = action.payload;
      // Auto-select appropriate default model for provider
      if (action.payload === 'anthropic') {
        state.selectedModel = 'claude-3-5-haiku-20241022';
      } else if (action.payload === 'openai') {
        state.selectedModel = 'gpt-4o-mini';
      } else if (action.payload === 'gemini') {
        state.selectedModel = 'gemini-1.5-flash';
      }
      saveToLocalStorage(state);
    },
    setSelectedModel: (state, action: PayloadAction<AIModel>) => {
      state.selectedModel = action.payload;
      saveToLocalStorage(state);
    },
    setTemperature: (state, action: PayloadAction<number>) => {
      state.temperature = Math.max(0, Math.min(1, action.payload)); // Clamp 0-1
      saveToLocalStorage(state);
    },
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'system'>) => {
      state.theme = action.payload;
      saveToLocalStorage(state);
    },
    setEnableNotifications: (state, action: PayloadAction<boolean>) => {
      state.enableNotifications = action.payload;
      saveToLocalStorage(state);
    },
    resetSettings: (state) => {
      Object.assign(state, initialState);
      saveToLocalStorage(state);
    },
  },
});

function saveToLocalStorage(state: SettingsState) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('app-settings', JSON.stringify(state));
  }
}

export const {
  setSleeperUsername,
  setDefaultScoringFormat,
  setLLMProvider,
  setSelectedModel,
  setTemperature,
  setTheme,
  setEnableNotifications,
  resetSettings,
} = settingsSlice.actions;

export default settingsSlice.reducer;
