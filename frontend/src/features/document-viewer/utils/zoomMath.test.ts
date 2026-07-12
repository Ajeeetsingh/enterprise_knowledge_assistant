import { describe, expect, it } from 'vitest'

import {
  clampZoom,
  computeAnchorPoint,
  computeAnchoredScroll,
  computeRenderWidth,
  distanceBetweenTouches,
  midpointBetweenTouches,
  rectCenter,
  zoomFactorFromWheelDelta,
  ZOOM_MAX,
  ZOOM_MIN,
} from './zoomMath'

describe('clampZoom', () => {
  it('clamps below the minimum', () => {
    expect(clampZoom(0.1)).toBe(ZOOM_MIN)
  })

  it('clamps above the maximum', () => {
    expect(clampZoom(10)).toBe(ZOOM_MAX)
  })

  it('passes through in-range values', () => {
    expect(clampZoom(1.5)).toBe(1.5)
  })
})

describe('zoomFactorFromWheelDelta', () => {
  it('zooms in for negative deltaY (wheel up / pinch-out)', () => {
    expect(zoomFactorFromWheelDelta(-100)).toBeGreaterThan(1)
  })

  it('zooms out for positive deltaY (wheel down / pinch-in)', () => {
    expect(zoomFactorFromWheelDelta(100)).toBeLessThan(1)
  })

  it('is a no-op for zero delta', () => {
    expect(zoomFactorFromWheelDelta(0)).toBeCloseTo(1)
  })
})

describe('computeRenderWidth', () => {
  it('caps fit-width at fitWidthMax on very wide viewports', () => {
    expect(computeRenderWidth(1400, 1, true, 1000)).toBe(1000)
  })

  it('uses the base width directly when narrower than the cap', () => {
    expect(computeRenderWidth(800, 1, true, 1000)).toBe(800)
  })

  it('scales linearly with zoom when fit-width is off', () => {
    expect(computeRenderWidth(800, 1.5, false, 1000)).toBe(1200)
  })

  it('never renders narrower than the minimum page width', () => {
    expect(computeRenderWidth(800, 0.1, false, 1000)).toBe(280)
  })
})

describe('anchor-preserving zoom math', () => {
  it('computeAnchorPoint captures the content point under the cursor', () => {
    const anchor = computeAnchorPoint(
      { scrollLeft: 50, scrollTop: 200 },
      { left: 10, top: 20 },
      110, // clientX
      220, // clientY
    )
    expect(anchor.viewportX).toBe(100)
    expect(anchor.viewportY).toBe(200)
    expect(anchor.localX).toBe(150)
    expect(anchor.localY).toBe(400)
  })

  it('computeAnchoredScroll keeps the anchor point fixed under the cursor after scaling', () => {
    // Content doubles in size (scaleRatio = 2): the anchor's content
    // coordinates double, and scroll must grow by the same delta so the
    // point still lands at the same viewport position.
    const anchor = { localX: 150, localY: 400, viewportX: 100, viewportY: 200 }
    const { scrollLeft, scrollTop } = computeAnchoredScroll(anchor, 2)
    expect(scrollLeft).toBe(150 * 2 - 100)
    expect(scrollTop).toBe(400 * 2 - 200)
  })

  it('is a no-op when the scale ratio is 1 (no size change)', () => {
    const anchor = { localX: 150, localY: 400, viewportX: 100, viewportY: 200 }
    const { scrollLeft, scrollTop } = computeAnchoredScroll(anchor, 1)
    // scrollLeft/scrollTop should reconstruct the original scroll position.
    expect(scrollLeft).toBe(anchor.localX - anchor.viewportX)
    expect(scrollTop).toBe(anchor.localY - anchor.viewportY)
  })

  it('rectCenter returns the midpoint of a rect', () => {
    expect(rectCenter({ left: 0, top: 0, width: 200, height: 100 })).toEqual({
      clientX: 100,
      clientY: 50,
    })
  })

  it('distanceBetweenTouches computes euclidean distance', () => {
    expect(
      distanceBetweenTouches({ clientX: 0, clientY: 0 }, { clientX: 3, clientY: 4 }),
    ).toBe(5)
  })

  it('midpointBetweenTouches computes the average point', () => {
    expect(
      midpointBetweenTouches({ clientX: 0, clientY: 0 }, { clientX: 10, clientY: 20 }),
    ).toEqual({ clientX: 5, clientY: 10 })
  })
})
