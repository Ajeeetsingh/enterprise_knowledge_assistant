import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from 'react'

import type { ZoomIntent } from '../types'
import {
  clampZoom,
  computeAnchoredScroll,
  computeAnchorPoint,
  distanceBetweenTouches,
  midpointBetweenTouches,
  rectCenter,
  zoomFactorFromWheelDelta,
  ZOOM_ANIMATION_MS,
  ZOOM_COMMIT_DEBOUNCE_MS,
  ZOOM_STEP,
  type AnchorPoint,
} from '../utils/zoomMath'

interface GestureState {
  /** Zoom "number" baseline for this gesture (1 when starting from fit-width). */
  baseZoom: number
  /** Actual rendered page width (px) at gesture start — ground truth for CSS scale math. */
  baseRenderWidth: number
  /** Running target zoom number, updated per tick. */
  currentTargetZoom: number
}

interface PendingSettle {
  anchor: AnchorPoint
  baseRenderWidth: number
  animate: boolean
}

export interface UsePdfZoomGesturesOptions {
  /** The scrollable PDF viewport — wheel/pinch listeners attach here. */
  containerRef: RefObject<HTMLDivElement | null>
  /** Committed reducer state, read for baseline calculations. */
  zoom: number
  fitWidth: boolean
  /** Current actual rendered page width (px), i.e. the live `pageWidth` value. */
  renderWidth: number
  /** Given a hypothetical (zoom, fitWidth), returns the page width it would render at. */
  computeRenderWidth: (zoom: number, fitWidth: boolean) => number
  /** One-shot trigger for discrete (toolbar/keyboard) zoom actions. */
  zoomIntent: ZoomIntent | null
  /** Commits a new zoom/fitWidth to the source of truth (the viewer reducer). */
  onCommit: (zoom: number, fitWidth: boolean) => void
  enabled?: boolean
}

const IDLE_STYLE: CSSProperties = {}

/**
 * Drives the whole "zoom experience" for the PDF canvas:
 * - Ctrl+wheel / trackpad pinch zoom, scoped to the PDF viewport only.
 * - Two-finger touch pinch-to-zoom on mobile.
 * - Smooth, viewport-anchored animation for toolbar/keyboard zoom actions.
 *
 * Architecture: continuous gestures (wheel, touch-pinch) apply an instant
 * CSS `transform: scale()` "preview" to the pages wrapper — cheap, GPU-only,
 * no canvas re-render — anchored at the cursor/touch midpoint so the point
 * under it never moves. Once the gesture settles (idle debounce, or
 * touch/gesture end), the real zoom value is committed to the reducer,
 * `DocumentPdfViewer` re-renders the actual `<Page>` canvases at the crisp
 * target resolution, and this hook restores scroll position so the anchor
 * point lands in the exact same spot, then clears the preview transform.
 * Discrete actions (toolbar buttons, keyboard shortcuts) commit immediately
 * and use the same anchor-restore step plus a FLIP-style transform animation
 * for a smooth grow/shrink instead of a jump cut.
 */
