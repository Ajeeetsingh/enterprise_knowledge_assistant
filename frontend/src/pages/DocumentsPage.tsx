import { useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import { useToast } from '@/contexts/ToastContext'
import {
  fetchDocumentFileBlob,
  triggerBlobDownload,
} from '@/features/document-viewer/services/documentFileApi'
import {
  DeleteDocumentDialog,
  DocumentTable,
  DocumentUploadDialog,
} from '@/features/documents/components'
import { useDeleteDocument } from '@/features/documents/hooks/useDeleteDocument'
import { useUploadDocument } from '@/features/documents/hooks/useUploadDocument'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import {
  lifecycleStateFromUploadResponse,
  logUploadTransition,
} from '@/features/documents/utils/uploadLifecycleDebug'
import type { Document } from '@/features/documents/types'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

export default function DocumentsPage() {
  const { showSuccess, showError } = useToast()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useDocuments()
  const uploadDocument = useUploadDocument()
  const deleteDocument = useDeleteDocument()

  const documents = data?.items ?? []
  const total = data?.total ?? 0

  function openUpload() {
    setUploadError(null)
    setUploadOpen(true)
  }

  function closeUpload() {
    if (uploadDocument.isPending) return
    setUploadOpen(false)
    setUploadError(null)
  }

  async function handleUpload(file: File) {
    setUploadError(null)
    logUploadTransition('DocumentsPage', 'Uploading', { filename: file.name, sizeBytes: file.size })

    try {
      const result = await uploadDocument.mutateAsync(file)
      logUploadTransition('DocumentsPage', lifecycleStateFromUploadResponse(result), {
        filename: file.name,
        documentId: result.document_id,
        backendStatus: result.status,
      })
      setUploadOpen(false)
      showSuccess('Document uploaded successfully.')
    } catch (uploadFailure) {
      const message = getApiErrorMessage(uploadFailure)
      logUploadTransition('DocumentsPage', 'Failed', {
        filename: file.name,
        errorMessage: message,
      })
      setUploadError(message)
      showError(message)
    }
  }

  function openDelete(document: Document) {
    setDeleteError(null)
    setDeleteTarget(document)
  }

  function closeDelete() {
    if (deleteDocument.isPending) return
    setDeleteTarget(null)
    setDeleteError(null)
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleteError(null)
    try {
      await deleteDocument.mutateAsync(deleteTarget.document_id)
      setDeleteTarget(null)
      showSuccess('Document deleted successfully.')
    } catch (deleteFailure) {
      const message = getApiErrorMessage(deleteFailure)
      setDeleteError(message)
      showError(message)
    }
  }

  async function handleDownload(document: Document) {
    try {
      const blob = await fetchDocumentFileBlob(document.document_id, { download: true })
      triggerBlobDownload(blob, document.filename)
    } catch (downloadFailure) {
      showError(getApiErrorMessage(downloadFailure))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Documents</h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Manage enterprise knowledge documents for search and chat.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <p className="text-sm text-neutral-600 dark:text-neutral-300">
            <span className="font-medium">{total}</span> document{total === 1 ? '' : 's'}
          </p>
          <Button onClick={openUpload}>Upload document</Button>
        </div>
      </div>

      {isError && (
        <Card>
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {resolveErrorMessage(error)}
          </p>
        </Card>
      )}

      {!isError && !isLoading && documents.length === 0 ? (
        <Card>
          <EmptyState
            title="No documents uploaded yet"
            description="Upload your first document to make it available for knowledge search and chat."
            action={
              <Button size="sm" onClick={openUpload}>
                Upload your first document
              </Button>
            }
          />
        </Card>
      ) : (
        <DocumentTable
          documents={documents}
          isLoading={isLoading}
          onDownload={(document) => void handleDownload(document)}
          onDelete={openDelete}
        />
      )}

      <DocumentUploadDialog
        isOpen={uploadOpen}
        isUploading={uploadDocument.isPending}
        error={uploadError}
        onClose={closeUpload}
        onUpload={(file) => void handleUpload(file)}
      />

      <DeleteDocumentDialog
        targetDocument={deleteTarget}
        isOpen={deleteTarget !== null}
        isDeleting={deleteDocument.isPending}
        error={deleteError}
        onClose={closeDelete}
        onConfirm={() => void handleDeleteConfirm()}
      />
    </div>
  )
}
