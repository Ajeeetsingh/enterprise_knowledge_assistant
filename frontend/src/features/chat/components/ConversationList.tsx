import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'
import Spinner from '@/components/ui/Spinner'
import { cn } from '@/utils/cn'

import { conversationDisplayTitle, type Conversation } from '../types'
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
}

function formatCreatedDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
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
}: ConversationListProps) {
  return (
    <aside
      className="flex w-full flex-col border-r border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900 lg:w-72 xl:w-80"
      aria-label="Conversations"
    >
      <div className="flex items-center justify-between gap-2 border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
        <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          Conversations
        </h2>
        <Button size="sm" isLoading={isCreating} disabled={isCreating} onClick={onCreate}>
          New
        </Button>
      </div>

      {error && (
        <p role="alert" className="px-4 py-3 text-sm text-error-500 dark:text-error-400">
          {error}
        </p>
      )}

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex justify-center py-8" role="status">
            <Spinner size="md" label="Loading conversations" />
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState
            title="No conversations yet"
            description="Create your first conversation to start asking questions about your documents."
            action={
              <Button size="sm" isLoading={isCreating} disabled={isCreating} onClick={onCreate}>
                Create your first conversation
              </Button>
            }
            className="py-10"
          />
        ) : (
          <ul className="divide-y divide-neutral-200 dark:divide-neutral-700">
            {conversations.map((conversation) => {
              const isSelected = conversation.id === selectedId
              return (
                <li key={conversation.id}>
                  <div
                    className={cn(
                      'flex items-stretch gap-1',
                      isSelected && 'border-l-2 border-l-primary-600 dark:border-l-primary-400',
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelect(conversation.id)}
                      className={cn(
                        'min-w-0 flex-1 px-4 py-3 text-left transition-colors',
                        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500',
                        isSelected
                          ? 'bg-primary-50 dark:bg-primary-900/20'
                          : 'hover:bg-neutral-50 dark:hover:bg-neutral-800',
                      )}
                      aria-current={isSelected ? 'true' : undefined}
                    >
                      <div className="flex items-center gap-2">
                        {isSelected && (
                          <span
                            aria-hidden
                            className="size-2 shrink-0 rounded-full bg-primary-600 dark:bg-primary-400"
                          />
                        )}
                        <p
                          className={cn(
                            'truncate text-sm font-medium',
                            isSelected
                              ? 'text-primary-700 dark:text-primary-300'
                              : 'text-neutral-900 dark:text-neutral-100',
                          )}
                        >
                          {conversationDisplayTitle(conversation)}
                        </p>
                      </div>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                        Created {formatCreatedDate(conversation.created_at)}
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
