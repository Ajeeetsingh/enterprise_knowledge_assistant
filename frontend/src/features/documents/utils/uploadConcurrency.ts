import { MAX_CONCURRENT_UPLOADS } from '../constants'

/**
 * Run async work over *items* with a fixed concurrency ceiling.
 * Results are returned in input order. Errors are not swallowed —
 * callers should catch inside *worker* when partial failure is desired.
 */
export async function mapWithConcurrency<T, R>(
  items: readonly T[],
  worker: (item: T, index: number) => Promise<R>,
  concurrency: number = MAX_CONCURRENT_UPLOADS,
): Promise<R[]> {
  if (items.length === 0) return []

  const limit = Math.max(1, Math.min(concurrency, items.length))
  const results = new Array<R>(items.length)
  let nextIndex = 0

  async function runWorker(): Promise<void> {
    while (nextIndex < items.length) {
      const index = nextIndex
      nextIndex += 1
      results[index] = await worker(items[index] as T, index)
    }
  }

  await Promise.all(Array.from({ length: limit }, () => runWorker()))
  return results
}
