'use client';

import React, { useEffect, useRef } from 'react';
import { CheckCircle2, ArrowRight, Circle, XCircle } from 'lucide-react';
import type { Step } from '@/types/agent';

interface StepTimelineProps {
  steps: Step[];
}

// Get step icon and color
const getStepStyles = (status: Step['status']) => {
  switch (status) {
    case 'completed':
      return {
        icon: CheckCircle2,
        iconColor: 'text-green-500',
        lineColor: 'bg-green-500',
        textColor: 'text-green-700 dark:text-green-300',
        bgColor: 'bg-green-50 dark:bg-green-950/30',
      };
    case 'active':
      return {
        icon: ArrowRight,
        iconColor: 'text-blue-500 animate-pulse',
        lineColor: 'bg-blue-500',
        textColor: 'text-blue-700 dark:text-blue-300',
        bgColor: 'bg-blue-50 dark:bg-blue-950/30',
      };
    case 'pending':
      return {
        icon: Circle,
        iconColor: 'text-gray-400',
        lineColor: 'bg-gray-300 dark:bg-gray-700',
        textColor: 'text-gray-500 dark:text-gray-400',
        bgColor: 'bg-transparent',
      };
    case 'error':
      return {
        icon: XCircle,
        iconColor: 'text-red-500',
        lineColor: 'bg-red-500',
        textColor: 'text-red-700 dark:text-red-300',
        bgColor: 'bg-red-50 dark:bg-red-950/30',
      };
  }
};

export function StepTimeline({ steps }: StepTimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeStepRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to active step
  useEffect(() => {
    if (activeStepRef.current && containerRef.current) {
      activeStepRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [steps]);

  if (steps.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No steps yet
      </div>
    );
  }

  return (
    <div ref={containerRef} className="overflow-y-auto h-full py-4 px-3">
      <div className="relative">
        {steps.map((step, index) => {
          const styles = getStepStyles(step.status);
          const Icon = styles.icon;
          const isLast = index === steps.length - 1;
          const isActive = step.status === 'active';

          return (
            <div
              key={step.id}
              ref={isActive ? activeStepRef : null}
              className="relative pb-6 last:pb-0"
            >
              {/* Vertical Line */}
              {!isLast && (
                <div className="absolute left-3 top-6 bottom-0 w-0.5 -ml-px">
                  <div className={`h-full ${styles.lineColor} transition-all duration-300`} />
                </div>
              )}

              {/* Step Content */}
              <div className="relative flex items-start gap-3">
                {/* Icon */}
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${styles.iconColor} transition-all duration-300`}
                >
                  <Icon className="h-4 w-4" />
                </div>

                {/* Content */}
                <div className={`flex-1 min-w-0 ${styles.bgColor} rounded-lg p-2 -mt-0.5 transition-all duration-300`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4 className={`text-sm font-medium ${styles.textColor} transition-colors duration-300`}>
                        {step.label}
                      </h4>
                      {step.note && (
                        <p className="text-xs text-muted-foreground mt-0.5">{step.note}</p>
                      )}
                    </div>

                    {/* Timestamp */}
                    {step.timestamp && (
                      <span className="text-xs text-muted-foreground flex-shrink-0">
                        {new Date(step.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
