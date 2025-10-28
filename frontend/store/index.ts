import { configureStore } from '@reduxjs/toolkit';
import projectionReducer from './slices/projectionSlice';
import settingsReducer from './slices/settingsSlice';
import conversationReducer from './slices/conversationSlice';

export const store = configureStore({
  reducer: {
    projection: projectionReducer,
    settings: settingsReducer,
    conversation: conversationReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
