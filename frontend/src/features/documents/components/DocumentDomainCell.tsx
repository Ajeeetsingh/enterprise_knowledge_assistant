import { useEffect, useState } from 'react'

import type { KnowledgeDomain } from '@/features/knowledge-domains'
import { cn } from '@/utils/cn'

import type { Document } from '../types'
import { getDocumentDomainLabel, UNCATEGORIZED_DOMAIN_LABEL } from '../types'

export interface DocumentDomainCellProps {
  document: Document
  domains: KnowledgeDomain[]
  canEdit: boolean
  isUpdating?: boolean
  onDomainChange?: (
    document: Document,
    domainId: string | null,
  ) => Promise<void> | void
}

export default function DocumentDomainCell({
  document,
  domains,
  canEdit,
  isUpdating = false,
  onDomainChange,
}: DocumentDomainCellProps) {
  const committedValue = document.domain_id ?? ''
  const [draftValue, setDraftValue] = useState(committedValue)

  useEffect(() => {
    setDraftValue(committedValue)
  }, [committedValue])

  if (!canEdit || !onDomainChange) {
    return (
      <span className="text-sm text-neutral-600 dark:text-neutral-300">
        {getDocumentDomainLabel(document)}
      </span>
    )
  }

  async function handleChange(nextValue: string) {
    const nextDomainId = nextValue || null
    const previous = draftValue
    setDraftValue(nextValue)
    try {
      await onDomainChange?.(document, nextDomainId)
    } catch {
      setDraftValue(previous)
    }
  }

  return (
    <select
      aria-label={`Domain for ${document.filename}`}
      className={cn(
        'w-full min-w-[160px] max-w-[220px] rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm',
        'text-neutral-800 dark:border-neutral-600 dark:bg-neutral-900 dark:text-neutral-100',
        'disabled:cursor-not-allowed disabled:opacity-60',
      )}
      value={draftValue}
      disabled={isUpdating}
      onChange={(event) => {
        void handleChange(event.target.value)
      }}
    >
      <option value="">{UNCATEGORIZED_DOMAIN_LABEL}</option>
      {domains.map((domain) => (
        <option key={domain.id} value={domain.id}>
          {domain.name}
        </option>
      ))}
    </select>
  )
}
