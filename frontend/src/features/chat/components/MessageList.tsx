import { useEffect, useRef } from 'react'

import Spinner from '@/components/ui/Spinner'

import type { ActiveStream } from '../types/streaming'
import { getMessagesForDisplay } from '../types/streaming'
import type { Message } from '../types'
import MessageBubble from './MessageBubble'
import StreamingAssistantBubble from './StreamingAssistantBubble'

export interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  activeStream?: ActiveStream | null
  onStreamComplete?: () => void
}

export default function MessageList({
  messages,
  isLoading,
  activeStream = null,
  onStreamComplete,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const visibleMessages = getMessagesForDisplay(messages, activeStream)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, activeStream?.content])

  if (isLoading && !activeStream) {
    return (
      <div className="flex flex-1 items-center justify-center" role="status" aria-live="polite">
        <Spinner size="md" label="Loading messages" />
      </div>
    )
  }

  return (
    <div
      className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4"
      role="log"
      aria-label="Conversation messages"
      aria-live="polite"
    >
      {visibleMessages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {activeStream && onStreamComplete && (
        <StreamingAssistantBubble stream={activeStream} onComplete={onStreamComplete} />
      )}

      <div ref={bottomRef} />
    </div>
  )
}
