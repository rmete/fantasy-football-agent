'use client';

import { useState, useRef, useEffect } from 'react';
import { Dialog, DialogContent, DialogClose } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ConversationSidebar } from '@/components/conversation-sidebar';
import { TypewriterStatus } from '@/components/typewriter-status';
import { MarkdownRenderer } from '@/components/markdown-renderer';
import { useAppSelector, useAppDispatch } from '@/store/hooks';
import { setChatContext, fetchConversations } from '@/store/slices/conversationSlice';
import { Loader2, Send, Bot, User, X, PanelLeftClose, PanelLeft } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatFullscreenModalProps {
  isOpen: boolean;
  onClose: () => void;
  leagueId: string;
  rosterId: number;
  week?: number;
}

export function ChatFullscreenModal({
  isOpen,
  onClose,
  leagueId,
  rosterId,
  week,
}: ChatFullscreenModalProps) {
  const dispatch = useAppDispatch();
  const [sidebarOpen, setSidebarOpen] = useState(true);

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
      const loadedMessages: Message[] = currentConversation.messages.map((msg) => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at),
      }));
      setMessages(loadedMessages);
    } else {
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

  // Auto-scroll when modal opens
  useEffect(() => {
    if (isOpen) {
      // Small delay to ensure DOM is rendered
      setTimeout(() => scrollToBottom(), 100);
    }
  }, [isOpen]);

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
          thread_id: currentThreadId,
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
                setAgentStatus(data.message);
              } else if (data.type === 'response') {
                assistantResponse = data.message;
                setAgentStatus(null);
              } else if (data.type === 'metadata') {
                if (data.is_new_conversation) {
                  isNewConversation = true;
                }
              } else if (data.type === 'error') {
                throw new Error(data.message);
              } else if (data.type === 'done') {
                break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      if (assistantResponse) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: assistantResponse,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }

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
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[95vw] h-[95vh] p-0 gap-0 overflow-hidden flex flex-col [&>button]:hidden">
        <div className="flex flex-1 min-h-0">
          {/* Collapsible Sidebar */}
          {sidebarOpen && (
            <div className="w-[300px] border-r flex-shrink-0 flex flex-col bg-muted/20 min-h-0">
              <div className="flex items-center justify-between p-3 border-b bg-background flex-shrink-0">
                <h3 className="text-sm font-semibold">Conversations</h3>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSidebarOpen(false)}
                  className="h-6 w-6 p-0"
                >
                  <PanelLeftClose className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex-1 min-h-0 overflow-hidden">
                <ConversationSidebar />
              </div>
            </div>
          )}

          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col bg-background min-h-0">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-primary/5 to-primary/10 flex-shrink-0">
              <div className="flex items-center gap-3">
                {!sidebarOpen && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setSidebarOpen(true)}
                    className="h-8 w-8 p-0"
                  >
                    <PanelLeft className="h-4 w-4" />
                  </Button>
                )}
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <h2 className="text-base font-semibold">Lineup Assistant</h2>
                </div>
              </div>
              <Button size="sm" variant="ghost" onClick={onClose} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
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
                    className={`max-w-[70%] rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    }`}
                  >
                    {message.role === 'assistant' ? (
                      <MarkdownRenderer content={message.content} className="text-sm" />
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}
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

              {agentStatus && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  </div>
                  <div className="max-w-[70%] rounded-lg p-3 bg-muted">
                    <TypewriterStatus text={agentStatus} speed={20} />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Questions */}
            {messages.length === 1 && !isLoading && (
              <div className="px-6 pb-3 border-t bg-muted/30 flex-shrink-0">
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

            {/* Input */}
            <div className="border-t p-4 bg-background flex-shrink-0">
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
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
