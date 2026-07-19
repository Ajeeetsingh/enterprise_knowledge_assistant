import { useEffect, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import EmptyState from '@/components/ui/EmptyState'
import { useAuth } from '@/contexts/AuthContext'
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
import {
  formatUploadBatchSummary,
  useUploadDocuments,
} from '@/features/documents/hooks/useUploadDocuments'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import type { Document } from '@/features/documents/types'
import {
  DUPLICATE_HIGHLIGHT_MS,
  resolveHighlightDocumentId,
} from '@/features/documents/utils/duplicateHighlight'
import { getApiErrorMessage, resolveErrorMessage } from '@/services/errorHandler'
import { Permission, hasPermission } from '@/types/permissions'

export default function DocumentsPage() {
  const { user } = useAuth()
  const { showSuccess, showError } = useToast()
  const canUpload = hasPermission(user, Permission.DocumentCreate)

  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSummary, setUploadSummary] = useState<string | null>(null)
  const [highlightedDocumentId, setHighlightedDocumentId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useDocuments()
  const { items: uploadProgress, isUploading, uploadFiles, retryFailed, reset } =
    useUploadDocuments()
  const deleteDocument = useDeleteDocument()

  const documents = data?.items ?? []
  const total = data?.total ?? 0

  useEffect(() => {
    if (!highlightedDocumentId) return
    const timer = window.setTimeout(() => {
      setHighlightedDocumentId(null)
    }, DUPLICATE_HIGHLIGHT_MS)
    return () => window.clearTimeout(timer)
  }, [highlightedDocumentId])

  function openUpload() {
    if (!canUpload) return
    setUploadError(null)
    setUploadSummary(null)
    reset()
    setUploadOpen(true)
  }

  function closeUpload() {
    if (isUploading) return
    const highlightId = resolveHighlightDocumentId(uploadProgress, documents)
    setUploadOpen(false)
    setUploadError(null)
    setUploadSummary(null)
    reset()
    if (highlightId) {
      setHighlightedDocumentId(highlightId)
    }
  }

  async function handleUpload(files: File[]) {
    setUploadError(null)
    setUploadSummary(
      files.length === 1 ? '1 file selected — uploading…' : `${files.length} files selected — uploading…`,
    )

    const result = await uploadFiles(files)
    if (result.total === 0) return

    const summary = formatUploadBatchSummary(result)
    setUploadSummary(summary)

    if (result.failureCount === 0 && result.duplicateCount === 0) {
      showSuccess(
        result.successCount === 1
          ? 'Document uploaded successfully.'
          : `${result.successCount} documents uploaded successfully.`,
      )
      return
    }

    if (result.successCount > 0) {
      showSuccess(summary)
      return
    }

    if (result.duplicateCount > 0 && result.failureCount === 0) {
      // Expected business condition — not a system failure.
      setUploadError(null)
      return
    }

    const message = 'Unable to upload documents. Check individual file errors below.'
    setUploadError(message)
    showError(message)
  }

  async function handleRetryFailed() {
    setUploadError(null)
    const result = await retryFailed()
    if (!result) return

    const summary = formatUploadBatchSummary(result)
    setUploadSummary(summary)

    if (result.failureCount === 0 && result.duplicateCount === 0) {
      showSuccess(
        result.successCount === 1
          ? 'Document uploaded successfully.'
          : `${result.successCount} documents uploaded successfully.`,
      )
      return
    }

    if (result.successCount > 0) {
      showSuccess(summary)
      return
    }

    setUploadError('Retry failed. Check individual file errors below.')
    showError('Retry failed. Check individual file errors below.')
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
          {canUpload ? <Button onClick={openUpload}>Upload documents</Button> : null}
        </div>
      </div>

      {isError && (
        <Card>
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {resolveErrorMessage(error, 'Something went wrong. Please try again.')}
          </p>
        </Card>
      )}

      {!isError && !isLoading && documents.length === 0 ? (
        <Card>
          <EmptyState
            title="No documents uploaded yet"
            description="Upload your first document to make it available for knowledge search and chat."
            action={
              canUpload ? (
                <Button size="sm" onClick={openUpload}>
                  Upload your first document
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <DocumentTable
          documents={documents}
          isLoading={isLoading}
          highlightedDocumentId={highlightedDocumentId}
          onDownload={(document) => void handleDownload(document)}
          onDelete={openDelete}
        />
      )}

      {canUpload ? (
        <DocumentUploadDialog
          isOpen={uploadOpen}
          isUploading={isUploading}
          error={uploadError}
          uploadProgress={uploadProgress}
          summary={uploadSummary}
          onClose={closeUpload}
          onUpload={(files) => void handleUpload(files)}
          onRetryFailed={() => void handleRetryFailed()}
        />
      ) : null}

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
