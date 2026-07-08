import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import DocumentUploadForm from './DocumentUploadForm'

describe('DocumentUploadForm', () => {
  it('renders upload form controls', () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    expect(screen.getByRole('heading', { name: 'Upload Document' })).toBeInTheDocument()
    expect(screen.getByLabelText('Document file')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
  })

  it('validates unsupported files', async () => {
    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={vi.fn()} />,
    )

    const input = screen.getByLabelText('Document file')
    const file = new File(['content'], 'bad.exe', { type: 'application/octet-stream' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(screen.getByRole('alert')).toHaveTextContent('Unsupported file type.')
  })

  it('disables upload button during upload', () => {
    render(
      <DocumentUploadForm isUploading error={null} onUpload={vi.fn()} />,
    )

    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
    expect(screen.getByText(/Uploading document to the knowledge base/i)).toBeInTheDocument()
  })

  it('shows upload error state', () => {
    render(
      <DocumentUploadForm
        isUploading={false}
        error="Unable to upload document."
        onUpload={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to upload document.')
  })

  it('submits valid files', async () => {
    const user = userEvent.setup()
    const onUpload = vi.fn()

    render(
      <DocumentUploadForm isUploading={false} error={null} onUpload={onUpload} />,
    )

    const file = new File(['content'], 'policy.pdf', { type: 'application/pdf' })
    await user.upload(screen.getByLabelText('Document file'), file)
    await user.click(screen.getByRole('button', { name: 'Upload' }))

    expect(onUpload).toHaveBeenCalledWith(file)
  })
})
