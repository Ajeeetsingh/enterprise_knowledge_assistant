import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DocumentStatus } from '@/features/documents/types'

import UploadStatusPanel from './UploadStatusPanel'

describe('UploadStatusPanel', () => {
  it('shows upload success state', () => {
    render(
      <UploadStatusPanel
        isUploading={false}
        lastUpload={{
          document_id: 'doc-1',
          filename: 'Policy.pdf',
          status: DocumentStatus.Searchable,
          message: 'Uploaded',
        }}
      />,
    )

    expect(screen.getByText('Policy.pdf')).toBeInTheDocument()
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByText(/Document is ready for search/i)).toBeInTheDocument()
  })
})
