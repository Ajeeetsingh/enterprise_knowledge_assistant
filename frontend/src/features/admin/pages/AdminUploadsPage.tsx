import { useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'
import {
  formatUploadBatchSummary,
  useUploadDocuments,
} from '@/features/documents/hooks/useUploadDocuments'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

import DocumentUploadForm from '../components/DocumentUploadForm'
import RecentUploadsTable from '../components/RecentUploadsTable'
import { useRecentUploads } from '../hooks/useRecentUploads'
import type { AdminDocumentRow } from '../utils/documentFilters'

function resolveLoadError(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Unable to load uploads.'
}

export default function AdminUploadsPage() {
  const { showSuccess, showError } = useToast()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSummary, setUploadSummary] = useState<string | null>(null)
  const [formResetKey, setFormResetKey] = useState(0)

  const { items: uploadProgress, isUploading, uploadFiles, retryFailed, reset } =
    useUploadDocuments()
  const {
    data,
    isLoading,
    isError,
    error,
    isFetching,
    refetch,
  } = useRecentUploads()

  const recentUploads = (data?.items ?? []) as AdminDocumentRow[]

  async function handleUpload(files: File[]) {
    if (isUploading || files.length === 0) return

    setUploadError(null)
    setUploadSummary(
      files.length === 1 ? '1 file selected — uploading…' : `${files.length} files selected — uploading…`,
    )

    const result = await uploadFiles(files)
    void refetch()

    const summary = formatUploadBatchSummary(result)
    setUploadSummary(summary)

    if (result.failureCount === 0 && result.duplicateCount === 0) {
      showSuccess(
        result.successCount === 1
          ? 'Document uploaded successfully.'
          : `${result.successCount} documents uploaded successfully.`,
      )
      setFormResetKey((current) => current + 1)
      reset()
      setUploadSummary(null)
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
    void refetch()

    const summary = formatUploadBatchSummary(result)
    setUploadSummary(summary)

    if (result.failureCount === 0 && result.duplicateCount === 0) {
      showSuccess(
        result.successCount === 1
          ? 'Document uploaded successfully.'
          : `${result.successCount} documents uploaded successfully.`,
      )
      setFormResetKey((current) => current + 1)
      reset()
      setUploadSummary(null)
      return
    }

    if (result.successCount > 0) {
      showSuccess(summary)
      return
    }

    setUploadError('Retry failed. Check individual file errors below.')
    showError(getApiErrorMessage(new Error('Retry failed')) || 'Retry failed.')
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-foreground">Upload Center</h2>
        <p className="mt-1 text-sm text-muted">
          Add enterprise documents to the knowledge base and monitor ingestion status.
        </p>
      </div>

      <DocumentUploadForm
        isUploading={isUploading}
        error={uploadError}
        resetKey={formResetKey}
        uploadProgress={uploadProgress}
        summary={uploadSummary}
        onUpload={(files) => void handleUpload(files)}
        onRetryFailed={() => void handleRetryFailed()}
      />

      {isError && (
        <Card>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p role="alert" className="text-sm text-status-bad">
              {resolveLoadError(error)}
            </p>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              Retry
            </Button>
          </div>
        </Card>
      )}

      {!isError && (
        <RecentUploadsTable
          uploads={recentUploads}
          isLoading={isLoading}
          isRefreshing={isFetching && !isLoading}
        />
      )}
    </div>
  )
}
