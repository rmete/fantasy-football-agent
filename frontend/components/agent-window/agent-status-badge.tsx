'use client';

import React from 'react';
import { Badge } from '@/components/ui/badge';
import type { AgentStatus } from '@/types/agent';

interface AgentStatusBadgeProps {
  status: AgentStatus;
  className?: string;
}

const getStatusConfig = (status: AgentStatus) => {
  switch (status) {
    case 'idle':
      return {
        label: 'Idle',
        dotClass: 'bg-gray-400',
        badgeClass: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
        animate: false,
      };
    case 'running':
      return {
        label: 'Running',
        dotClass: 'bg-blue-500',
        badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
        animate: true,
      };
    case 'paused':
      return {
        label: 'Paused',
        dotClass: 'bg-orange-500',
        badgeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
        animate: false,
      };
    case 'error':
      return {
        label: 'Error',
        dotClass: 'bg-red-500',
        badgeClass: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
        animate: false,
      };
  }
};

export function AgentStatusBadge({ status, className = '' }: AgentStatusBadgeProps) {
  const config = getStatusConfig(status);

  return (
    <Badge variant="secondary" className={`${config.badgeClass} ${className}`}>
      <div className="flex items-center gap-1.5">
        {/* Dot Indicator */}
        <div className="relative">
          <div className={`w-2 h-2 rounded-full ${config.dotClass}`} />
          {/* Pulsing Ring for Running State */}
          {config.animate && (
            <div className="absolute inset-0 w-2 h-2 rounded-full bg-blue-500 animate-ping opacity-75" />
          )}
        </div>
        {/* Status Label */}
        <span className="text-xs font-medium">{config.label}</span>
      </div>
    </Badge>
  );
}
