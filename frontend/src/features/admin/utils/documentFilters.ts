import type { Document } from '@/features/documents/types'
import { getStatusDisplay } from '@/features/documents/types'

export type AdminStatusFilter = 'ALL' | 'READY' | 'PROCESSING' | 'FAILED'
export type AdminVisibilityFilter = 'ALL' | 'PUBLIC' | 'PRIVATE' | 'ROLE_BASED'

export interface AdminDocumentRow extends Document {
  visibility?: string
}

export interface DocumentFilterState {
  status: AdminStatusFilter
  visibility: AdminVisibilityFilter
}

export function getDocumentType(filename: string): string {
  const extension = filename.split('.').pop()?.trim()
  if (!extension) return 'UNKNOWN'
  return extension.toUpperCase()
}

export function mapVisibilityDisplay(visibility?: string): string {
  if (!visibility) return '—'

  switch (visibility.toLowerCase()) {
    case 'public':
      return 'PUBLIC'
    case 'private':
      return 'PRIVATE'
    case 'restricted':
      return 'ROLE_BASED'
    default:
      return visibility.toUpperCase()
  }
}

export function filterDocumentsBySearch(
  documents: AdminDocumentRow[],
  search: string,
): AdminDocumentRow[] {
  const query = search.trim().toLowerCase()
  if (!query) return documents

  return documents.filter((document) => document.filename.toLowerCase().includes(query))
}

export function filterDocumentsByStatus(
  documents: AdminDocumentRow[],
  status: AdminStatusFilter,
): AdminDocumentRow[] {
  if (status === 'ALL') return documents

  return documents.filter((document) => getStatusDisplay(document.status) === status)
}

export function filterDocumentsByVisibility(
  documents: AdminDocumentRow[],
  visibility: AdminVisibilityFilter,
): AdminDocumentRow[] {
  if (visibility === 'ALL') return documents

  const target = visibility === 'ROLE_BASED' ? 'restricted' : visibility.toLowerCase()

  return documents.filter((document) => {
    if (!document.visibility) return true
    return document.visibility.toLowerCase() === target
  })
}

export function applyDocumentFilters(
  documents: AdminDocumentRow[],
  filters: DocumentFilterState,
  search = '',
): AdminDocumentRow[] {
  let result = filterDocumentsBySearch(documents, search)
  result = filterDocumentsByStatus(result, filters.status)
  result = filterDocumentsByVisibility(result, filters.visibility)
  return result
}

export interface PaginatedSlice<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export function paginateDocuments<T>(
  documents: T[],
  page: number,
  pageSize: number,
): PaginatedSlice<T> {
  const total = documents.length
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const safePage = Math.min(Math.max(page, 1), totalPages)
  const start = (safePage - 1) * pageSize

  return {
    items: documents.slice(start, start + pageSize),
    total,
    page: safePage,
    pageSize,
    totalPages,
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
