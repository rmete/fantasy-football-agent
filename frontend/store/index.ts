import { configureStore } from '@reduxjs/toolkit';
import projectionReducer from './slices/projectionSlice';
import settingsReducer from './slices/settingsSlice';
import conversationReducer from './slices/conversationSlice';
import agentReducer from './slices/agentSlice';

export const store = configureStore({
  reducer: {
    projection: projectionReducer,
    settings: settingsReducer,
    conversation: conversationReducer,
    agent: agentReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
