/**
 * Pure math helpers for the PDF zoom experience.
 *
 * Kept framework/DOM-free so the anchor-preservation formulas can be unit
 * tested without mounting react-pdf or touching the DOM.
 */

export const ZOOM_MIN = 0.5
export const ZOOM_MAX = 3
export const ZOOM_STEP = 0.1

/** Multiplier applied per wheel "tick" — tuned so a normal trackpad pinch feels continuous. */
const WHEEL_SENSITIVITY = 0.0016

/** Idle time after the last zoom tick before the real PDF re-render is committed. */
export const ZOOM_COMMIT_DEBOUNCE_MS = 160

/** Duration of the FLIP-style settle animation for discrete (button/keyboard) zoom. */
export const ZOOM_ANIMATION_MS = 200

export function clampZoom(value: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value))
}

/**
 * Converts a wheel event's `deltaY` into a multiplicative zoom factor.
 * Negative deltaY (wheel up / pinch-out) zooms in, producing a factor > 1.
 */
export function zoomFactorFromWheelDelta(deltaY: number): number {
  return Math.exp(-deltaY * WHEEL_SENSITIVITY)
}

export interface AnchorPoint {
  /** Point in the transformed element's own (unscaled) local coordinate space. */
  localX: number
  localY: number
  /** Point relative to the container's viewport — where the anchor must stay visually. */
  viewportX: number
  viewportY: number
}

/**
 * Captures the content point currently under `clientX`/`clientY` so it can be
 * kept visually fixed while the surrounding content scales.
 */
export function computeAnchorPoint(
  scroll: { scrollLeft: number; scrollTop: number },
  containerRect: { left: number; top: number },
  clientX: number,
  clientY: number,
): AnchorPoint {
  const viewportX = clientX - containerRect.left
  const viewportY = clientY - containerRect.top
  return {
    localX: scroll.scrollLeft + viewportX,
    localY: scroll.scrollTop + viewportY,
    viewportX,
    viewportY,
  }
}

/**
 * Given an anchor captured at the old render size and the ratio between the
 * new and old render size, returns the scroll offsets that keep the anchor
 * point fixed under the cursor / viewport point it was captured at.
 */
export function computeAnchoredScroll(
  anchor: AnchorPoint,
  scaleRatio: number,
): { scrollLeft: number; scrollTop: number } {
  return {
    scrollLeft: anchor.localX * scaleRatio - anchor.viewportX,
    scrollTop: anchor.localY * scaleRatio - anchor.viewportY,
  }
}

/** Center point of a rect, in client coordinates — used as the anchor for button/keyboard zoom. */
export function rectCenter(rect: { left: number; top: number; width: number; height: number }): {
  clientX: number
  clientY: number
} {
  return {
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2,
  }
}

/**
 * Mirrors the page-width formula in `DocumentPdfViewer` so the zoom gesture
 * hook can compute exact pixel widths for hypothetical (zoom, fitWidth)
 * pairs — needed to size the live CSS preview correctly even when fit-width
 * is capped by `fitWidthMax`.
 */
export function computeRenderWidth(
  basePageWidth: number,
  zoom: number,
  fitWidth: boolean,
  fitWidthMax: number,
): number {
  return fitWidth ? Math.min(basePageWidth, fitWidthMax) : Math.max(280, basePageWidth * zoom)
}

export function distanceBetweenTouches(
  a: { clientX: number; clientY: number },
  b: { clientX: number; clientY: number },
): number {
  return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)
}

export function midpointBetweenTouches(
  a: { clientX: number; clientY: number },
  b: { clientX: number; clientY: number },
): { clientX: number; clientY: number } {
  return {
    clientX: (a.clientX + b.clientX) / 2,
    clientY: (a.clientY + b.clientY) / 2,
  }
}
