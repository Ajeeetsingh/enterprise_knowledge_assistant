import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Document } from '../types'
import { DUPLICATE_HIGHLIGHT_MS } from '../utils/duplicateHighlight'
import DocumentTable, { DOCUMENT_TABLE_MIN_WIDTH_PX } from './DocumentTable'

function doc(
  id: string,
  filename: string,
  domain?: { domain_id?: string | null; domain_name?: string | null },
): Document {
  return {
    document_id: id,
    filename,
    status: 'searchable',
    uploaded_at: '2026-08-09T02:13:47Z',
    uploaded_by: 'user-1',
    domain_id: domain?.domain_id ?? null,
    domain_name: domain?.domain_name ?? null,
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

describe('DocumentTable domain column', () => {
  it('shows domain names and Uncategorized for legacy documents', () => {
    render(
      <MemoryRouter>
        <DocumentTable
          documents={[
            doc('doc-1', 'Budget.pdf', {
              domain_id: 'finance-id',
              domain_name: 'Finance',
            }),
            doc('doc-2', 'Legacy.pdf'),
            doc('doc-3', 'HR Policy.pdf', {
              domain_id: 'hr-id',
              domain_name: 'Human Resources',
            }),
            doc('doc-4', 'Gov Standard.pdf', {
              domain_id: 'gov-id',
              domain_name: 'Enterprise Governance',
            }),
          ]}
          isLoading={false}
          onDelete={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('Domain')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('Uncategorized')).toBeInTheDocument()
    expect(screen.getByText('Human Resources')).toBeInTheDocument()
    expect(screen.getByText('Enterprise Governance')).toBeInTheDocument()
  })
})

describe('DocumentTable scroll and responsive width', () => {
  function renderTable(options?: { width?: number; height?: number; count?: number }) {
    const width = options?.width ?? 700
    const height = options?.height ?? 360
    const count = options?.count ?? 8

    return render(
      <MemoryRouter>
        <div
          style={{ width, height, display: 'flex', flexDirection: 'column' }}
          data-testid="table-host"
        >
          <DocumentTable
            documents={Array.from({ length: count }, (_, index) =>
              doc(
                `doc-${index}`,
                index === 0
                  ? 'very-long-enterprise-policy-filename-that-should-truncate.pdf'
                  : `file-${index}.pdf`,
                index % 2 === 0
                  ? { domain_id: 'hr', domain_name: 'Human Resources' }
                  : {
                      domain_id: 'gov',
                      domain_name: 'Enterprise Governance',
                    },
              ),
            )}
            isLoading={false}
            onDownload={vi.fn()}
            onDelete={vi.fn()}
          />
        </div>
      </MemoryRouter>,
    )
  }

  it('uses one overflow-auto scrollport for both axes', () => {
    renderTable()
    const scroll = screen.getByTestId('document-table-scroll')
    expect(scroll).toHaveClass('overflow-auto')
    expect(scroll).toHaveClass('document-table-scroll')
    expect(scroll.querySelectorAll('[class*="overflow"]').length).toBe(0)
    expect(screen.queryByTestId('document-table-hscroll')).not.toBeInTheDocument()
  })

  it('applies a readability min-width so narrow viewports can overflow horizontally', () => {
    renderTable({ width: 700 })
    const table = screen.getByTestId('document-table-scroll').querySelector('table')
    expect(table).not.toBeNull()
    expect(table).toHaveClass('document-table')
    expect(table).toHaveClass('w-full')
    expect((table as HTMLElement).style.minWidth).toBe(`${DOCUMENT_TABLE_MIN_WIDTH_PX}px`)
    expect(DOCUMENT_TABLE_MIN_WIDTH_PX).toBeGreaterThan(700)
  })

  it('keeps Uploaded At and Actions as non-wrapping columns', () => {
    renderTable({ width: 700, count: 2 })
    expect(screen.getByText('Uploaded At')).toHaveClass('document-table-col-uploaded')
    expect(screen.getByText('Actions')).toHaveClass('document-table-col-actions')

    const uploadedCells = document.querySelectorAll('td.document-table-col-uploaded')
    const actionCells = document.querySelectorAll('td.document-table-col-actions')
    expect(uploadedCells.length).toBeGreaterThan(0)
    expect(actionCells.length).toBeGreaterThan(0)
  })

  it('preserves View / Download / Delete actions', () => {
    const onDelete = vi.fn()
    const onDownload = vi.fn()
    render(
      <MemoryRouter>
        <DocumentTable
          documents={[doc('doc-1', 'policy.pdf')]}
          isLoading={false}
          onDownload={onDownload}
          onDelete={onDelete}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: 'View' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download' })).toBeInTheDocument()
    screen.getByRole('button', { name: 'Delete' }).click()
    expect(onDelete).toHaveBeenCalled()
  })
})

describe('DocumentsPage highlight lifetime helper', () => {
  it('keeps highlight duration at approximately two seconds', () => {
    expect(DUPLICATE_HIGHLIGHT_MS).toBe(2000)
  })
})
