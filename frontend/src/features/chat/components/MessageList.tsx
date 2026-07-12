import { useEffect } from 'react'

import { useChatScroll } from '@/hooks/useChatScroll'

import type { ActiveStream } from '../types/streaming'
import { getMessagesForDisplay } from '../types/streaming'
import type { Message } from '../types'
import MessageBubble from './MessageBubble'
import MessageListSkeleton from './MessageListSkeleton'
import StreamingAssistantBubble from './StreamingAssistantBubble'

export interface MessageListProps {
  conversationId: string
  messages: Message[]
  isLoading: boolean
  activeStream?: ActiveStream | null
  onStreamComplete?: () => void
}

export default function MessageList({
  conversationId,
  messages,
  isLoading,
  activeStream = null,
  onStreamComplete,
}: MessageListProps) {
  const visibleMessages = getMessagesForDisplay(messages, activeStream)
  const { containerRef, handleScroll, scrollIfNearBottom, ensureInitialScroll } =
    useChatScroll(conversationId)

  useEffect(() => {
    scrollIfNearBottom('smooth')
  }, [messages.length, activeStream?.content, scrollIfNearBottom])

  useEffect(() => {
    if (!isLoading) {
      ensureInitialScroll()
    }
  }, [conversationId, isLoading, messages.length, ensureInitialScroll])

  if (isLoading && !activeStream) {
    return (
      <div className="flex min-h-0 flex-1 flex-col" role="status" aria-live="polite">
        <MessageListSkeleton />
        <span className="sr-only">Loading messages</span>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="scrollbar-thin flex min-h-0 flex-1 flex-col gap-8 overflow-y-auto px-4 py-6 sm:px-6"
      role="log"
      aria-label="Conversation messages"
      aria-live="polite"
    >
      {visibleMessages.map((message, index) => (
        <MessageBubble
          key={message.id}
          message={message}
          animationDelayMs={Math.min(index * 40, 200)}
        />
      ))}

      {activeStream && onStreamComplete && (
        <StreamingAssistantBubble stream={activeStream} onComplete={onStreamComplete} />
      )}
    </div>
  )
}