export function usePdfZoomGestures({
  containerRef,
  zoom,
  fitWidth,
  renderWidth,
  computeRenderWidth,
  zoomIntent,
  onCommit,
  enabled = true,
}: UsePdfZoomGesturesOptions): { previewStyle: CSSProperties } {
  const [previewStyle, setPreviewStyle] = useState<CSSProperties>(IDLE_STYLE)

  const gestureRef = useRef<GestureState | null>(null)
  const pendingSettleRef = useRef<PendingSettle | null>(null)
  const commitTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const settleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastZoomIntentNonceRef = useRef<number | null>(null)
  const pinchStartDistanceRef = useRef<number | null>(null)

  const zoomRef = useRef(zoom)
  const fitWidthRef = useRef(fitWidth)
  const renderWidthRef = useRef(renderWidth)
  const computeRenderWidthRef = useRef(computeRenderWidth)
  zoomRef.current = zoom
  fitWidthRef.current = fitWidth
  renderWidthRef.current = renderWidth
  computeRenderWidthRef.current = computeRenderWidth

  function beginGesture(): GestureState {
    if (gestureRef.current) return gestureRef.current
    const baseZoom = fitWidthRef.current ? 1 : zoomRef.current
    const started: GestureState = {
      baseZoom,
      baseRenderWidth: renderWidthRef.current,
      currentTargetZoom: baseZoom,
    }
    gestureRef.current = started
    return started
  }

  function applyLivePreview(targetZoom: number, clientX: number, clientY: number) {
    const container = containerRef.current
    const gesture = gestureRef.current
    if (!container || !gesture) return
    const rect = container.getBoundingClientRect()
    const anchor = computeAnchorPoint(container, rect, clientX, clientY)
    const desiredRenderWidth = computeRenderWidthRef.current(targetZoom, false)
    const scale = desiredRenderWidth / gesture.baseRenderWidth
    setPreviewStyle({
      transform: `scale(${scale})`,
      transformOrigin: `${anchor.localX}px ${anchor.localY}px`,
      transition: 'none',
      willChange: 'transform',
    })
  }

  /**
   * Arms the post-commit settle step, but only when the commit will actually
   * change the rendered page width — otherwise the pending anchor would sit
   * unconsumed and could misfire on a later, unrelated `renderWidth` change
   * (e.g. a plain window resize).
   */
  function armSettleIfNeeded(
    clientX: number,
    clientY: number,
    baseRenderWidth: number,
    predictedRenderWidth: number,
    animate: boolean,
  ) {
    const container = containerRef.current
    if (!container) return
    if (Math.abs(predictedRenderWidth - baseRenderWidth) < 0.5) {
      pendingSettleRef.current = null
      setPreviewStyle(IDLE_STYLE)
      return
    }
    const rect = container.getBoundingClientRect()
    pendingSettleRef.current = {
      anchor: computeAnchorPoint(container, rect, clientX, clientY),
      baseRenderWidth,
      animate,
    }
  }

  function finishGesture(targetZoom: number, targetFitWidth: boolean, clientX: number, clientY: number) {
    const gesture = gestureRef.current
    if (commitTimerRef.current) {
      clearTimeout(commitTimerRef.current)
      commitTimerRef.current = null
    }
    const clamped = clampZoom(targetZoom)
    const baseRenderWidth = gesture?.baseRenderWidth ?? renderWidthRef.current
    const predicted = computeRenderWidthRef.current(clamped, targetFitWidth)
    armSettleIfNeeded(clientX, clientY, baseRenderWidth, predicted, false)
    gestureRef.current = null
    onCommit(clamped, targetFitWidth)
  }

  function commitDiscrete(targetZoom: number, targetFitWidth: boolean) {
    const container = containerRef.current
    if (!container) return
    const rect = container.getBoundingClientRect()
    const { clientX, clientY } = rectCenter(rect)
    const clamped = clampZoom(targetZoom)
    const baseRenderWidth = renderWidthRef.current
    const predicted = computeRenderWidthRef.current(clamped, targetFitWidth)
    armSettleIfNeeded(clientX, clientY, baseRenderWidth, predicted, true)
    gestureRef.current = null
    onCommit(clamped, targetFitWidth)
  }

  // Ctrl+wheel / trackpad-pinch zoom — scoped to this viewport only. Plain
  // (non-ctrl) wheel events are left completely untouched for normal scrolling.
  useEffect(() => {
    const container = containerRef.current
    if (!container || !enabled) return

    function handleWheel(event: WheelEvent) {
      if (!event.ctrlKey) return
      event.preventDefault()

      const gesture = beginGesture()
      const factor = zoomFactorFromWheelDelta(event.deltaY)
      gesture.currentTargetZoom = clampZoom(gesture.currentTargetZoom * factor)

      applyLivePreview(gesture.currentTargetZoom, event.clientX, event.clientY)

      if (commitTimerRef.current) clearTimeout(commitTimerRef.current)
      commitTimerRef.current = setTimeout(() => {
        commitTimerRef.current = null
        finishGesture(gesture.currentTargetZoom, false, event.clientX, event.clientY)
      }, ZOOM_COMMIT_DEBOUNCE_MS)
    }

    container.addEventListener('wheel', handleWheel, { passive: false })
    return () => container.removeEventListener('wheel', handleWheel)
  }, [containerRef, enabled])

  // Two-finger touch pinch-to-zoom, scoped to the PDF viewport. Single-touch
  // gestures (page-swipe navigation, normal scrolling) are left untouched.
  useEffect(() => {
    const container = containerRef.current
    if (!container || !enabled) return

    function handleTouchStart(event: TouchEvent) {
      if (event.touches.length !== 2) return
      const [a, b] = [event.touches[0]!, event.touches[1]!]
      pinchStartDistanceRef.current = distanceBetweenTouches(a, b)
      beginGesture()
    }

    function handleTouchMove(event: TouchEvent) {
      if (event.touches.length !== 2) return
      const startDistance = pinchStartDistanceRef.current
      const gesture = gestureRef.current
      if (!startDistance || !gesture) return

      event.preventDefault()
      const [a, b] = [event.touches[0]!, event.touches[1]!]
      const distance = distanceBetweenTouches(a, b)
      const midpoint = midpointBetweenTouches(a, b)
      gesture.currentTargetZoom = clampZoom(gesture.baseZoom * (distance / startDistance))
      applyLivePreview(gesture.currentTargetZoom, midpoint.clientX, midpoint.clientY)
    }

    function handleTouchEnd(event: TouchEvent) {
      const gesture = gestureRef.current
      const node = containerRef.current
      if (!gesture || !node || pinchStartDistanceRef.current == null) return
      if (event.touches.length >= 2) return

      pinchStartDistanceRef.current = null
      const rect = node.getBoundingClientRect()
      const { clientX, clientY } = rectCenter(rect)
      finishGesture(gesture.currentTargetZoom, false, clientX, clientY)
    }

    container.addEventListener('touchstart', handleTouchStart, { passive: true })
    container.addEventListener('touchmove', handleTouchMove, { passive: false })
    container.addEventListener('touchend', handleTouchEnd, { passive: true })
    container.addEventListener('touchcancel', handleTouchEnd, { passive: true })
    return () => {
      container.removeEventListener('touchstart', handleTouchStart)
      container.removeEventListener('touchmove', handleTouchMove)
      container.removeEventListener('touchend', handleTouchEnd)
      container.removeEventListener('touchcancel', handleTouchEnd)
    }
  }, [containerRef, enabled])

  // Discrete toolbar/keyboard zoom actions — animate smoothly, anchored at
  // the viewport center (no cursor position available).
  useEffect(() => {
    if (!zoomIntent || !enabled) return
    if (lastZoomIntentNonceRef.current === zoomIntent.nonce) return
    lastZoomIntentNonceRef.current = zoomIntent.nonce

    const baseline = fitWidthRef.current ? 1 : zoomRef.current
    let targetZoom = baseline
    let targetFitWidth = false

    switch (zoomIntent.type) {
      case 'in':
        targetZoom = clampZoom(baseline + ZOOM_STEP)
        break
      case 'out':
        targetZoom = clampZoom(baseline - ZOOM_STEP)
        break
      case 'fit':
        targetFitWidth = true
        targetZoom = zoomRef.current
        break
      case 'actual':
        targetZoom = 1
        break
      default:
        break
    }

    commitDiscrete(targetZoom, targetFitWidth)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refs cover latest zoom/fitWidth
  }, [zoomIntent, enabled])

  // Runs after the parent has re-rendered with the newly-committed render
  // width: restores scroll so the anchor point stays fixed, and (for
  // discrete actions) plays the FLIP settle animation back to natural size.
  useLayoutEffect(() => {
    const pending = pendingSettleRef.current
    const container = containerRef.current
    if (!pending || !container) return
    pendingSettleRef.current = null

    const scaleRatio = pending.baseRenderWidth > 0 ? renderWidth / pending.baseRenderWidth : 1
    const { scrollLeft, scrollTop } = computeAnchoredScroll(pending.anchor, scaleRatio)
    container.scrollLeft = Math.max(0, scrollLeft)
    container.scrollTop = Math.max(0, scrollTop)

    if (settleTimeoutRef.current) {
      clearTimeout(settleTimeoutRef.current)
      settleTimeoutRef.current = null
    }

    if (pending.animate && Math.abs(scaleRatio - 1) > 0.001) {
      const originX = pending.anchor.localX * scaleRatio
      const originY = pending.anchor.localY * scaleRatio
      setPreviewStyle({
        transform: `scale(${1 / scaleRatio})`,
        transformOrigin: `${originX}px ${originY}px`,
        transition: 'none',
      })
      requestAnimationFrame(() => {
        setPreviewStyle({
          transform: 'scale(1)',
          transformOrigin: `${originX}px ${originY}px`,
          transition: `transform ${ZOOM_ANIMATION_MS}ms cubic-bezier(0.4, 0, 0.2, 1)`,
        })
        settleTimeoutRef.current = setTimeout(() => {
          setPreviewStyle(IDLE_STYLE)
        }, ZOOM_ANIMATION_MS + 40)
      })
    } else {
      setPreviewStyle(IDLE_STYLE)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pendingSettleRef drives this, not renderWidth alone
  }, [renderWidth])

  useEffect(
    () => () => {
      if (commitTimerRef.current) clearTimeout(commitTimerRef.current)
      if (settleTimeoutRef.current) clearTimeout(settleTimeoutRef.current)
    },
    [],
  )

  return { previewStyle }
}
