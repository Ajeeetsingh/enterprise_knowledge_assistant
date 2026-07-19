import { describe, expect, it, vi } from 'vitest'

import {
  clearCitationHighlights,
  highlightCitationInTextLayer,
  PDF_CITATION_HIGHLIGHT_CLASS,
} from './applyTextLayerHighlight'

function buildTextLayer(chunks: string[]): HTMLElement {
  const root = document.createElement('div')
  root.className = 'textLayer'
  for (const chunk of chunks) {
    const span = document.createElement('span')
    span.textContent = chunk
    root.appendChild(span)
  }
  return root
}

describe('highlightCitationInTextLayer', () => {
  it('highlights exact citation text across multiple spans', () => {
    const layer = buildTextLayer([
      'Employees ',
      'are entitled ',
      'to 20 days ',
      'of annual leave.',
    ])
    const scrollIntoView = vi.fn()
    ;(layer.children[0] as HTMLElement).scrollIntoView = scrollIntoView

    const result = highlightCitationInTextLayer(
      layer,
      'Employees are entitled to 20 days of annual leave.',
    )

    expect(result).toBe('matched')
    const highlighted = layer.querySelectorAll(`.${PDF_CITATION_HIGHLIGHT_CLASS}`)
    expect(highlighted.length).toBeGreaterThan(1)
    expect(scrollIntoView).toHaveBeenCalled()
  })

  it('tolerates whitespace differences between citation and text layer', () => {
    const layer = buildTextLayer(['Remote', 'work', 'is', 'permitted', 'up', 'to', 'three', 'days'])
    const result = highlightCitationInTextLayer(
      layer,
      'Remote work is permitted up to three days',
    )
    expect(result).toBe('matched')
  })

  it('returns failed without breaking when text cannot be matched', () => {
    const layer = buildTextLayer(['Unrelated parking policy content only.'])
    const result = highlightCitationInTextLayer(
      layer,
      'Employees are entitled to twenty days of annual leave each calendar year under this handbook.',
    )
    expect(result).toBe('failed')
    expect(layer.querySelectorAll(`.${PDF_CITATION_HIGHLIGHT_CLASS}`)).toHaveLength(0)
  })

  it('returns failed when the text layer has no spans', () => {
    const layer = document.createElement('div')
    expect(highlightCitationInTextLayer(layer, 'anything at all here')).toBe('failed')
  })

  it('clears previous highlights', () => {
    const layer = buildTextLayer(['Alpha beta gamma delta epsilon zeta eta.'])
    highlightCitationInTextLayer(layer, 'Alpha beta gamma delta epsilon zeta eta.')
    expect(layer.querySelectorAll(`.${PDF_CITATION_HIGHLIGHT_CLASS}`).length).toBeGreaterThan(0)
    clearCitationHighlights(layer)
    expect(layer.querySelectorAll(`.${PDF_CITATION_HIGHLIGHT_CLASS}`)).toHaveLength(0)
  })
})
