/**
 * Document management API client (Phase 9.3).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  DocumentDeleteResponse,
  DocumentDetail,
  DocumentUploadResponse,
  PaginatedDocumentResponse,
} from '../types'
import type { DocumentListParams } from '../types/listParams'

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
  const { limit = 50, offset = 0, filename, status } = params

  return request(async () => {
    const { data } = await apiClient.get<PaginatedDocumentResponse>('/documents', {
      params: {
        limit,
        offset,
        ...(filename ? { filename } : {}),
        ...(status ? { status } : {}),
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

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  return request(async () => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await apiClient.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
    )
    return data
  })
}

export async function deleteDocument(documentId: string): Promise<DocumentDeleteResponse> {
  return request(async () => {
    const { data } = await apiClient.delete<DocumentDeleteResponse>(
      `/documents/${documentId}`,
    )
    return data
  })
}
