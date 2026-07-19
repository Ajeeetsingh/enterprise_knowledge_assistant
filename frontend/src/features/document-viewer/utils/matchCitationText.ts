/**
 * Normalized text matching for citation excerpts against PDF page text.
 * Search is expected to be constrained to a single cited page by the caller.
 */

export function normalizeForMatch(text: string): string {
  return text.replace(/\s+/g, ' ').trim().toLowerCase()
}

/**
 * Build a whitespace-collapsed, lowercased string plus a map from each
 * normalized character index back to an index in the original string.
 */
export function buildNormalizedIndexMap(raw: string): {
  normalized: string
  normToRaw: number[]
} {
  const normToRaw: number[] = []
  let normalized = ''
  let lastWasSpace = false

  for (let i = 0; i < raw.length; i += 1) {
    const ch = raw[i]!
    if (/\s/.test(ch)) {
      if (!lastWasSpace && normalized.length > 0) {
        normalized += ' '
        normToRaw.push(i)
        lastWasSpace = true
      }
      continue
    }
    normalized += ch.toLowerCase()
    normToRaw.push(i)
    lastWasSpace = false
  }

  if (normalized.endsWith(' ')) {
    normalized = normalized.slice(0, -1)
    normToRaw.pop()
  }

  return { normalized, normToRaw }
}

function rangeFromNormalized(
  normToRaw: number[],
  start: number,
  length: number,
): { start: number; end: number } | null {
  if (length <= 0 || start < 0 || start + length > normToRaw.length) {
    return null
  }
  const rawStart = normToRaw[start]
  const rawEndInclusive = normToRaw[start + length - 1]
  if (rawStart == null || rawEndInclusive == null) return null
  return { start: rawStart, end: rawEndInclusive + 1 }
}

/**
 * Locate the best match for `citationText` inside `pageText`.
 * Prefers an exact normalized match, then progressively shorter distinctive slices.
 */
export function findCitationMatchInPage(
  pageText: string,
  citationText: string,
): { start: number; end: number } | null {
  const cite = normalizeForMatch(citationText)
  if (!cite || cite.length < 8) return null

  const { normalized, normToRaw } = buildNormalizedIndexMap(pageText)
  if (!normalized) return null

  const exact = normalized.indexOf(cite)
  if (exact !== -1) {
    // Short matches must be unique on the page to avoid common-word highlights.
    if (cite.length < 16) {
      const second = normalized.indexOf(cite, exact + 1)
      if (second !== -1) return null
    }
    return rangeFromNormalized(normToRaw, exact, cite.length)
  }

  // Short excerpts: require exact unique match only.
  if (cite.length < 16) {
    return null
  }

  const minLen = Math.max(24, Math.floor(cite.length * 0.35))

  // Prefer word-aligned windows so progressive fallbacks do not start mid-token.
  const wordStarts: number[] = [0]
  for (let i = 1; i < cite.length; i += 1) {
    if (cite[i - 1] === ' ' && cite[i] !== ' ') {
      wordStarts.push(i)
    }
  }

  for (let len = cite.length - 1; len >= minLen; len -= 1) {
    let best: { start: number; end: number; len: number } | null = null

    for (const offset of wordStarts) {
      if (offset + len > cite.length) continue
      const slice = cite.slice(offset, offset + len).trim()
      if (slice.length < minLen) continue

      const found = normalized.indexOf(slice)
      if (found === -1) continue

      const second = normalized.indexOf(slice, found + 1)
      if (second !== -1 && slice.length < cite.length * 0.55) continue

      const range = rangeFromNormalized(normToRaw, found, slice.length)
      if (!range) continue
      if (!best || slice.length > best.len) {
        best = { ...range, len: slice.length }
      }
    }

    if (best) {
      return { start: best.start, end: best.end }
    }
  }

  return null
}
