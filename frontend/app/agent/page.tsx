'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { startBrowserSession, stopBrowserSession } from '@/store/slices/agentSlice';
import { AgentWindow } from '@/components/agent-window';
import { Loader2 } from 'lucide-react';

export default function AgentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const dispatch = useAppDispatch();

  // Get URL params
  const leagueId = searchParams.get('league_id') || '';
  const rosterId = parseInt(searchParams.get('roster_id') || '0');
  const week = searchParams.get('week') ? parseInt(searchParams.get('week')!) : undefined;

  // Redux state
  const { browserSessionId, status } = useAppSelector((state) => state.agent);

  // Local loading state
  const [isInitializing, setIsInitializing] = useState(true);

  // Start browser session on mount
  useEffect(() => {
    const initSession = async () => {
      if (!browserSessionId) {
        try {
          setIsInitializing(true);
          await dispatch(startBrowserSession('default')).unwrap();
        } catch (error) {
          console.error('Failed to start browser session:', error);
        } finally {
          setIsInitializing(false);
        }
      } else {
        setIsInitializing(false);
      }
    };

    initSession();

    // Cleanup on unmount
    return () => {
      if (browserSessionId) {
        dispatch(stopBrowserSession(browserSessionId));
      }
    };
  }, []);

  const handleClose = () => {
    router.push('/');
  };

  if (isInitializing) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          <div>
            <h2 className="text-lg font-semibold mb-1">Initializing Agent</h2>
            <p className="text-sm text-muted-foreground">Starting browser session...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden">
      <AgentWindow
        leagueId={leagueId}
        rosterId={rosterId}
        week={week}
        onClose={handleClose}
      />
    </div>
  );
}
