import { useCallback, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'
import { useUploadDocument } from '@/features/documents/hooks'
import {
  lifecycleStateFromUploadResponse,
  logUploadTransition,
  type UploadLifecycleState,
} from '@/features/documents/utils/uploadLifecycleDebug'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

import DocumentUploadForm, {
  type BatchUploadFileStatus,
  type BatchUploadProgressItem,
} from '../components/DocumentUploadForm'
import RecentUploadsTable from '../components/RecentUploadsTable'
import { useRecentUploads } from '../hooks/useRecentUploads'
import type { AdminDocumentRow } from '../utils/documentFilters'

function resolveLoadError(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Unable to load uploads.'
}

function toUiBatchStatus(lifecycle: UploadLifecycleState): BatchUploadFileStatus {
  if (lifecycle === 'Completed' || lifecycle === 'Indexed') return 'ready'
  if (lifecycle === 'Failed') return 'failed'
  if (lifecycle === 'Uploading') return 'uploading'
  return 'processing'
}

function createProgressItem(file: File, index: number): BatchUploadProgressItem {
  return {
    id: `${file.name}-${file.lastModified}-${index}`,
    filename: file.name,
    size: file.size,
    status: 'queued',
  }
}

export default function AdminUploadsPage() {
  const { showSuccess, showError } = useToast()
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState<BatchUploadProgressItem[]>([])
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
  const isUploading = uploadDocument.isPending

  const updateProgressItem = useCallback(
    (id: string, patch: Partial<BatchUploadProgressItem>) => {
      setUploadProgress((current) =>
        current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
      )
    },
    [],
  )

  async function handleUpload(files: File[]) {
    if (isUploading || files.length === 0) return

    logUploadTransition('AdminUploadsPage', 'Uploading', {
      fileCount: files.length,
      filenames: files.map((file) => file.name),
    })

    setUploadError(null)
    const progressItems = files.map(createProgressItem)
    setUploadProgress(progressItems)

    let successCount = 0

    for (const [index, file] of files.entries()) {
      const item = progressItems[index]
      if (!item) continue

      logUploadTransition('AdminUploadsPage', 'Uploading', {
        filename: file.name,
        batchIndex: index + 1,
        batchTotal: files.length,
      })
      updateProgressItem(item.id, { status: 'uploading', error: undefined })

      try {
        const result = await uploadDocument.mutateAsync(file)
        const lifecycle = lifecycleStateFromUploadResponse(result)
        logUploadTransition('AdminUploadsPage', lifecycle, {
          filename: file.name,
          documentId: result.document_id,
          backendStatus: result.status,
          message: result.message,
        })
        updateProgressItem(item.id, {
          status: toUiBatchStatus(lifecycle),
        })
        successCount += 1
      } catch (uploadFailure) {
        const message = getApiErrorMessage(uploadFailure) || 'Unable to upload document.'
        logUploadTransition('AdminUploadsPage', 'Failed', {
          filename: file.name,
          errorMessage: message,
        })
        updateProgressItem(item.id, { status: 'failed', error: message })
      }
    }

    void refetch()

    if (successCount === files.length) {
      logUploadTransition('AdminUploadsPage', 'Completed', {
        uploadedCount: successCount,
      })
      showSuccess(
        successCount === 1
          ? 'Document uploaded successfully.'
          : `${successCount} documents uploaded successfully.`,
      )
      setFormResetKey((current) => current + 1)
    } else if (successCount > 0) {
      showSuccess(`${successCount} of ${files.length} documents uploaded.`)
      setFormResetKey((current) => current + 1)
    } else {
      const message = 'Unable to upload documents. Check individual file errors below.'
      logUploadTransition('AdminUploadsPage', 'Failed', {
        uploadedCount: successCount,
        totalCount: files.length,
        errorMessage: message,
      })
      setUploadError(message)
      showError(message)
    }
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
        onUpload={(files) => void handleUpload(files)}
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
