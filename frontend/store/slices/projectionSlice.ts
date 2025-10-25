import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export type ScoringFormat = 'PPR' | 'HALF_PPR' | 'STD';

interface ProjectionState {
  scoringFormat: ScoringFormat;
  selectedWeek: number | null;
}

const initialState: ProjectionState = {
  scoringFormat: 'PPR',
  selectedWeek: null, // null means use current week
};

// Load initial state from localStorage if available
const loadInitialState = (): ProjectionState => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('projection-preferences');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load projection preferences from localStorage', e);
    }
  }
  return initialState;
};

const projectionSlice = createSlice({
  name: 'projection',
  initialState: loadInitialState(),
  reducers: {
    setScoringFormat: (state, action: PayloadAction<ScoringFormat>) => {
      state.scoringFormat = action.payload;
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('projection-preferences', JSON.stringify(state));
      }
    },
    setSelectedWeek: (state, action: PayloadAction<number>) => {
      state.selectedWeek = action.payload;
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('projection-preferences', JSON.stringify(state));
      }
    },
    resetToCurrentWeek: (state) => {
      state.selectedWeek = null;
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('projection-preferences', JSON.stringify(state));
      }
    },
  },
});

export const { setScoringFormat, setSelectedWeek, resetToCurrentWeek } =
  projectionSlice.actions;

export default projectionSlice.reducer;
