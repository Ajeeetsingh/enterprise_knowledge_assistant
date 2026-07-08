import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import UploadStatusBadge from './UploadStatusBadge'

describe('UploadStatusBadge', () => {
  it('renders upload status labels', () => {
    const { rerender } = render(<UploadStatusBadge status="UPLOADING" />)
    expect(screen.getByText('Uploading')).toBeInTheDocument()

    rerender(<UploadStatusBadge status="PROCESSING" />)
    expect(screen.getByText('Processing')).toBeInTheDocument()

    rerender(<UploadStatusBadge status="READY" />)
    expect(screen.getByText('Ready')).toBeInTheDocument()

    rerender(<UploadStatusBadge status="FAILED" />)
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })
})
