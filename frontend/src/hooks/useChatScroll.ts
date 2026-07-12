import { useCallback, useEffect, useRef } from 'react'

const NEAR_BOTTOM_THRESHOLD = 96

export function useChatScroll(conversationId: string | null) {
  const containerRef = useRef<HTMLDivElement>(null)
  const positionsRef = useRef<Map<string, number>>(new Map())
  const previousConversationIdRef = useRef<string | null>(null)
  const isNearBottomRef = useRef(true)

  const updateNearBottom = useCallback(() => {
    const container = containerRef.current
    if (!container) return
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight
    isNearBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_THRESHOLD
  }, [])

  const handleScroll = useCallback(() => {
    updateNearBottom()
  }, [updateNearBottom])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const container = containerRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior })
    isNearBottomRef.current = true
  }, [])

  const scrollIfNearBottom = useCallback(
    (behavior: ScrollBehavior = 'smooth') => {
      if (isNearBottomRef.current) {
        scrollToBottom(behavior)
      }
    },
    [scrollToBottom],
  )

  const ensureInitialScroll = useCallback(() => {
    const container = containerRef.current
    if (!container || !conversationId) return
    if (!positionsRef.current.has(conversationId)) {
      scrollToBottom('auto')
    }
  }, [conversationId, scrollToBottom])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const previousId = previousConversationIdRef.current
    if (previousId && previousId !== conversationId) {
      positionsRef.current.set(previousId, container.scrollTop)
    }

    if (conversationId) {
      const savedPosition = positionsRef.current.get(conversationId)
      requestAnimationFrame(() => {
        if (!containerRef.current) return
        if (savedPosition !== undefined) {
          containerRef.current.scrollTop = savedPosition
        } else {
          containerRef.current.scrollTop = containerRef.current.scrollHeight
        }
        updateNearBottom()
      })
    }

    previousConversationIdRef.current = conversationId
  }, [conversationId, updateNearBottom])

  return {
    containerRef,
    handleScroll,
    scrollIfNearBottom,
    scrollToBottom,
    ensureInitialScroll,
  }
}
