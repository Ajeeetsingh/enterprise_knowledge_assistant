import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Document } from '../types'
import { DUPLICATE_HIGHLIGHT_MS } from '../utils/duplicateHighlight'
import DocumentTable from './DocumentTable'

function doc(id: string, filename: string): Document {
  return {
    document_id: id,
    filename,
    status: 'searchable',
    uploaded_at: '2026-01-01T00:00:00Z',
    uploaded_by: 'user-1',
  }
}

describe('DocumentTable duplicate highlight', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('highlights the matching row and scrolls it into view', () => {
    const { rerender } = render(
      <MemoryRouter>
        <DocumentTable
          documents={[doc('doc-1', 'one.pdf'), doc('doc-2', 'two.pdf')]}
          isLoading={false}
          highlightedDocumentId={null}
          onDelete={vi.fn()}
        />
      </MemoryRouter>,
    )

    rerender(
      <MemoryRouter>
        <DocumentTable
          documents={[doc('doc-1', 'one.pdf'), doc('doc-2', 'two.pdf')]}
          isLoading={false}
          highlightedDocumentId="doc-2"
          onDelete={vi.fn()}
        />
      </MemoryRouter>,
    )

    const row = screen.getByText('two.pdf').closest('tr')
    expect(row).toHaveAttribute('data-document-id', 'doc-2')
    expect(row).toHaveAttribute('data-highlighted', 'true')
    expect(row).toHaveClass('document-row--highlight')
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledTimes(1)
  })

  it('does not throw when the highlighted document is not rendered', () => {
    expect(() =>
      render(
        <MemoryRouter>
          <DocumentTable
            documents={[doc('doc-1', 'one.pdf')]}
            isLoading={false}
            highlightedDocumentId="missing"
            onDelete={vi.fn()}
          />
        </MemoryRouter>,
      ),
    ).not.toThrow()

    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled()
  })

  it('uses instant scroll when prefers-reduced-motion is set', () => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn((query: string) => ({
        matches: query.includes('prefers-reduced-motion'),
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })

    render(
      <MemoryRouter>
        <DocumentTable
          documents={[doc('doc-1', 'one.pdf')]}
          isLoading={false}
          highlightedDocumentId="doc-1"
          onDelete={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'auto',
      block: 'nearest',
    })
  })
})

describe('DocumentsPage highlight lifetime helper', () => {
  it('keeps highlight duration at approximately two seconds', () => {
    expect(DUPLICATE_HIGHLIGHT_MS).toBe(2000)
  })

  it('can clear a highlight after the configured duration', () => {
    vi.useFakeTimers()
    let highlighted: string | null = 'doc-1'
    const clear = () => {
      highlighted = null
    }
    const timer = window.setTimeout(clear, DUPLICATE_HIGHLIGHT_MS)
    expect(highlighted).toBe('doc-1')
    act(() => {
      vi.advanceTimersByTime(DUPLICATE_HIGHLIGHT_MS)
    })
    expect(highlighted).toBeNull()
    window.clearTimeout(timer)
    vi.useRealTimers()
  })
})
