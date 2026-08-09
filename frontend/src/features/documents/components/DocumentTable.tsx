import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

import ActionButton from '@/components/ui/ActionButton'
import Button from '@/components/ui/Button'
import type { KnowledgeDomain } from '@/features/knowledge-domains'
import { cn } from '@/utils/cn'

import { VISIBILITY_NOT_IN_LIST_API } from '../constants'
import type { Document } from '../types'
import { prefersReducedMotion } from '../utils/duplicateHighlight'
import DocumentDomainCell from './DocumentDomainCell'
import DocumentStatusBadge from './DocumentStatusBadge'

/** Floor width so columns stay readable; narrower viewports scroll horizontally. */
export const DOCUMENT_TABLE_MIN_WIDTH_PX = 1200

export interface DocumentTableProps {
  documents: Document[]
  isLoading: boolean
  highlightedDocumentId?: string | null
  domains?: KnowledgeDomain[]
  canEditDomain?: boolean
  updatingDomainDocumentId?: string | null
  onDomainChange?: (
    document: Document,
    domainId: string | null,
  ) => Promise<void> | void
  onView?: (document: Document) => void
  onDownload?: (document: Document) => void
  onDelete: (document: Document) => void
}

export default function DocumentTable({
  documents,
  isLoading,
  highlightedDocumentId = null,
  domains = [],
  canEditDomain = false,
  updatingDomainDocumentId = null,
  onDomainChange,
  onView,
  onDownload,
  onDelete,
}: DocumentTableProps) {
  const navigate = useNavigate()
  const rowRefs = useRef(new Map<string, HTMLTableRowElement>())

  useEffect(() => {
    if (!highlightedDocumentId) return
    const row = rowRefs.current.get(highlightedDocumentId)
    if (!row) return

    const reduceMotion = prefersReducedMotion()
    row.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
      block: 'nearest',
    })
  }, [highlightedDocumentId])

  function handleView(document: Document) {
    if (onView) {
      onView(document)
      return
    }
    navigate(`/documents/${document.document_id}`)
  }

  if (isLoading) {
    return (
      <div
        className="min-h-0 min-w-0 flex-1 space-y-3"
        aria-busy="true"
        aria-label="Loading documents"
        data-testid="document-table-loading"
      >
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-12 animate-pulse rounded-md bg-neutral-200 dark:bg-neutral-800"
          />
        ))}
      </div>
    )
  }

  return (
    <div
      className="document-table-scroll scrollbar-thin min-h-0 min-w-0 w-full flex-1 overflow-auto rounded-lg border border-neutral-200 dark:border-neutral-700"
      data-testid="document-table-scroll"
    >
      {/*
        Single scrollport: overflow-x + overflow-y auto.
        Native horizontal scrollbar stays at the bottom of this viewport.
      */}
      <table
        className="document-table w-full divide-y divide-neutral-200 dark:divide-neutral-700"
        style={{ minWidth: DOCUMENT_TABLE_MIN_WIDTH_PX }}
      >
        <caption className="sr-only">Uploaded documents</caption>
        <thead className="sticky top-0 z-10 bg-neutral-50 dark:bg-neutral-900">
          <tr>
            <th
              scope="col"
              className="document-table-col-name px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Name
            </th>
            <th
              scope="col"
              className="document-table-col-domain px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Domain
            </th>
            <th
              scope="col"
              className="document-table-col-status px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Status
            </th>
            <th
              scope="col"
              className="document-table-col-visibility px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
              title={VISIBILITY_NOT_IN_LIST_API}
            >
              Visibility
            </th>
            <th
              scope="col"
              className="document-table-col-uploaded px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Uploaded At
            </th>
            <th
              scope="col"
              className="document-table-col-actions px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-200 bg-white dark:divide-neutral-700 dark:bg-neutral-900">
          {documents.map((document) => {
            const isHighlighted = highlightedDocumentId === document.document_id
            return (
              <tr
                key={document.document_id}
                ref={(node) => {
                  if (node) {
                    rowRefs.current.set(document.document_id, node)
                  } else {
                    rowRefs.current.delete(document.document_id)
                  }
                }}
                data-document-id={document.document_id}
                data-highlighted={isHighlighted ? 'true' : undefined}
                className={cn(
                  'hover:bg-neutral-50 dark:hover:bg-neutral-800/40',
                  isHighlighted && 'document-row--highlight',
                )}
              >
                <td className="document-table-col-name px-4 py-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  <span className="block truncate" title={document.filename}>
                    {document.filename}
                  </span>
                </td>
                <td className="document-table-col-domain px-4 py-3">
                  <DocumentDomainCell
                    document={document}
                    domains={domains}
                    canEdit={canEditDomain}
                    isUpdating={updatingDomainDocumentId === document.document_id}
                    {...(onDomainChange !== undefined ? { onDomainChange } : {})}
                  />
                </td>
                <td className="document-table-col-status px-4 py-3">
                  <DocumentStatusBadge status={document.status} />
                </td>
                <td
                  className="document-table-col-visibility px-4 py-3 text-sm text-neutral-500 dark:text-neutral-400"
                  title={VISIBILITY_NOT_IN_LIST_API}
                >
                  —
                </td>
                <td className="document-table-col-uploaded px-4 py-3 text-sm text-neutral-600 dark:text-neutral-300">
                  {new Date(document.uploaded_at).toLocaleString()}
                </td>
                <td className="document-table-col-actions px-4 py-3 text-right">
                  <div className="inline-flex flex-nowrap items-center justify-end gap-2">
                    <ActionButton onClick={() => handleView(document)}>View</ActionButton>
                    {onDownload && (
                      <ActionButton onClick={() => onDownload(document)}>Download</ActionButton>
                    )}
                    <Button variant="danger" size="sm" onClick={() => onDelete(document)}>
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
