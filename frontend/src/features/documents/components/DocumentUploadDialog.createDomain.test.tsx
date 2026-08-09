import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { type ComponentProps } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/features/knowledge-domains/services/knowledgeDomainApi', () => ({
  listKnowledgeDomains: vi.fn(),
  createKnowledgeDomain: vi.fn(),
}))

import * as knowledgeDomainApi from '@/features/knowledge-domains/services/knowledgeDomainApi'

import DocumentUploadDialog from './DocumentUploadDialog'

const FINANCE = { id: 'domain-finance', name: 'Finance', description: null }
const NEW_DOMAIN = {
  id: 'domain-finance-ops',
  name: 'Finance Operations',
  description: null,
}

function renderDialog(props: Partial<ComponentProps<typeof DocumentUploadDialog>> = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const onClose = vi.fn()
  const onUpload = vi.fn()
  const view = render(
    <QueryClientProvider client={client}>
      <DocumentUploadDialog
        isOpen
        isUploading={false}
        error={null}
        onClose={onClose}
        onUpload={onUpload}
        {...props}
      />
    </QueryClientProvider>,
  )
  return { ...view, onClose, onUpload }
}

describe('DocumentUploadDialog + Create Domain architecture', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(knowledgeDomainApi.listKnowledgeDomains)
      .mockResolvedValueOnce([FINANCE])
      .mockResolvedValue([FINANCE, NEW_DOMAIN])
    vi.mocked(knowledgeDomainApi.createKnowledgeDomain).mockResolvedValue(NEW_DOMAIN)
  })

  it('keeps Upload dialog open and preserves files after Create Domain succeeds', async () => {
    const user = userEvent.setup()
    const { onClose, onUpload } = renderDialog()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const files = [
      new File(['a'], 'file1.pdf', { type: 'application/pdf' }),
      new File(['b'], 'file2.pdf', { type: 'application/pdf' }),
    ]
    await user.upload(input, files)
    expect(await screen.findByText('file1.pdf')).toBeInTheDocument()
    expect(screen.getByText('file2.pdf')).toBeInTheDocument()

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')

    const createDialog = await screen.findByTestId('create-knowledge-domain-dialog')
    expect(createDialog).toBeInTheDocument()
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()

    await user.type(within(createDialog).getByLabelText('Domain Name'), 'Finance Operations')
    await user.click(within(createDialog).getByRole('button', { name: 'Create' }))

    await waitFor(() => {
      expect(knowledgeDomainApi.createKnowledgeDomain).toHaveBeenCalledWith({
        name: 'Finance Operations',
        description: null,
      })
    })
    await waitFor(() => {
      expect(screen.queryByTestId('create-knowledge-domain-dialog')).not.toBeInTheDocument()
    })

    // Parent upload dialog must remain open; files preserved; new domain selected.
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
    expect(screen.getByText('file1.pdf')).toBeInTheDocument()
    expect(screen.getByText('file2.pdf')).toBeInTheDocument()
    expect(screen.getByLabelText('Knowledge Domain')).toHaveValue(NEW_DOMAIN.id)
    expect(onClose).not.toHaveBeenCalled()
    expect(onUpload).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Upload 2 files' }))
    expect(onUpload).toHaveBeenCalledWith(files, NEW_DOMAIN.id)
  })

  it('supports Create Domain before file selection without closing Upload', async () => {
    const user = userEvent.setup()
    const { onClose, onUpload } = renderDialog()

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')

    const createDialog = await screen.findByTestId('create-knowledge-domain-dialog')
    await user.type(within(createDialog).getByLabelText('Domain Name'), 'Finance Operations')
    await user.click(within(createDialog).getByRole('button', { name: 'Create' }))

    await waitFor(() => {
      expect(screen.queryByTestId('create-knowledge-domain-dialog')).not.toBeInTheDocument()
    })
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
    expect(screen.getByLabelText('Knowledge Domain')).toHaveValue(NEW_DOMAIN.id)
    expect(onClose).not.toHaveBeenCalled()
    expect(onUpload).not.toHaveBeenCalled()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['x'], 'later.pdf', { type: 'application/pdf' })
    await user.upload(input, [file])
    await user.click(await screen.findByRole('button', { name: 'Upload' }))
    expect(onUpload).toHaveBeenCalledWith([file], NEW_DOMAIN.id)
  })

  it('Escape while Create Domain is open closes only Create Domain', async () => {
    const user = userEvent.setup()
    const { onClose } = renderDialog()

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')
    expect(await screen.findByTestId('create-knowledge-domain-dialog')).toBeInTheDocument()

    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.queryByTestId('create-knowledge-domain-dialog')).not.toBeInTheDocument()
    })
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('Create Domain modal is portaled outside the Upload form', async () => {
    const user = userEvent.setup()
    renderDialog()

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')

    const createDialog = await screen.findByTestId('create-knowledge-domain-dialog')
    const uploadForm = screen.getByTestId('document-upload-dialog').querySelector('form')
    expect(uploadForm).not.toBeNull()
    expect(uploadForm!.contains(createDialog)).toBe(false)
    expect(document.body.contains(createDialog)).toBe(true)
  })

  it('pointerdown on Create buttons does not close the Upload dialog via backdrop', async () => {
    const user = userEvent.setup()
    const { onClose } = renderDialog()

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')
    const createDialog = await screen.findByTestId('create-knowledge-domain-dialog')

    // Simulate the dangerous click-through sequence: Create succeeds and unmounts;
    // a leftover click lands on the upload backdrop. Backdrop uses pointerdown,
    // so a late click must not close Upload.
    await user.type(within(createDialog).getByLabelText('Domain Name'), 'Finance Operations')
    await user.click(within(createDialog).getByRole('button', { name: 'Create' }))
    await waitFor(() => {
      expect(screen.queryByTestId('create-knowledge-domain-dialog')).not.toBeInTheDocument()
    })

    fireEvent.click(screen.getByTestId('document-upload-backdrop'))
    expect(onClose).not.toHaveBeenCalled()
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
  })

  it('preserves upload state when Create Domain fails', async () => {
    const user = userEvent.setup()
    vi.mocked(knowledgeDomainApi.createKnowledgeDomain).mockRejectedValueOnce(
      new Error('Domain already exists'),
    )
    const { onClose, onUpload } = renderDialog()

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const files = [
      new File(['a'], 'keep1.pdf', { type: 'application/pdf' }),
      new File(['b'], 'keep2.pdf', { type: 'application/pdf' }),
    ]
    await user.upload(input, files)

    const domainSelect = await screen.findByLabelText('Knowledge Domain')
    await user.selectOptions(domainSelect, '__create_new__')
    const createDialog = await screen.findByTestId('create-knowledge-domain-dialog')
    await user.type(within(createDialog).getByLabelText('Domain Name'), 'Finance Operations')
    await user.click(within(createDialog).getByRole('button', { name: 'Create' }))

    expect(await within(createDialog).findByRole('alert')).toBeInTheDocument()
    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
    expect(screen.getByText('keep1.pdf')).toBeInTheDocument()
    expect(screen.getByText('keep2.pdf')).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
    expect(onUpload).not.toHaveBeenCalled()
  })

  it('keeps Upload open when parent reports upload error without closing', () => {
    const { onClose } = renderDialog({
      error: 'Unable to upload documents. Check individual file errors below.',
    })

    expect(screen.getByTestId('document-upload-dialog')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/Unable to upload/)
    expect(onClose).not.toHaveBeenCalled()
  })

  it('disables Upload without files even when a domain is selected', async () => {
    const user = userEvent.setup()
    renderDialog()
    await user.selectOptions(await screen.findByLabelText('Knowledge Domain'), FINANCE.id)
    expect(screen.getByRole('button', { name: 'Upload' })).toBeDisabled()
  })
})
