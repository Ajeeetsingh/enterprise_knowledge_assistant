import { useMemo, useState } from 'react'

import { PlusIcon } from '@/components/layout/NavIcons'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

import { conversationDisplayTitle, type Conversation } from '../types'
import ConversationListSkeleton from './ConversationListSkeleton'
import ConversationMenu from './ConversationMenu'

export interface ConversationListProps {
  conversations: Conversation[]
  selectedId: string | null
  isLoading: boolean
  isCreating: boolean
  error: string | null
  onSelect: (conversationId: string) => void
  onCreate: () => void
  onRename: (conversation: Conversation) => void
  onDelete: (conversation: Conversation) => void
  className?: string
}

function formatCreatedDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function NewConversationButton({
  isCreating,
  onCreate,
  label = 'New',
}: {
  isCreating: boolean
  onCreate: () => void
  label?: string
}) {
  return (
    <button
      type="button"
      className="new-conversation-button"
      disabled={isCreating}
      onClick={onCreate}
    >
      {isCreating ? (
        <Spinner size="sm" label="Creating conversation" />
      ) : (
        <PlusIcon />
      )}
      <span>{label}</span>
    </button>
  )
}

export default function ConversationList({
  conversations,
  selectedId,
  isLoading,
  isCreating,
  error,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  className,
}: ConversationListProps) {
  const [query, setQuery] = useState('')

  const filteredConversations = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return conversations
    return conversations.filter((conversation) =>
      conversationDisplayTitle(conversation).toLowerCase().includes(normalized),
    )
  }, [conversations, query])

  return (
    <aside
      className={cn('flex h-full min-h-0 w-full flex-col bg-surface', className)}
      aria-label="Conversations"
    >
      <div className="space-y-3 border-b border-border-subtle px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-medium text-foreground">Conversations</h2>
          <NewConversationButton isCreating={isCreating} onCreate={onCreate} />
        </div>
        <Input
          type="search"
          value={query}
          placeholder="Search conversations"
          aria-label="Search conversations"
          className="h-9"
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      {error && (
        <p role="alert" className="px-4 py-3 text-sm text-error-500">
          {error}
        </p>
      )}

      <div className="scrollbar-thin flex-1 overflow-y-auto">
        {isLoading ? (
          <div role="status" aria-live="polite">
            <ConversationListSkeleton />
            <span className="sr-only">Loading conversations</span>
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState
            title="No conversations yet"
            description="Create your first conversation to start asking questions about your documents."
            action={
              <NewConversationButton
                isCreating={isCreating}
                onCreate={onCreate}
                label="Create your first conversation"
              />
            }
            className="px-4 py-10"
          />
        ) : filteredConversations.length === 0 ? (
          <p className="px-4 py-8 text-sm text-muted">No conversations match your search.</p>
        ) : (
          <ul className="py-1">
            {filteredConversations.map((conversation) => {
              const isSelected = conversation.id === selectedId
              return (
                <li key={conversation.id}>
                  <div
                    className={cn(
                      'flex items-stretch gap-1 transition-colors duration-150',
                      isSelected && 'border-l-[3px] border-l-accent',
                      !isSelected && 'border-l-[3px] border-l-transparent',
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(conversation.id)}
                      className={cn(
                        'interactive-row min-w-0 flex-1 px-4 py-3 text-left',
                        'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
                        isSelected ? 'text-foreground' : 'text-muted hover:text-foreground',
                      )}
                      aria-current={isSelected ? 'true' : undefined}
                    >
                      <p
                        className={cn(
                          'truncate text-sm font-medium',
                          isSelected ? 'text-accent' : undefined,
                        )}
                      >
                        {conversationDisplayTitle(conversation)}
                      </p>
                      <p className="mt-1 text-xs text-subtle">
                        {formatCreatedDate(conversation.created_at)}
                      </p>
                    </button>

                    <div className="flex items-center pr-2">
                      <ConversationMenu
                        onRename={() => onRename(conversation)}
                        onDelete={() => onDelete(conversation)}
                      />
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </aside>
  )
}
