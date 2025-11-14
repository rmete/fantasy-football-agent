'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Play, Square, Pause, X, Zap } from 'lucide-react';
import { AgentStatusBadge } from './agent-status-badge';
import type { AgentStatus } from '@/types/agent';

interface ControlPanelProps {
  status: AgentStatus;
  autopilot: boolean;
  sessionId: string | null;
  onRun?: () => void;
  onStop?: () => void;
  onPause?: () => void;
  onAutopilotChange?: (enabled: boolean) => void;
  onClose?: () => void;
}

export function ControlPanel({
  status,
  autopilot,
  sessionId,
  onRun,
  onStop,
  onPause,
  onAutopilotChange,
  onClose,
}: ControlPanelProps) {
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isIdle = status === 'idle';

  return (
    <div className="border-b bg-gradient-to-r from-primary/5 to-primary/10 px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        {/* Left: Status & Session */}
        <div className="flex items-center gap-3">
          <AgentStatusBadge status={status} />

          {sessionId && (
            <div className="text-xs text-muted-foreground hidden sm:block">
              Session: {sessionId.slice(0, 8)}...
            </div>
          )}
        </div>

        {/* Center: Controls */}
        <div className="flex items-center gap-2">
          {/* Run Button */}
          {(isIdle || isPaused) && (
            <Button
              size="sm"
              variant="default"
              onClick={onRun}
              disabled={!sessionId}
              className="h-8"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              {isPaused ? 'Resume' : 'Run'}
            </Button>
          )}

          {/* Pause Button */}
          {isRunning && (
            <Button
              size="sm"
              variant="outline"
              onClick={onPause}
              className="h-8"
            >
              <Pause className="h-3.5 w-3.5 mr-1.5" />
              Pause
            </Button>
          )}

          {/* Stop Button */}
          {(isRunning || isPaused) && (
            <Button
              size="sm"
              variant="destructive"
              onClick={onStop}
              className="h-8"
            >
              <Square className="h-3.5 w-3.5 mr-1.5" />
              Stop
            </Button>
          )}

          {/* Autopilot Toggle */}
          <div className="flex items-center gap-2 ml-2 pl-2 border-l">
            <Switch
              id="autopilot"
              checked={autopilot}
              onCheckedChange={onAutopilotChange}
              disabled={isRunning}
            />
            <Label
              htmlFor="autopilot"
              className="text-xs font-medium cursor-pointer flex items-center gap-1"
            >
              <Zap className="h-3 w-3" />
              Autopilot
            </Label>
          </div>
        </div>

        {/* Right: Close Button */}
        <Button
          size="sm"
          variant="ghost"
          onClick={onClose}
          className="h-8 w-8 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Autopilot Info */}
      {autopilot && (
        <div className="mt-2 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 px-3 py-1.5 rounded-md flex items-center gap-2">
          <Zap className="h-3 w-3" />
          <span>
            Autopilot enabled: Agent will execute actions without confirmation
          </span>
        </div>
      )}
    </div>
  );
}
