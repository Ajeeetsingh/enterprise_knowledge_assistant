import { useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'
import { useUploadDocument } from '@/features/documents/hooks'
import type { DocumentUploadResponse } from '@/features/documents/types'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

import DocumentUploadForm from '../components/DocumentUploadForm'
import RecentUploadsTable from '../components/RecentUploadsTable'
import UploadStatusPanel from '../components/UploadStatusPanel'
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
  const [lastUpload, setLastUpload] = useState<DocumentUploadResponse | null>(null)
  const [formResetKey, setFormResetKey] = useState(0)

  const uploadDocument = useUploadDocument()
  const {
    data,
    isLoading,
    isError,
    error,
    isFetching,
    refetch,
  } = useRecentUploads()

  const recentUploads = (data?.items ?? []) as AdminDocumentRow[]

  async function handleUpload(file: File) {
    if (uploadDocument.isPending) return

    setUploadError(null)
    setLastUpload(null)

    try {
      const result = await uploadDocument.mutateAsync(file)
      setLastUpload(result)
      setFormResetKey((current) => current + 1)
      showSuccess('Document uploaded successfully.')
    } catch (uploadFailure) {
      const message = getApiErrorMessage(uploadFailure) || 'Unable to upload document.'
      setUploadError(message)
      showError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Upload Center</h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Add enterprise documents to the knowledge base and monitor ingestion status.
        </p>
      </div>

      <DocumentUploadForm
        isUploading={uploadDocument.isPending}
        error={uploadError}
        resetKey={formResetKey}
        onUpload={(file) => void handleUpload(file)}
      />

      <UploadStatusPanel isUploading={uploadDocument.isPending} lastUpload={lastUpload} />

      {isError && (
        <Card>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
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
