import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import CitationList from './CitationList'
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

const citations: Citation[] = [
  {
    source: 'Employee Handbook.pdf',
    excerpt: 'Employees are entitled to 20 days of annual leave.',
    confidence: 0.92,
    page: 14,
  },
]

describe('CitationList', () => {
  it('navigates to the document viewer when Open Source is clicked', async () => {
    const user = userEvent.setup()
    navigate.mockClear()

    render(<CitationList citations={citations} />)

    await user.click(
      screen.getByRole('button', { name: /open source document for employee handbook\.pdf/i }),
    )

    expect(navigate).toHaveBeenCalledWith('/documents/doc-123?page=14')
  })
})
