'use client';

import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchConversations,
  fetchConversation,
  deleteConversation,
  startNewConversation,
  loadConversation,
} from '@/store/slices/conversationSlice';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { MessageSquare, Trash2, Plus, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface ConversationSidebarProps {
  onConversationSelect?: (conversationId: string) => void;
  onNewConversation?: () => void;
}

export function ConversationSidebar({
  onConversationSelect,
  onNewConversation,
}: ConversationSidebarProps) {
  const dispatch = useAppDispatch();
  const {
    conversations,
    conversationsLoading,
    conversationsError,
    currentConversation,
    currentThreadId,
  } = useAppSelector((state) => state.conversation);

  // Fetch conversations on mount
  useEffect(() => {
    dispatch(fetchConversations());
  }, [dispatch]);

  const handleNewConversation = () => {
    dispatch(startNewConversation());
    onNewConversation?.();
  };

  const handleSelectConversation = async (conversationId: string) => {
    try {
      // Load the conversation thread_id into state
      dispatch(loadConversation(conversationId));

      // Fetch full conversation details
      await dispatch(fetchConversation(conversationId)).unwrap();

      // Notify parent component
      onConversationSelect?.(conversationId);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering conversation select

    if (confirm('Are you sure you want to delete this conversation?')) {
      try {
        await dispatch(deleteConversation(conversationId)).unwrap();
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  return (
    <Card className="h-full flex flex-col shadow-sm">
      <CardHeader className="pb-3 border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2 font-semibold">
            <MessageSquare className="h-4 w-4" />
            Conversations
          </CardTitle>
          <Button
            size="sm"
            onClick={handleNewConversation}
            className="h-7 px-2 text-xs"
          >
            <Plus className="h-3 w-3 mr-1" />
            New
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 overflow-hidden">
        {conversationsError && (
          <div className="px-4 py-2 text-sm text-red-500">
            {conversationsError}
          </div>
        )}

        {conversationsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No conversations yet.
            <br />
            Start chatting to create one!
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <div className="p-2 space-y-1">
              {conversations.map((conversation) => {
                const isActive = currentConversation?.id === conversation.id;

                return (
                  <div
                    key={conversation.id}
                    className={`
                      group relative rounded-md border p-2.5 cursor-pointer
                      transition-all duration-150 ease-in-out
                      ${
                        isActive
                          ? 'bg-primary/5 border-primary/20 shadow-sm'
                          : 'border-transparent hover:bg-accent/50 hover:border-border'
                      }
                    `}
                    onClick={() => handleSelectConversation(conversation.id)}
                  >
                    {/* Title and delete button */}
                    <div className="flex items-start justify-between gap-1.5 mb-1.5">
                      <h4 className="text-xs font-semibold line-clamp-2 flex-1 leading-tight">
                        {conversation.title}
                      </h4>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                        onClick={(e) => handleDeleteConversation(conversation.id, e)}
                      >
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <MessageSquare className="h-2.5 w-2.5" />
                        {conversation.message_count}
                      </span>
                      <span>•</span>
                      <span className="truncate">
                        {formatDistanceToNow(new Date(conversation.updated_at), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
