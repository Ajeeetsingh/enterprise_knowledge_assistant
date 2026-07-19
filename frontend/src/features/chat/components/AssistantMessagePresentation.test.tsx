import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AssistantMessagePresentation from './AssistantMessagePresentation'
import type { Citation } from '../types'

const openDocumentInNewTab = vi.fn()
const storeCitationHighlight = vi.fn(() => 'cite-key-1')
const resolveCitationDocumentId = vi.fn(async () => 'doc-123')
const buildDocumentViewerUrl = vi.fn(
  (documentId: string, params: { page?: number; citeKey?: string } = {}) => {
    const search = new URLSearchParams()
    if (params.page) search.set('page', String(params.page))
    if (params.citeKey) search.set('citeKey', params.citeKey)
    const query = search.toString()
    return `/documents/${documentId}${query ? `?${query}` : ''}`
  },
)

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
    showInfo: vi.fn(),
    showWarning: vi.fn(),
  }),
}))

vi.mock('@/features/document-viewer', () => ({
  buildDocumentViewerUrl: (...args: unknown[]) =>
    buildDocumentViewerUrl(...(args as [string, { page?: number; citeKey?: string }?])),
  buildCitationViewerParams: (citation: Citation) =>
    typeof citation.page === 'number' ? { page: citation.page } : {},
  resolveCitationDocumentId: (...args: unknown[]) =>
    resolveCitationDocumentId(...(args as [Citation])),
  storeCitationHighlight: (...args: unknown[]) =>
    storeCitationHighlight(...(args as [{ excerpt: string; page?: number }])),
  openDocumentInNewTab: (...args: unknown[]) => openDocumentInNewTab(...(args as [string])),
}))

vi.mock('@/hooks/useMinWidthMediaQuery', () => ({
  useMinWidthMediaQuery: () => true,
}))

const citations: Citation[] = [
  {
    source: 'Employee Handbook.pdf',
    excerpt: 'Employees are entitled to 20 days of annual leave.',
    confidence: 0.92,
    page: 14,
  },
]

describe('AssistantMessagePresentation', () => {
  beforeEach(() => {
    openDocumentInNewTab.mockClear()
    storeCitationHighlight.mockClear()
    resolveCitationDocumentId.mockClear()
    buildDocumentViewerUrl.mockClear()
  })

  it('shows only the answer and timestamp by default', () => {
    render(
      <AssistantMessagePresentation
        content={<p>Annual leave is 20 days.</p>}
        timestamp="2026-03-15T10:30:00.000Z"
        metadata={{ confidence_score: 0.92, citations }}
      />,
    )

    expect(screen.getByText('Annual leave is 20 days.')).toBeInTheDocument()
    expect(screen.getByRole('time')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Details' })).toBeInTheDocument()
    expect(screen.queryByText('Sources')).not.toBeInTheDocument()
    expect(screen.queryByText(/^Confidence$/i)).not.toBeInTheDocument()
  })

  it('reveals sources and confidence inside the details panel', async () => {
    const user = userEvent.setup()

    render(
      <AssistantMessagePresentation
        content={<p>Annual leave is 20 days.</p>}
        timestamp="2026-03-15T10:30:00.000Z"
        metadata={{ confidence_score: 0.92, citations }}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Details' }))

    expect(screen.getByText('Sources')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('Employee Handbook.pdf')).toBeInTheDocument()
    expect(screen.getByText('Page 14')).toBeInTheDocument()
  })

  it('opens the source document in a new tab with page and citation context', async () => {
    const user = userEvent.setup()

    render(
      <AssistantMessagePresentation
        content={<p>Annual leave is 20 days.</p>}
        timestamp="2026-03-15T10:30:00.000Z"
        metadata={{ confidence_score: 0.92, citations }}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Details' }))
    await user.click(screen.getByRole('button', { name: 'Open Source' }))

    expect(resolveCitationDocumentId).toHaveBeenCalledWith(citations[0])
    expect(storeCitationHighlight).toHaveBeenCalledWith({
      excerpt: 'Employees are entitled to 20 days of annual leave.',
      page: 14,
    })
    expect(buildDocumentViewerUrl).toHaveBeenCalledWith('doc-123', {
      page: 14,
      citeKey: 'cite-key-1',
    })
    expect(openDocumentInNewTab).toHaveBeenCalledWith(
      '/documents/doc-123?page=14&citeKey=cite-key-1',
    )
  })

  it('hides metadata controls while streaming', () => {
    render(
      <AssistantMessagePresentation
        content={<p>Streaming answer…</p>}
        metadata={{ confidence_score: 0.5, citations }}
        showMeta={false}
      />,
    )

    expect(screen.queryByRole('time')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Details' })).not.toBeInTheDocument()
  })
})
