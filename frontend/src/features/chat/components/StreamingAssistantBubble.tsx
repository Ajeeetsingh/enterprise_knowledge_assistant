import { useState } from 'react'

import StreamingMessage from '@/components/chat/StreamingMessage'
import { cn } from '@/utils/cn'

import type { ActiveStream } from '../types/streaming'
import CitationList from './CitationList'

export interface StreamingAssistantBubbleProps {
  stream: ActiveStream
  onComplete: () => void
}

export default function StreamingAssistantBubble({
  stream,
  onComplete,
}: StreamingAssistantBubbleProps) {
  const [streamingComplete, setStreamingComplete] = useState(false)

  function handleStreamComplete() {
    setStreamingComplete(true)
    onComplete()
  }

  return (
    <article className="flex w-full justify-start" aria-label="Assistant message">
      <div
        className={cn(
          'max-w-[85%] rounded-lg border border-neutral-200 bg-white px-4 py-3 text-sm shadow-sm',
          'text-neutral-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-50',
        )}
      >
        <StreamingMessage
          content={stream.content}
          isStreaming
          onComplete={handleStreamComplete}
        />

        {streamingComplete && stream.confidence_score != null && (
          <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            Confidence: {Math.round(stream.confidence_score * 100)}%
          </p>
        )}

        {streamingComplete && stream.citations.length > 0 && (
          <CitationList citations={stream.citations} />
        )}
      </div>
    </article>
  )
}
