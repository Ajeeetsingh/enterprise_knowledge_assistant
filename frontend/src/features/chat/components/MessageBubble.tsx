import { MarkdownRenderer } from '@/components/chat'

import type { Message } from '../types'
import AiMessageLayout from './AiMessageLayout'
import AssistantMessagePresentation from './AssistantMessagePresentation'

export interface MessageBubbleProps {
  message: Message
  animationDelayMs?: number
}

export default function MessageBubble({ message, animationDelayMs = 0 }: MessageBubbleProps) {
  const animationStyle =
    animationDelayMs > 0 ? { animationDelay: `${animationDelayMs}ms` } : undefined

  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <article
        className="group/message flex w-full animate-message-in justify-end"
        style={animationStyle}
        aria-label="Your message"
      >
        <div className="user-message-bubble">
          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{message.content}</p>
        </div>
      </article>
    )
  }

  return (
    <AiMessageLayout style={animationStyle}>
      <AssistantMessagePresentation
        content={<MarkdownRenderer content={message.content} />}
        timestamp={message.created_at}
        metadata={{
          confidence_score: message.confidence_score,
          citations: message.citations,
        }}
      />
    </AiMessageLayout>
  )
}
