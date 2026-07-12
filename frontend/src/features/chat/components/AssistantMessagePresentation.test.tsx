import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import AssistantMessagePresentation from './AssistantMessagePresentation'
import type { Citation } from '../types'

const navigate = vi.fn()

vi.mock('@/contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
    showInfo: vi.fn(),
    showWarning: vi.fn(),
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

vi.mock('@/features/document-viewer', () => ({
  buildDocumentViewerUrl: (documentId: string) => `/documents/${documentId}?page=14`,
  buildCitationViewerParams: (citation: Citation) =>
    typeof citation.page === 'number' ? { page: citation.page } : {},
  resolveCitationDocumentId: vi.fn(async () => 'doc-123'),
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

  it('navigates to the document viewer when Open Source is clicked', async () => {
    const user = userEvent.setup()
    navigate.mockClear()

    render(
      <AssistantMessagePresentation
        content={<p>Annual leave is 20 days.</p>}
        timestamp="2026-03-15T10:30:00.000Z"
        metadata={{ confidence_score: 0.92, citations }}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Details' }))
    await user.click(screen.getByRole('button', { name: 'Open Source' }))

    expect(navigate).toHaveBeenCalledWith('/documents/doc-123?page=14')
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
