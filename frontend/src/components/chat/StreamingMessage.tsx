import { memo, useEffect, useRef, useState } from 'react'

import { cn } from '@/utils/cn'

import MarkdownRenderer from './MarkdownRenderer'
import { STREAMING_CHUNK_SIZE, STREAMING_INTERVAL_MS } from './streamingConstants'

export interface StreamingMessageProps {
  content: string
  isStreaming: boolean
  onComplete?: () => void
  chunkSize?: number
  intervalMs?: number
  className?: string
}

function ThinkingIndicator() {
  return (
    <div
      className="flex items-center gap-1.5 py-1"
      role="status"
      aria-live="polite"
      aria-label="Assistant is thinking"
    >
      <span className="thinking-dot size-2 rounded-full" />
      <span className="thinking-dot size-2 rounded-full" />
      <span className="thinking-dot size-2 rounded-full" />
    </div>
  )
}

function StreamingMessage({
  content,
  isStreaming,
  onComplete,
  chunkSize = STREAMING_CHUNK_SIZE,
  intervalMs = STREAMING_INTERVAL_MS,
  className,
}: StreamingMessageProps) {
  const [streamedContent, setStreamedContent] = useState('')
  const [streamingComplete, setStreamingComplete] = useState(!isStreaming)
  const onCompleteRef = useRef(onComplete)

  onCompleteRef.current = onComplete

  useEffect(() => {
    if (!isStreaming) {
      setStreamedContent(content)
      setStreamingComplete(true)
      onCompleteRef.current?.()
      return
    }

    if (!content) {
      setStreamedContent('')
      setStreamingComplete(false)
      return
    }

    let index = 0
    setStreamedContent('')
    setStreamingComplete(false)

    const timerId = window.setInterval(() => {
      index = Math.min(index + chunkSize, content.length)
      setStreamedContent(content.slice(0, index))

      if (index >= content.length) {
        window.clearInterval(timerId)
        setStreamingComplete(true)
        onCompleteRef.current?.()
      }
    }, intervalMs)

    return () => {
      window.clearInterval(timerId)
    }
  }, [content, isStreaming, chunkSize, intervalMs])

  if (streamingComplete) {
    return className ? (
      <MarkdownRenderer content={content} className={className} />
    ) : (
      <MarkdownRenderer content={content} />
    )
  }

  if (!streamedContent) {
    return <ThinkingIndicator />
  }

  return (
    <div className={cn(className)}>
      <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{streamedContent}</p>
    </div>
  )
}

export default memo(StreamingMessage)
