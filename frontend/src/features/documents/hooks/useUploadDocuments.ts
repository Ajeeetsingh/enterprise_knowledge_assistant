import { useCallback, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { chatQueryKeys } from '@/features/chat/hooks/queryKeys'
import {
  DUPLICATE_DOCUMENT_USER_MESSAGE,
  getApiErrorMessage,
  isDuplicateDocumentError,
} from '@/services/errorHandler'
import { toApiError } from '@/utils/apiError'

import { MAX_CONCURRENT_UPLOADS } from '../constants'
import * as documentApi from '../services/documentApi'
import { sha256Hex } from '../utils/fileChecksum'
import { mapWithConcurrency } from '../utils/uploadConcurrency'
import {
  lifecycleStateFromUploadResponse,
  logUploadTransition,
  type UploadLifecycleState,
} from '../utils/uploadLifecycleDebug'
import { documentQueryKeys } from './queryKeys'

export type BatchUploadItemStatus =
  | 'queued'
  | 'uploading'
  | 'processing'
  | 'completed'
  | 'duplicate'
  | 'failed'

export interface BatchUploadItem {
  id: string
  file: File
  filename: string
  size: number
  status: BatchUploadItemStatus
  error?: string
  documentId?: string
  /** Authorized public ID of an existing document when status is duplicate. */
  existingDocumentId?: string
}

export interface UploadDocumentsResult {
  successCount: number
  failureCount: number
  duplicateCount: number
  total: number
  items: BatchUploadItem[]
}

function toProgressItem(file: File, index: number): BatchUploadItem {
  return {
    id: `${file.name}-${file.size}-${file.lastModified}-${index}`,
    file,
    filename: file.name,
    size: file.size,
    status: 'queued',
  }
}

function statusFromLifecycle(lifecycle: UploadLifecycleState): BatchUploadItemStatus {
  if (lifecycle === 'Failed') return 'failed'
  if (lifecycle === 'Processing') return 'processing'
  return 'completed'
}

function patchItem(
  items: BatchUploadItem[],
  id: string,
  patch: Partial<BatchUploadItem>,
): BatchUploadItem[] {
  return items.map((item) => (item.id === id ? { ...item, ...patch } : item))
}

function emptyResult(total: number): UploadDocumentsResult {
  return {
    successCount: 0,
    failureCount: 0,
    duplicateCount: 0,
    total,
    items: [],
  }
}

/**
 * Mark later batch items that share content with an earlier item as duplicates
 * before any network request is made.
 */
async function markInBatchContentDuplicates(
  items: BatchUploadItem[],
): Promise<BatchUploadItem[]> {
  const seen = new Map<string, string>()
  const next: BatchUploadItem[] = []

  for (const item of items) {
    const hash = await sha256Hex(item.file)
    const firstName = seen.get(hash)
    if (firstName) {
      next.push({
        ...item,
        status: 'duplicate',
        error: `${item.filename} is already selected.`,
      })
      continue
    }
    seen.set(hash, item.filename)
    next.push(item)
  }

  return next
}

export function formatUploadBatchSummary(result: UploadDocumentsResult): string {
  if (
    result.successCount === 0 &&
    result.failureCount === 0 &&
    result.duplicateCount > 0
  ) {
    return result.duplicateCount === 1
      ? 'No new documents were uploaded. The selected document already exists.'
      : 'No new documents were uploaded. The selected documents already exist.'
  }

  const parts: string[] = []
  if (result.successCount > 0) {
    parts.push(
      result.successCount === 1
        ? '1 uploaded successfully'
        : `${result.successCount} uploaded successfully`,
    )
  }
  if (result.duplicateCount > 0) {
    parts.push(
      result.duplicateCount === 1
        ? '1 already exists'
        : `${result.duplicateCount} already exist`,
    )
  }
  if (result.failureCount > 0) {
    parts.push(result.failureCount === 1 ? '1 failed' : `${result.failureCount} failed`)
  }
  if (parts.length === 0) {
    return `0 of ${result.total} uploaded successfully`
  }
  return parts.join(' · ')
}

export function useUploadDocuments() {
  const queryClient = useQueryClient()
  const [items, setItems] = useState<BatchUploadItem[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const uploadingRef = useRef(false)

  const uploadFiles = useCallback(
    async (files: File[]): Promise<UploadDocumentsResult> => {
      if (uploadingRef.current || files.length === 0) {
        return emptyResult(files.length)
      }

      uploadingRef.current = true
      setIsUploading(true)

      let working = await markInBatchContentDuplicates(files.map(toProgressItem))
      setItems(working)

      const uploadable = working.filter((item) => item.status === 'queued')

      logUploadTransition('useUploadDocuments', 'Uploading', {
        fileCount: files.length,
        uploadableCount: uploadable.length,
        concurrency: MAX_CONCURRENT_UPLOADS,
        filenames: files.map((file) => file.name),
      })

      await mapWithConcurrency(
        uploadable,
        async (item) => {
          working = patchItem(working, item.id, { status: 'uploading' })
          setItems(working)

          try {
            const result = await documentApi.uploadDocument(item.file)
            const lifecycle = lifecycleStateFromUploadResponse(result)
            working = working.map((row) =>
              row.id === item.id
                ? {
                    id: row.id,
                    file: row.file,
                    filename: row.filename,
                    size: row.size,
                    status: statusFromLifecycle(lifecycle),
                    documentId: result.document_id,
                  }
                : row,
            )
            setItems(working)
            logUploadTransition('useUploadDocuments', lifecycle, {
              filename: item.filename,
              documentId: result.document_id,
              backendStatus: result.status,
            })
          } catch (error) {
            if (isDuplicateDocumentError(error)) {
              const apiError = toApiError(error)
              working = patchItem(working, item.id, {
                status: 'duplicate',
                error: DUPLICATE_DOCUMENT_USER_MESSAGE,
                ...(apiError.existingDocumentId
                  ? { existingDocumentId: apiError.existingDocumentId }
                  : {}),
              })
              setItems(working)
              logUploadTransition('useUploadDocuments', 'Uploaded', {
                filename: item.filename,
                errorMessage: DUPLICATE_DOCUMENT_USER_MESSAGE,
                duplicate: true,
                existingDocumentId: apiError.existingDocumentId,
              })
              return
            }

            const message = getApiErrorMessage(error) || 'Unable to upload document.'
            working = patchItem(working, item.id, { status: 'failed', error: message })
            setItems(working)
            logUploadTransition('useUploadDocuments', 'Failed', {
              filename: item.filename,
              errorMessage: message,
            })
          }
        },
        MAX_CONCURRENT_UPLOADS,
      )

      void queryClient.invalidateQueries({ queryKey: documentQueryKeys.list() })
      void queryClient.invalidateQueries({ queryKey: chatQueryKeys.suggestedQuestions() })

      uploadingRef.current = false
      setIsUploading(false)

      const successCount = working.filter(
        (item) => item.status === 'completed' || item.status === 'processing',
      ).length
      const failureCount = working.filter((item) => item.status === 'failed').length
      const duplicateCount = working.filter((item) => item.status === 'duplicate').length

      return {
        successCount,
        failureCount,
        duplicateCount,
        total: files.length,
        items: working,
      }
    },
    [queryClient],
  )

  const retryFailed = useCallback(async (): Promise<UploadDocumentsResult | null> => {
    const failedFiles = items
      .filter((item) => item.status === 'failed')
      .map((item) => item.file)
    if (failedFiles.length === 0) return null
    return uploadFiles(failedFiles)
  }, [items, uploadFiles])

  const reset = useCallback(() => {
    if (uploadingRef.current) return
    setItems([])
  }, [])

  return {
    items,
    isUploading,
    uploadFiles,
    retryFailed,
    reset,
  }
}
