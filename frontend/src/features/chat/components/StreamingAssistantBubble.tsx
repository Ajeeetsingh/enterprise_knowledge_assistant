import { useState } from 'react'

import StreamingMessage from '@/components/chat/StreamingMessage'

import type { ActiveStream } from '../types/streaming'
import AiMessageLayout from './AiMessageLayout'
import AssistantMessagePresentation from './AssistantMessagePresentation'

export interface StreamingAssistantBubbleProps {
  stream: ActiveStream
  onComplete: () => void
}

export default function StreamingAssistantBubble({
  stream,
  onComplete,
}: StreamingAssistantBubbleProps) {
  const [streamingComplete, setStreamingComplete] = useState(false)
  const [completedAt] = useState(() => new Date().toISOString())

  function handleStreamComplete() {
    setStreamingComplete(true)
    onComplete()
  }

  return (
    <AiMessageLayout>
      <AssistantMessagePresentation
        content={
          <StreamingMessage
            content={stream.content}
            isStreaming
            onComplete={handleStreamComplete}
          />
        }
        timestamp={streamingComplete ? completedAt : null}
        metadata={{
          confidence_score: stream.confidence_score,
          citations: stream.citations,
        }}
        showMeta={streamingComplete}
      />
    </AiMessageLayout>
  )
}
