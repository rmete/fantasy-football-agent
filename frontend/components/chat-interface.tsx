'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Send, Bot, User, Maximize2 } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { TypewriterStatus } from '@/components/typewriter-status';
import { ChatFullscreenModal } from '@/components/chat-fullscreen-modal';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setChatContext, fetchConversations } from '@/store/slices/conversationSlice';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  leagueId: string;
  rosterId: number;
  week?: number;
}

export function ChatInterface({ leagueId, rosterId, week }: ChatInterfaceProps) {
  const dispatch = useAppDispatch();
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Get AI settings from Redux
  const selectedModel = useAppSelector((state) => state.settings.selectedModel);
  const temperature = useAppSelector((state) => state.settings.temperature);

  // Get conversation state from Redux
  const currentThreadId = useAppSelector((state) => state.conversation.currentThreadId);
  const currentConversation = useAppSelector((state) => state.conversation.currentConversation);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        "Hi! I'm your fantasy football AI assistant. I can search the web, analyze matchups, and help you make lineup decisions. What would you like to know?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Store chat context when props change
  useEffect(() => {
    dispatch(
      setChatContext({
        league_id: leagueId,
        roster_id: rosterId,
        week: week || 0,
      })
    );
  }, [dispatch, leagueId, rosterId, week]);

  // Load conversation messages when conversation is selected
  useEffect(() => {
    if (currentConversation?.messages) {
      // Convert conversation messages to UI message format
      const loadedMessages: Message[] = currentConversation.messages.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at),
      }));

      setMessages(loadedMessages);
    } else {
      // Reset to initial greeting when no conversation is loaded
      setMessages([
        {
          id: '1',
          role: 'assistant',
          content:
            "Hi! I'm your fantasy football AI assistant. I can search the web, analyze matchups, and help you make lineup decisions. What would you like to know?",
          timestamp: new Date(),
        },
      ]);
    }
  }, [currentConversation]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, agentStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setAgentStatus('Connecting to agent...');

    try {
      // Use streaming endpoint with thread_id for conversation persistence
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_URL}/api/v1/agents/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          league_id: leagueId,
          roster_id: rosterId,
          week: week || null,
          thread_id: currentThreadId, // Send thread_id for conversation tracking
          model: selectedModel,
          temperature: temperature,
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

      let assistantResponse = '';
      let isNewConversation = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'status') {
                // Update agent status with typewriter effect
                setAgentStatus(data.message);
              } else if (data.type === 'response') {
                // Final response
                assistantResponse = data.message;
                setAgentStatus(null);
              } else if (data.type === 'metadata') {
                // Handle conversation metadata
                if (data.is_new_conversation) {
                  isNewConversation = true;
                }
              } else if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'done') {
                // Stream complete
                break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      // Add assistant message
      if (assistantResponse) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: assistantResponse,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }

      // Refresh conversation list if this was a new conversation
      if (isNewConversation) {
        dispatch(fetchConversations());
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setAgentStatus(null);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const suggestedQuestions = [
    'Search for best waiver wire pickups',
    'Which players have the best matchups?',
    'Who should I start this week?',
    'Any injury concerns on my roster?',
  ];

  return (
    <React.Fragment>
      <Card className="flex flex-col h-[600px] shadow-sm">
        <CardHeader className="border-b bg-gradient-to-r from-primary/5 to-primary/10 py-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              Lineup Assistant
            </CardTitle>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsFullscreen(true)}
              className="h-7 px-2"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
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

        {/* Agent status with typewriter effect */}
        {agentStatus && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-4 w-4 text-primary" />
              </div>
            </div>
            <div className="max-w-[80%] rounded-lg p-3 bg-muted">
              <TypewriterStatus text={agentStatus} speed={20} />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </CardContent>

      {/* Suggested questions */}
      {messages.length === 1 && !isLoading && (
        <div className="px-4 pb-3 border-t bg-muted/30">
          <p className="text-[10px] font-medium text-muted-foreground mb-2 mt-3">
            QUICK ACTIONS
          </p>
          <div className="grid grid-cols-2 gap-2">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => setInput(question)}
                className="text-xs px-3 py-2 rounded-lg bg-background border hover:border-primary/50 hover:bg-primary/5 transition-all text-left font-medium shadow-sm"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="border-t p-4 bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your lineup, search for players, analyze matchups..."
            className="min-h-[60px] resize-none focus-visible:ring-1"
            disabled={isLoading}
          />
          <Button
            type="submit"
            size="icon"
            disabled={isLoading || !input.trim()}
            className="h-[60px] w-[60px]"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </form>
      </div>
    </Card>

    <ChatFullscreenModal
      isOpen={isFullscreen}
      onClose={() => setIsFullscreen(false)}
      leagueId={leagueId}
      rosterId={rosterId}
      week={week}
    />
    </React.Fragment>
  );
}
