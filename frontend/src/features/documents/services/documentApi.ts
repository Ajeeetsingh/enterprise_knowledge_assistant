/**
 * Document management API client (Phase 9.3).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import { UPLOAD_REQUEST_TIMEOUT_MS } from '../constants'
import type {
  Document,
  DocumentDeleteResponse,
  DocumentDetail,
  DocumentUploadResponse,
  PaginatedDocumentResponse,
} from '../types'
import type { DocumentListParams } from '../types/listParams'
import {
  lifecycleStateFromUploadResponse,
  logUploadTransition,
} from '../utils/uploadLifecycleDebug'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getDocuments(
  params: DocumentListParams = {},
): Promise<PaginatedDocumentResponse> {
  const { limit = 50, offset = 0, filename, status, domain_id } = params

  return request(async () => {
    const { data } = await apiClient.get<PaginatedDocumentResponse>('/documents', {
      params: {
        limit,
        offset,
        ...(filename ? { filename } : {}),
        ...(status ? { status } : {}),
        ...(domain_id ? { domain_id } : {}),
      },
    })
    return data
  })
}

export async function getDocument(documentId: string): Promise<DocumentDetail> {
  return request(async () => {
    const { data } = await apiClient.get<DocumentDetail>(`/documents/${documentId}`)
    return data
  })
}

export async function uploadDocument(
  file: File,
  domainId: string,
): Promise<DocumentUploadResponse> {
  const startedAt = performance.now()

  logUploadTransition('documentApi', 'Uploading', {
    filename: file.name,
    sizeBytes: file.size,
    timeoutMs: UPLOAD_REQUEST_TIMEOUT_MS,
    domainId,
  })

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('domain_id', domainId)
    const { data, status: httpStatus } = await apiClient.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      { timeout: UPLOAD_REQUEST_TIMEOUT_MS },
    )

    logUploadTransition('documentApi', lifecycleStateFromUploadResponse(data), {
      filename: file.name,
      documentId: data.document_id,
      backendStatus: data.status,
      message: data.message,
      elapsedMs: Math.round(performance.now() - startedAt),
      httpStatus,
    })

    return data
  } catch (error) {
    const apiError = toApiError(error)
    logUploadTransition('documentApi', 'Failed', {
      filename: file.name,
      elapsedMs: Math.round(performance.now() - startedAt),
      httpStatus: apiError.status,
      errorMessage: apiError.message,
      axiosCode:
        error && typeof error === 'object' && 'code' in error
          ? String((error as { code?: string }).code)
          : undefined,
    })
    throw apiError
  }
}

export async function deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
  return request(async () => {
    const { data } = await apiClient.delete<DocumentDeleteResponse>(
      `/documents/${documentId}`,
    )
    return data
  })
}

export async function updateDocumentDomain(
  documentId: string,
  domainId: string | null,
): Promise<Document> {
  return request(async () => {
    const { data } = await apiClient.patch<Document>(`/documents/${documentId}/domain`, {
      domain_id: domainId,
    })
    return data
  })
}
