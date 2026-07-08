import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import StreamingMessage from './StreamingMessage'

const SAMPLE_TEXT = 'Hello world from the assistant'
const MARKDOWN_CONTENT = '# Heading\n\n- Item one'

describe('StreamingMessage', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('starts streaming with typing indicator', () => {
    render(
      <StreamingMessage
        content={SAMPLE_TEXT}
        isStreaming
        chunkSize={5}
        intervalMs={20}
      />,
    )

    expect(screen.getByText(/Assistant is typing/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })

  it('reveals content progressively in chunks', () => {
    render(
      <StreamingMessage
        content={SAMPLE_TEXT}
        isStreaming
        chunkSize={5}
        intervalMs={20}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(20)
    })
    expect(screen.getByText('Hello')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(20)
    })
    expect(screen.getByText('Hello worl')).toBeInTheDocument()
  })

  it('completes streaming and removes typing indicator', () => {
    render(
      <StreamingMessage
        content={SAMPLE_TEXT}
        isStreaming
        chunkSize={10}
        intervalMs={10}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.queryByText(/Assistant is typing/i)).not.toBeInTheDocument()
    expect(screen.getByText(SAMPLE_TEXT)).toBeInTheDocument()
  })

  it('calls onComplete when streaming finishes', () => {
    const onComplete = vi.fn()

    render(
      <StreamingMessage
        content={SAMPLE_TEXT}
        isStreaming
        onComplete={onComplete}
        chunkSize={10}
        intervalMs={10}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(onComplete).toHaveBeenCalledTimes(1)
  })

  it('cleans up interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval')

    const { unmount } = render(
      <StreamingMessage
        content={SAMPLE_TEXT}
        isStreaming
        chunkSize={5}
        intervalMs={20}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(20)
    })

    unmount()

    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })

  it('renders markdown after streaming completes', () => {
    render(
      <StreamingMessage
        content={MARKDOWN_CONTENT}
        isStreaming
        chunkSize={20}
        intervalMs={10}
      />,
    )

    act(() => {
      vi.advanceTimersByTime(10_000)
    })

    expect(screen.getByRole('heading', { level: 1, name: 'Heading' })).toBeInTheDocument()
    expect(screen.getByText('Item one')).toBeInTheDocument()
  })

  it('falls back to full markdown immediately when not streaming', () => {
    const onComplete = vi.fn()

    render(
      <StreamingMessage
        content={MARKDOWN_CONTENT}
        isStreaming={false}
        onComplete={onComplete}
      />,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Heading' })).toBeInTheDocument()
    expect(screen.queryByText(/Assistant is typing/i)).not.toBeInTheDocument()
    expect(onComplete).toHaveBeenCalledTimes(1)
  })
})
