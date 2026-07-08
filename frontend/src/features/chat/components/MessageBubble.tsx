import { cn } from '@/utils/cn'

import { MarkdownRenderer } from '@/components/chat'

import type { Message } from '../types'
import CitationList from './CitationList'

export interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <article
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
      aria-label={isUser ? 'Your message' : 'Assistant message'}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-lg px-4 py-3 text-sm shadow-sm',
          isUser
            ? 'bg-primary-600 text-white dark:bg-primary-500'
            : 'border border-neutral-200 bg-white text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-50',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <MarkdownRenderer content={message.content} />
        )}

        {!isUser && message.confidence_score != null && (
          <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            Confidence: {Math.round(message.confidence_score * 100)}%
          </p>
        )}

        {!isUser && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}
      </div>
    </article>
  )
}
