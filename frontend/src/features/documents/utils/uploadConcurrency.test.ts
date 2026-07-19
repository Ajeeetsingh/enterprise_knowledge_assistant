import { describe, expect, it, vi } from 'vitest'

import { mapWithConcurrency } from './uploadConcurrency'

describe('mapWithConcurrency', () => {
  it('limits concurrent workers', async () => {
    let active = 0
    let maxActive = 0

    const results = await mapWithConcurrency(
      [1, 2, 3, 4, 5],
      async (value) => {
        active += 1
        maxActive = Math.max(maxActive, active)
        await new Promise((resolve) => setTimeout(resolve, 20))
        active -= 1
        return value * 2
      },
      3,
    )

    expect(results).toEqual([2, 4, 6, 8, 10])
    expect(maxActive).toBeLessThanOrEqual(3)
  })

  it('preserves order when tasks finish out of order', async () => {
    const delays = [30, 5, 15]
    const worker = vi.fn(async (value: number, index: number) => {
      await new Promise((resolve) => setTimeout(resolve, delays[index]))
      return value
    })

    const results = await mapWithConcurrency([10, 20, 30], worker, 3)
    expect(results).toEqual([10, 20, 30])
  })
})
