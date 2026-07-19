import { findCitationMatchInPage } from './matchCitationText'

export const PDF_CITATION_HIGHLIGHT_CLASS = 'pdf-citation-highlight'

export type CitationHighlightApplyResult = 'matched' | 'failed'

function collectSpans(textLayerRoot: HTMLElement): HTMLElement[] {
  return Array.from(textLayerRoot.querySelectorAll('span')).filter(
    (node): node is HTMLElement => node instanceof HTMLElement,
  )
}

function buildCharMap(
  spans: HTMLElement[],
  insertSpaces: boolean,
): { raw: string; charToSpan: number[] } {
  let raw = ''
  const charToSpan: number[] = []

  spans.forEach((span, spanIndex) => {
    const text = span.textContent ?? ''
    if (
      insertSpaces &&
      raw.length > 0 &&
      !/\s$/.test(raw) &&
      text.length > 0 &&
      !/^\s/.test(text)
    ) {
      charToSpan.push(spanIndex)
      raw += ' '
    }
    for (let i = 0; i < text.length; i += 1) {
      charToSpan.push(spanIndex)
      raw += text[i]!
    }
  })

  return { raw, charToSpan }
}

export function clearCitationHighlights(root: ParentNode): void {
  root.querySelectorAll(`.${PDF_CITATION_HIGHLIGHT_CLASS}`).forEach((el) => {
    el.classList.remove(PDF_CITATION_HIGHLIGHT_CLASS)
  })
}

/**
 * Highlight text-layer spans that best match the citation excerpt.
 * Returns whether a match was painted.
 */
export function highlightCitationInTextLayer(
  textLayerRoot: HTMLElement,
  citationText: string,
  options?: { scrollIntoView?: boolean },
): CitationHighlightApplyResult {
  const spans = collectSpans(textLayerRoot)
  if (spans.length === 0 || !citationText.trim()) {
    return 'failed'
  }

  let match = findCitationMatchInPage(buildCharMap(spans, false).raw, citationText)
  let charToSpan = buildCharMap(spans, false).charToSpan

  if (!match) {
    const spaced = buildCharMap(spans, true)
    match = findCitationMatchInPage(spaced.raw, citationText)
    charToSpan = spaced.charToSpan
  }

  if (!match) {
    return 'failed'
  }

  clearCitationHighlights(textLayerRoot)

  const spanIndices = new Set<number>()
  for (let i = match.start; i < match.end && i < charToSpan.length; i += 1) {
    spanIndices.add(charToSpan[i]!)
  }

  let first: HTMLElement | null = null
  for (const index of [...spanIndices].sort((a, b) => a - b)) {
    const span = spans[index]
    if (!span) continue
    span.classList.add(PDF_CITATION_HIGHLIGHT_CLASS)
    if (!first) first = span
  }

  if (!first) {
    return 'failed'
  }

  if (options?.scrollIntoView !== false && typeof first.scrollIntoView === 'function') {
    first.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
  }

  return 'matched'
}

/** Locates the react-pdf / pdf.js text layer inside a page frame. */
export function findPageTextLayer(pageFrame: HTMLElement): HTMLElement | null {
  const layer =
    pageFrame.querySelector<HTMLElement>('.react-pdf__Page__textContent') ??
    pageFrame.querySelector<HTMLElement>('.textLayer')
  return layer
}
