'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Globe,
  MousePointer,
  Type,
  Keyboard,
  Clock,
  Camera,
  Timer,
  LogIn,
  Navigation,
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Wrench,
} from 'lucide-react';
import type { ToolCall } from '@/types/agent';

interface ToolCallCardProps {
  toolCall: ToolCall;
}

// Map tool names to icons
const getToolIcon = (toolName: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    open_page: <Globe className="h-4 w-4" />,
    click_element: <MousePointer className="h-4 w-4" />,
    type_text: <Type className="h-4 w-4" />,
    press_key: <Keyboard className="h-4 w-4" />,
    wait_for_element: <Clock className="h-4 w-4" />,
    take_screenshot: <Camera className="h-4 w-4" />,
    sleep_ms: <Timer className="h-4 w-4" />,
    sleeper_login: <LogIn className="h-4 w-4" />,
    navigate_to_lineup: <Navigation className="h-4 w-4" />,
  };

  return iconMap[toolName] || <Wrench className="h-4 w-4" />;
};

// Get status color and icon
const getStatusStyles = (status: ToolCall['status']) => {
  switch (status) {
    case 'pending':
      return {
        bg: 'bg-gray-50 dark:bg-gray-900',
        border: 'border-gray-200 dark:border-gray-800',
        text: 'text-gray-600 dark:text-gray-400',
        badge: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
        icon: <Clock className="h-3 w-3" />,
      };
    case 'running':
      return {
        bg: 'bg-blue-50 dark:bg-blue-950',
        border: 'border-blue-200 dark:border-blue-800',
        text: 'text-blue-700 dark:text-blue-300',
        badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
      };
    case 'success':
      return {
        bg: 'bg-green-50 dark:bg-green-950',
        border: 'border-green-200 dark:border-green-800',
        text: 'text-green-700 dark:text-green-300',
        badge: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
        icon: <CheckCircle2 className="h-3 w-3" />,
      };
    case 'error':
      return {
        bg: 'bg-red-50 dark:bg-red-950',
        border: 'border-red-200 dark:border-red-800',
        text: 'text-red-700 dark:text-red-300',
        badge: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
        icon: <XCircle className="h-3 w-3" />,
      };
  }
};

// Format tool name for display
const formatToolName = (name: string): string => {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const styles = getStatusStyles(toolCall.status);

  // Format timestamp
  const timeStr = toolCall.timestamp
    ? new Date(toolCall.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '';

  return (
    <Card className={`${styles.bg} ${styles.border} border transition-all duration-200`}>
      <CardHeader className="py-3 px-4">
        <div className="flex items-start justify-between gap-3">
          {/* Left: Icon + Name */}
          <div className="flex items-center gap-2 min-w-0">
            <div className={`${styles.text} flex-shrink-0`}>{getToolIcon(toolCall.name)}</div>
            <div className="min-w-0">
              <h4 className={`text-sm font-semibold ${styles.text} truncate`}>
                {formatToolName(toolCall.name)}
              </h4>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-muted-foreground">{timeStr}</span>
                {toolCall.duration && (
                  <span className="text-xs text-muted-foreground">
                    • {toolCall.duration}ms
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right: Status Badge */}
          <Badge variant="secondary" className={`${styles.badge} flex items-center gap-1.5 flex-shrink-0`}>
            {styles.icon}
            <span className="text-xs capitalize">{toolCall.status}</span>
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="py-0 px-4 pb-3">
        {/* Args Preview (if not expanded) */}
        {!isExpanded && Object.keys(toolCall.args).length > 0 && (
          <div className="text-xs text-muted-foreground mb-2 truncate">
            Args: {Object.keys(toolCall.args).join(', ')}
          </div>
        )}

        {/* Error Message */}
        {toolCall.error && (
          <div className="bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-xs p-2 rounded mb-2">
            {toolCall.error}
          </div>
        )}

        {/* Result Preview (if success and not expanded) */}
        {!isExpanded && toolCall.status === 'success' && toolCall.result && (
          <div className="bg-muted/50 text-xs p-2 rounded mb-2 max-h-20 overflow-hidden">
            <pre className="truncate">
              {typeof toolCall.result === 'string'
                ? toolCall.result
                : JSON.stringify(toolCall.result, null, 2)}
            </pre>
          </div>
        )}

        {/* Expand/Collapse Button */}
        {(Object.keys(toolCall.args).length > 0 || toolCall.result) && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="h-3 w-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" />
                Show details
              </>
            )}
          </button>
        )}

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mt-3 space-y-3">
            {/* Arguments */}
            {Object.keys(toolCall.args).length > 0 && (
              <div>
                <h5 className="text-xs font-semibold text-muted-foreground mb-1.5">
                  Arguments:
                </h5>
                <div className="bg-muted/50 rounded p-2 max-h-40 overflow-auto">
                  <pre className="text-xs text-foreground/90">
                    {JSON.stringify(toolCall.args, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Result */}
            {toolCall.result && (
              <div>
                <h5 className="text-xs font-semibold text-muted-foreground mb-1.5">Result:</h5>
                <div className="bg-muted/50 rounded p-2 max-h-40 overflow-auto">
                  <pre className="text-xs text-foreground/90">
                    {typeof toolCall.result === 'string'
                      ? toolCall.result
                      : JSON.stringify(toolCall.result, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
