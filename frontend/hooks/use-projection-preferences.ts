import { useState, useEffect } from 'react';

export type ScoringFormat = 'PPR' | 'HALF_PPR' | 'STD';

interface ProjectionPreferences {
  scoringFormat: ScoringFormat;
  selectedWeek: number | null;
}

const STORAGE_KEY = 'projection-preferences';

export function useProjectionPreferences(currentWeek: number = 1) {
  const [scoringFormat, setScoringFormat] = useState<ScoringFormat>('PPR');
  const [selectedWeek, setSelectedWeek] = useState<number>(currentWeek);

  // Load preferences from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          const prefs: ProjectionPreferences = JSON.parse(stored);
          setScoringFormat(prefs.scoringFormat);
          // Use stored week if available, otherwise use current week
          if (prefs.selectedWeek) {
            setSelectedWeek(prefs.selectedWeek);
          } else {
            setSelectedWeek(currentWeek);
          }
        } catch (e) {
          console.error('Failed to load projection preferences', e);
        }
      } else {
        setSelectedWeek(currentWeek);
      }
    }
  }, [currentWeek]);

  // Save preferences to localStorage when they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const prefs: ProjectionPreferences = {
        scoringFormat,
        selectedWeek,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    }
  }, [scoringFormat, selectedWeek]);

  return {
    scoringFormat,
    setScoringFormat,
    selectedWeek,
    setSelectedWeek,
  };
}
