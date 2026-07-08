import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DocumentStatus } from '@/features/documents/types'

import RecentUploadsTable from './RecentUploadsTable'

describe('RecentUploadsTable', () => {
  it('renders recent uploads', () => {
    render(
      <RecentUploadsTable
        isLoading={false}
        uploads={[
          {
            document_id: 'doc-1',
            filename: 'Policy.pdf',
            status: DocumentStatus.Searchable,
            uploaded_at: new Date().toISOString(),
            uploaded_by: 'user-1',
          },
          {
            document_id: 'doc-2',
            filename: 'Guide.pdf',
            status: DocumentStatus.Processing,
            uploaded_at: new Date(Date.now() - 2 * 60_000).toISOString(),
            uploaded_by: 'user-2',
          },
        ]}
      />,
    )

    expect(screen.getByText('Policy.pdf')).toBeInTheDocument()
    expect(screen.getByText('Guide.pdf')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('renders loading state', () => {
    render(<RecentUploadsTable isLoading uploads={[]} />)

    expect(screen.getByLabelText('Loading recent uploads')).toBeInTheDocument()
  })
})
