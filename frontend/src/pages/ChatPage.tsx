import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import ChatArea from '@/features/chat/components/ChatArea'
import ConversationList from '@/features/chat/components/ConversationList'
import DeleteConversationDialog from '@/features/chat/components/DeleteConversationDialog'
import RenameConversationModal from '@/features/chat/components/RenameConversationModal'
import { useConversations } from '@/features/chat/hooks/useConversations'
import { useCreateConversation } from '@/features/chat/hooks/useCreateConversation'
import { useDeleteConversation } from '@/features/chat/hooks/useDeleteConversation'
import { useRenameConversation } from '@/features/chat/hooks/useRenameConversation'
import type { Conversation } from '@/features/chat/types'
import { useToast } from '@/contexts/ToastContext'
import { getApiErrorMessage } from '@/services/errorHandler'
import type { ApiError } from '@/types'

function resolveErrorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as ApiError).message)
  }
  return 'Something went wrong. Please try again.'
}

export default function ChatPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedConversationId = searchParams.get('conversation')
  const { showSuccess, showError } = useToast()

  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading, isError, error } = useConversations()
  const createConversation = useCreateConversation()
  const renameConversation = useRenameConversation()
  const deleteConversation = useDeleteConversation()

  const conversations = data?.items ?? []

  function handleSelectConversation(conversationId: string) {
    setSearchParams({ conversation: conversationId })
  }

  function clearSelectedConversation() {
    navigate('/chat', { replace: true })
  }

  async function handleCreateConversation() {
    try {
      const conversation = await createConversation.mutateAsync()
      setSearchParams({ conversation: conversation.id })
      showSuccess('Conversation created.')
    } catch (mutationError) {
      showError(getApiErrorMessage(mutationError))
    }
  }

  function openRename(conversation: Conversation) {
    setRenameError(null)
    setRenameTarget(conversation)
  }

  function closeRename() {
    if (renameConversation.isPending) return
    setRenameTarget(null)
    setRenameError(null)
  }

  async function handleRenameSave(title: string) {
    if (!renameTarget) return
    setRenameError(null)
    try {
      await renameConversation.mutateAsync({
        conversationId: renameTarget.id,
        title,
      })
      setRenameTarget(null)
      showSuccess('Conversation renamed.')
    } catch (mutationError) {
      const message = getApiErrorMessage(mutationError)
      setRenameError(message)
      showError(message)
    }
  }

  function openDelete(conversation: Conversation) {
    setDeleteError(null)
    setDeleteTarget(conversation)
  }

  function closeDelete() {
    if (deleteConversation.isPending) return
    setDeleteTarget(null)
    setDeleteError(null)
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleteError(null)
    const deletedId = deleteTarget.id

    try {
      await deleteConversation.mutateAsync(deletedId)
      setDeleteTarget(null)
      showSuccess('Conversation deleted.')

      if (selectedConversationId === deletedId) {
        clearSelectedConversation()
      }
    } catch (mutationError) {
      const message = getApiErrorMessage(mutationError)
      setDeleteError(message)
      showError(message)
    }
  }

  return (
    <>
      <div className="-mx-4 -my-6 flex h-[calc(100dvh-3.5rem-3rem)] min-h-[28rem] flex-col overflow-hidden border border-neutral-200 dark:border-neutral-700 sm:-mx-6 lg:-mx-8 lg:flex-row">
        <ConversationList
          conversations={conversations}
          selectedId={selectedConversationId}
          isLoading={isLoading}
          isCreating={createConversation.isPending}
          error={isError ? resolveErrorMessage(error) : null}
          onSelect={handleSelectConversation}
          onCreate={() => void handleCreateConversation()}
          onRename={openRename}
          onDelete={openDelete}
        />

        <ChatArea conversationId={selectedConversationId} />
      </div>

      <RenameConversationModal
        conversation={renameTarget}
        isOpen={renameTarget !== null}
        isSaving={renameConversation.isPending}
        error={renameError}
        onClose={closeRename}
        onSave={(title) => void handleRenameSave(title)}
      />

      <DeleteConversationDialog
        conversation={deleteTarget}
        isOpen={deleteTarget !== null}
        isDeleting={deleteConversation.isPending}
        error={deleteError}
        onClose={closeDelete}
        onConfirm={() => void handleDeleteConfirm()}
      />
    </>
  )
}
