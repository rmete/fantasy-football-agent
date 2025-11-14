'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import {
  setStatus,
  setError,
  setAutopilot,
  setThreadId,
  addStep,
  updateStepByLabel,
  addToolCall,
  updateToolCall,
  addScreenshot,
  resetAgent,
} from '@/store/slices/agentSlice';
import { ControlPanel } from './control-panel';
import { ToolCallCard } from './tool-call-card';
import { StepTimeline } from './step-timeline';
import { ScreenshotStrip } from './screenshot-strip';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Bot, User } from 'lucide-react';
import type { AnyAgentEvent } from '@/types/agent';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AgentWindowProps {
  leagueId?: string;
  rosterId?: number;
  week?: number;
  onClose?: () => void;
}

export function AgentWindow({
  leagueId = '',
  rosterId = 0,
  week,
  onClose,
}: AgentWindowProps) {
  const dispatch = useAppDispatch();

  // Redux state
  const agentState = useAppSelector((state) => state.agent);
  const { status, autopilot, steps, toolCalls, screenshots, browserSessionId, threadId } =
    agentState;

  // Local state
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        "Hi! I'm your browser automation agent. I can log into Sleeper and manage your lineup. What would you like me to do?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, toolCalls]);

  // Handle SSE events
  const handleAgentEvent = (event: AnyAgentEvent) => {
    switch (event.type) {
      case 'status':
        if ('status' in event && event.status) {
          dispatch(setStatus(event.status));
        }
        break;

      case 'tool_call':
        if ('name' in event && 'args' in event) {
          dispatch(
            addToolCall({
              id: event.id,
              name: event.name,
              args: event.args,
              status: 'running',
            })
          );
        }
        break;

      case 'tool_result':
        if ('id' in event) {
          dispatch(
            updateToolCall({
              id: event.id,
              updates: {
                status: event.ok ? 'success' : 'error',
                result: event.data,
                error: event.error,
                duration: event.duration,
              },
            })
          );
        }
        break;

      case 'screenshot':
        if ('url' in event) {
          dispatch(
            addScreenshot({
              url: event.url,
              tag: event.tag,
            })
          );
        }
        break;

      case 'step':
        if ('label' in event) {
          const existingStep = steps.find((s) => s.label === event.label);
          if (existingStep) {
            dispatch(
              updateStepByLabel({
                label: event.label,
                updates: {
                  status: event.status || 'active',
                  note: event.note,
                },
              })
            );
          } else {
            dispatch(
              addStep({
                label: event.label,
                note: event.note,
                status: event.status || 'active',
              })
            );
          }
        }
        break;

      case 'response':
        if ('message' in event) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              role: 'assistant',
              content: event.message,
              timestamp: new Date(),
            },
          ]);
        }
        break;

      case 'metadata':
        if ('thread_id' in event && event.thread_id) {
          dispatch(setThreadId(event.thread_id));
        }
        break;

      case 'error':
        if ('message' in event) {
          dispatch(setError(event.message));
        }
        break;

      case 'done':
        dispatch(setStatus('idle'));
        setIsStreaming(false);
        break;
    }
  };

  // Send message
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    dispatch(setStatus('running'));

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_URL}/api/v1/agents/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          league_id: leagueId,
          roster_id: rosterId,
          week: week || null,
          thread_id: threadId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to connect to agent');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) as AnyAgentEvent;
              handleAgentEvent(data);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Agent error:', error);
      dispatch(setError(error instanceof Error ? error.message : 'Unknown error'));
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      dispatch(setStatus('idle'));
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleReset = () => {
    dispatch(resetAgent());
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content:
          "Hi! I'm your browser automation agent. I can log into Sleeper and manage your lineup. What would you like me to do?",
        timestamp: new Date(),
      },
    ]);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Control Panel */}
      <ControlPanel
        status={status}
        autopilot={autopilot}
        sessionId={browserSessionId}
        onRun={() => dispatch(setStatus('running'))}
        onStop={() => {
          dispatch(setStatus('idle'));
          setIsStreaming(false);
        }}
        onPause={() => dispatch(setStatus('paused'))}
        onAutopilotChange={(enabled) => dispatch(setAutopilot(enabled))}
        onClose={onClose}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0">
        {/* Left Panel: Chat + Tool Cards */}
        <div className="w-2/5 border-r flex flex-col min-h-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                )}

                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>

                {message.role === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                      <User className="h-4 w-4 text-primary-foreground" />
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Tool Call Cards */}
            {toolCalls.length > 0 && (
              <div className="space-y-3 mt-4">
                <h3 className="text-xs font-semibold text-muted-foreground">Tool Executions</h3>
                {toolCalls.map((toolCall) => (
                  <ToolCallCard key={toolCall.id} toolCall={toolCall} />
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Right Panel: Steps + Screenshots */}
        <div className="w-3/5 flex flex-col min-h-0">
          {/* Step Timeline */}
          <div className="flex-1 border-b overflow-hidden">
            <div className="h-full flex flex-col">
              <div className="px-4 py-2 border-b bg-muted/30">
                <h3 className="text-sm font-semibold">Progress</h3>
              </div>
              <StepTimeline steps={steps} />
            </div>
          </div>

          {/* Screenshot Strip */}
          <div className="h-48 border-t">
            <div className="h-full flex flex-col">
              <div className="px-4 py-2 border-b bg-muted/30">
                <h3 className="text-sm font-semibold">Screenshots</h3>
              </div>
              <div className="flex-1 overflow-hidden p-3">
                <ScreenshotStrip screenshots={screenshots} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t p-4 bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the agent to manage your lineup, login to Sleeper, or execute browser actions..."
            className="min-h-[60px] resize-none"
            disabled={isStreaming}
          />
          <Button
            type="submit"
            size="icon"
            disabled={isStreaming || !input.trim()}
            className="h-[60px] w-[60px]"
          >
            <Send className="h-5 w-5" />
          </Button>
        </form>
      </div>
    </div>
  );
}
