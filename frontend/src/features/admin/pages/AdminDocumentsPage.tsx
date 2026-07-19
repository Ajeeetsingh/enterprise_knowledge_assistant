import { useEffect, useMemo, useState } from 'react'

import Button from '@/components/ui/Button'
import Card from '@/components/ui/Card'
import { useToast } from '@/contexts/ToastContext'
import DeleteDocumentDialog from '@/features/documents/components/DeleteDocumentDialog'
import { useDeleteDocument, useDocument, useDocuments } from '@/features/documents/hooks'
import type { Document } from '@/features/documents/types'
import { getApiErrorMessage, resolveErrorMessage } from '@/services/errorHandler'

import {
  ADMIN_DOCUMENTS_FETCH_LIMIT,
  ADMIN_DOCUMENTS_PAGE_SIZE,
} from '../constants/documents'
import DocumentDetailsModal from '../components/DocumentDetailsModal'
import DocumentFilters from '../components/DocumentFilters'
import DocumentPagination from '../components/DocumentPagination'
import DocumentsTable from '../components/DocumentsTable'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import {
  applyDocumentFilters,
  paginateDocuments,
  type AdminDocumentRow,
  type DocumentFilterState,
} from '../utils/documentFilters'

const DEFAULT_FILTERS: DocumentFilterState = {
  status: 'ALL',
  visibility: 'ALL',
}

export default function AdminDocumentsPage() {
  const { showSuccess, showError } = useToast()
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<DocumentFilterState>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)
  const [viewTargetId, setViewTargetId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const debouncedSearch = useDebouncedValue(search, 300)

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useDocuments({
    limit: ADMIN_DOCUMENTS_FETCH_LIMIT,
    offset: 0,
    ...(debouncedSearch.trim() ? { filename: debouncedSearch.trim() } : {}),
  })

  const deleteDocument = useDeleteDocument()

  const {
    data: documentDetail,
    isLoading: isDetailLoading,
    isError: isDetailError,
    error: detailError,
    refetch: refetchDetail,
  } = useDocument(viewTargetId, viewTargetId !== null)

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, filters.status, filters.visibility])

  const filteredDocuments = useMemo(() => {
    const items = (data?.items ?? []) as AdminDocumentRow[]
    return applyDocumentFilters(items, filters)
  }, [data?.items, filters])

  const pagination = useMemo(
    () => paginateDocuments(filteredDocuments, page, ADMIN_DOCUMENTS_PAGE_SIZE),
    [filteredDocuments, page],
  )

  function openView(document: AdminDocumentRow) {
    setViewTargetId(document.document_id)
  }

  function closeView() {
    setViewTargetId(null)
  }

  function openDelete(document: AdminDocumentRow) {
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
      const message = getApiErrorMessage(deleteFailure) || 'Unable to delete document.'
      setDeleteError(message)
      showError(message)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
            Documents Management
          </h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Search, inspect, and remove documents from the enterprise knowledge base.
          </p>
        </div>

        <p className="text-sm text-neutral-600 dark:text-neutral-300">
          <span className="font-medium">{pagination.total}</span> document
          {pagination.total === 1 ? '' : 's'}
        </p>
      </div>

      <DocumentFilters
        filters={filters}
        onChange={setFilters}
        search={search}
        onSearchChange={setSearch}
      />

      {isError && (
        <Card>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p role="alert" className="text-sm text-error-500 dark:text-error-400">
              {resolveErrorMessage(error, 'Unable to load documents.')}
            </p>
            <Button variant="secondary" size="sm" onClick={() => void refetch()}>
              Retry
            </Button>
          </div>
        </Card>
      )}

      {!isError && (
        <>
          <DocumentsTable
            documents={pagination.items}
            isLoading={isLoading}
            onView={openView}
            onDelete={openDelete}
          />

          {!isLoading && pagination.total > 0 && (
            <DocumentPagination
              page={pagination.page}
              totalPages={pagination.totalPages}
              totalResults={pagination.total}
              onPrevious={() => setPage((current) => Math.max(current - 1, 1))}
              onNext={() =>
                setPage((current) => Math.min(current + 1, pagination.totalPages))
              }
            />
          )}
        </>
      )}

      <DocumentDetailsModal
        isOpen={viewTargetId !== null}
        documentDetail={documentDetail ?? null}
        isLoading={isDetailLoading}
        error={
          isDetailError
            ? getApiErrorMessage(detailError) || 'Unable to load document details.'
            : null
        }
        onClose={closeView}
        onRetry={() => void refetchDetail()}
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
