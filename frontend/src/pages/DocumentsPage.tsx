import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

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
  DocumentDomainFilters,
  DocumentListPagination,
  DocumentTable,
  DocumentUploadDialog,
} from '@/features/documents/components'
import { ALL_DOMAINS_VALUE } from '@/features/documents/components/DocumentDomainFilters'
import { useDeleteDocument } from '@/features/documents/hooks/useDeleteDocument'
import { useDebouncedValue } from '@/features/documents/hooks/useDebouncedValue'
import {
  formatUploadBatchSummary,
  useUploadDocuments,
} from '@/features/documents/hooks/useUploadDocuments'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import { useUpdateDocumentDomain } from '@/features/documents/hooks/useUpdateDocumentDomain'
import type { Document } from '@/features/documents/types'
import {
  DUPLICATE_HIGHLIGHT_MS,
  resolveHighlightDocumentId,
} from '@/features/documents/utils/duplicateHighlight'
import { useKnowledgeDomains } from '@/features/knowledge-domains'
import { getApiErrorMessage, resolveErrorMessage } from '@/services/errorHandler'
import { Permission, hasPermission, isAdminUser } from '@/types/permissions'

const PAGE_SIZE = 50

export default function DocumentsPage() {
  const { user } = useAuth()
  const { showSuccess, showError } = useToast()
  const canUpload = hasPermission(user, Permission.DocumentCreate)
  const canEditDomain = isAdminUser(user)
  const [searchParams, setSearchParams] = useSearchParams()

  const domainIdFromUrl = searchParams.get('domain_id') ?? ALL_DOMAINS_VALUE
  const filenameFromUrl = searchParams.get('filename') ?? ''
  const pageFromUrl = Math.max(Number(searchParams.get('page') ?? '1') || 1, 1)

  const [searchInput, setSearchInput] = useState(filenameFromUrl)
  const debouncedSearch = useDebouncedValue(searchInput, 300)

  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSummary, setUploadSummary] = useState<string | null>(null)
  const [highlightedDocumentId, setHighlightedDocumentId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const domainsQuery = useKnowledgeDomains()
  const domains = domainsQuery.data ?? []

  const selectedDomainName = useMemo(() => {
    if (!domainIdFromUrl) return null
    return domains.find((domain) => domain.id === domainIdFromUrl)?.name ?? null
  }, [domainIdFromUrl, domains])

  const offset = (pageFromUrl - 1) * PAGE_SIZE
  const { data, isLoading, isFetching, isError, error } = useDocuments({
    limit: PAGE_SIZE,
    offset,
    ...(debouncedSearch.trim() ? { filename: debouncedSearch.trim() } : {}),
    ...(domainIdFromUrl ? { domain_id: domainIdFromUrl } : {}),
  })
  const { items: uploadProgress, isUploading, uploadFiles, retryFailed, reset } =
    useUploadDocuments()
  const deleteDocument = useDeleteDocument()
  const updateDocumentDomain = useUpdateDocumentDomain()

  const documents = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const showTableLoading = isLoading || (isFetching && documents.length === 0)

  useEffect(() => {
    setSearchInput(filenameFromUrl)
  }, [filenameFromUrl])

  useEffect(() => {
    const trimmed = debouncedSearch.trim()
    const currentFilename = searchParams.get('filename') ?? ''
    if (currentFilename === trimmed) {
      return
    }

    const next = new URLSearchParams(searchParams)
    if (trimmed) {
      next.set('filename', trimmed)
    } else {
      next.delete('filename')
    }
    // Reset to page 1 when the applied search changes.
    next.delete('page')
    setSearchParams(next, { replace: true })
  }, [debouncedSearch, searchParams, setSearchParams])

  useEffect(() => {
    if (!highlightedDocumentId) return
    const timer = window.setTimeout(() => {
      setHighlightedDocumentId(null)
    }, DUPLICATE_HIGHLIGHT_MS)
    return () => window.clearTimeout(timer)
  }, [highlightedDocumentId])

  function updateParams(mutator: (params: URLSearchParams) => void) {
    const next = new URLSearchParams(searchParams)
    mutator(next)
    setSearchParams(next, { replace: true })
  }

  function handleFilterDomainChange(nextDomainId: string) {
    updateParams((params) => {
      if (nextDomainId) {
        params.set('domain_id', nextDomainId)
      } else {
        params.delete('domain_id')
      }
      params.delete('page')
    })
  }

  function handleSearchChange(value: string) {
    setSearchInput(value)
  }

  function handlePageChange(nextPage: number) {
    updateParams((params) => {
      if (nextPage <= 1) {
        params.delete('page')
      } else {
        params.set('page', String(nextPage))
      }
    })
  }

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

  async function handleUpload(files: File[], domainId: string) {
    setUploadError(null)
    setUploadSummary(
      files.length === 1 ? '1 file selected — uploading…' : `${files.length} files selected — uploading…`,
    )

    const result = await uploadFiles(files, domainId)
    if (result.total === 0) return

    const summary = formatUploadBatchSummary(result)
    setUploadSummary(summary)

    if (result.failureCount === 0 && result.duplicateCount === 0) {
      showSuccess(
        result.successCount === 1
          ? 'Document uploaded successfully.'
          : `${result.successCount} documents uploaded successfully.`,
      )
      closeUpload()
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
      closeUpload()
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

  async function handleDocumentDomainChange(document: Document, domainId: string | null) {
    const previousDomainId = document.domain_id ?? null
    if (previousDomainId === domainId) return

    try {
      await updateDocumentDomain.mutateAsync({
        documentId: document.document_id,
        domainId,
      })
      showSuccess('Document domain updated.')
    } catch (domainFailure) {
      const message = getApiErrorMessage(domainFailure)
      showError(message)
      throw domainFailure
    }
  }

  const hasActiveFilters = Boolean(domainIdFromUrl) || Boolean(debouncedSearch.trim())
  const emptyTitle = domainIdFromUrl
    ? `No documents found in ${selectedDomainName ?? 'this domain'}.`
    : debouncedSearch.trim()
      ? 'No documents match your search'
      : 'No documents uploaded yet'
  const emptyDescription = domainIdFromUrl
    ? 'Try another domain, clear the filter, or upload a document to this domain.'
    : debouncedSearch.trim()
      ? 'Try a different search term or clear the domain filter.'
      : 'Upload your first document to make it available for knowledge search and chat.'

  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-4"
      data-testid="documents-page"
    >
      <div className="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
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

      <div className="shrink-0">
        <DocumentDomainFilters
          search={searchInput}
          onSearchChange={handleSearchChange}
          domainId={domainIdFromUrl}
          onDomainChange={handleFilterDomainChange}
          domains={domains}
          domainsLoading={domainsQuery.isLoading}
        />
      </div>

      {isError && (
        <Card>
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {resolveErrorMessage(error, 'Something went wrong. Please try again.')}
          </p>
        </Card>
      )}

      {!isError && !showTableLoading && documents.length === 0 ? (
        <Card>
          <EmptyState
            title={emptyTitle}
            description={emptyDescription}
            action={
              canUpload && !hasActiveFilters ? (
                <Button size="sm" onClick={openUpload}>
                  Upload your first document
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
          <DocumentTable
            documents={documents}
            isLoading={showTableLoading}
            highlightedDocumentId={highlightedDocumentId}
            domains={domains}
            canEditDomain={canEditDomain}
            updatingDomainDocumentId={
              updateDocumentDomain.isPending
                ? (updateDocumentDomain.variables?.documentId ?? null)
                : null
            }
            onDomainChange={handleDocumentDomainChange}
            onDownload={(document) => void handleDownload(document)}
            onDelete={openDelete}
          />
          <div className="shrink-0">
            <DocumentListPagination
              page={Math.min(pageFromUrl, totalPages)}
              totalPages={totalPages}
              totalResults={total}
              onPrevious={() => handlePageChange(Math.max(pageFromUrl - 1, 1))}
              onNext={() => handlePageChange(Math.min(pageFromUrl + 1, totalPages))}
            />
          </div>
        </div>
      )}

      {canUpload ? (
        <DocumentUploadDialog
          isOpen={uploadOpen}
          isUploading={isUploading}
          error={uploadError}
          uploadProgress={uploadProgress}
          summary={uploadSummary}
          onClose={closeUpload}
          onUpload={(files, domainId) => void handleUpload(files, domainId)}
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
