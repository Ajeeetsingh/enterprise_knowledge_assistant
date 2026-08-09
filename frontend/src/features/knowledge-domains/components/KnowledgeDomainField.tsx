import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useId, useState } from 'react'

import { getApiErrorMessage } from '@/services/errorHandler'
import { cn } from '@/utils/cn'

import { knowledgeDomainQueryKeys, useKnowledgeDomains } from '../hooks/useKnowledgeDomains'
import * as knowledgeDomainApi from '../services/knowledgeDomainApi'
import CreateKnowledgeDomainDialog from './CreateKnowledgeDomainDialog'

const CREATE_NEW_VALUE = '__create_new__'

export interface KnowledgeDomainFieldProps {
  value: string | null
  disabled?: boolean
  onChange: (domainId: string | null) => void
  /** Notifies parent when the Create Domain modal opens/closes (Escape/backdrop ownership). */
  onCreateDialogOpenChange?: (isOpen: boolean) => void
}

export default function KnowledgeDomainField({
  value,
  disabled = false,
  onChange,
  onCreateDialogOpenChange,
}: KnowledgeDomainFieldProps) {
  const selectId = useId()
  const queryClient = useQueryClient()
  const domainsQuery = useKnowledgeDomains()
  const domains = domainsQuery.data ?? []
  const isLoading = domainsQuery.isLoading
  const loadError = domainsQuery.isError
    ? getApiErrorMessage(domainsQuery.error) || 'Unable to load knowledge domains.'
    : null

  const [createOpen, setCreateOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const setCreateDialogOpen = useCallback(
    (open: boolean) => {
      setCreateOpen(open)
      onCreateDialogOpenChange?.(open)
    },
    [onCreateDialogOpenChange],
  )

  useEffect(() => {
    return () => {
      onCreateDialogOpenChange?.(false)
    }
  }, [onCreateDialogOpenChange])

  function handleSelectChange(next: string) {
    if (next === CREATE_NEW_VALUE) {
      setCreateError(null)
      setCreateDialogOpen(true)
      return
    }
    onChange(next || null)
  }

  async function handleCreate(input: { name: string; description: string }) {
    setIsCreating(true)
    setCreateError(null)
    try {
      const created = await knowledgeDomainApi.createKnowledgeDomain({
        name: input.name,
        description: input.description || null,
      })
      void queryClient.invalidateQueries({ queryKey: knowledgeDomainQueryKeys.list() })
      onChange(created.id)
      setCreateDialogOpen(false)
    } catch (error) {
      setCreateError(getApiErrorMessage(error) || 'Unable to create knowledge domain.')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={selectId} className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
        Knowledge Domain
      </label>

      {isLoading ? (
        <p className="text-sm text-neutral-500 dark:text-neutral-400" role="status">
          Loading domains…
        </p>
      ) : loadError ? (
        <div className="space-y-2">
          <p role="alert" className="text-sm text-error-500 dark:text-error-400">
            {loadError}
          </p>
          <button
            type="button"
            className="text-sm text-primary-700 hover:underline dark:text-primary-300"
            disabled={disabled}
            onClick={() => void domainsQuery.refetch()}
          >
            Retry
          </button>
        </div>
      ) : (
        <select
          id={selectId}
          value={value ?? ''}
          disabled={disabled || domains.length === 0}
          required
          className={cn(
            'block w-full rounded-[var(--radius-sm)] border px-3 py-2.5 text-sm',
            'bg-surface text-foreground',
            'border-border-default focus:border-accent focus:outline-none',
            'focus:shadow-[0_0_0_3px_var(--accent-muted)]',
            'disabled:cursor-not-allowed disabled:opacity-50',
          )}
          onChange={(event) => handleSelectChange(event.target.value)}
        >
          <option value="" disabled>
            Select a knowledge domain
          </option>
          {domains.map((domain) => (
            <option key={domain.id} value={domain.id}>
              {domain.name}
            </option>
          ))}
          <option value={CREATE_NEW_VALUE}>+ Create New Domain</option>
        </select>
      )}

      <CreateKnowledgeDomainDialog
        isOpen={createOpen}
        isSubmitting={isCreating}
        error={createError}
        onClose={() => {
          if (!isCreating) setCreateDialogOpen(false)
        }}
        onSubmit={(input) => void handleCreate(input)}
      />
    </div>
  )
}
