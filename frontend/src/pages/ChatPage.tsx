import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'

import ChatArea from '@/features/chat/components/ChatArea'
import ConversationList from '@/features/chat/components/ConversationList'
import DeleteConversationDialog from '@/features/chat/components/DeleteConversationDialog'
import ChatLayout from '@/features/chat/layouts/ChatLayout'
import { useConversations } from '@/features/chat/hooks/useConversations'
import { useCreateConversation } from '@/features/chat/hooks/useCreateConversation'
import { useDeleteConversation } from '@/features/chat/hooks/useDeleteConversation'
import { useRenameConversation } from '@/features/chat/hooks/useRenameConversation'
import type { Conversation } from '@/features/chat/types'
import { useLayoutContext } from '@/contexts/LayoutContext'
import { useToast } from '@/contexts/ToastContext'
import { getApiErrorMessage, resolveErrorMessage } from '@/services/errorHandler'

interface ChatOutletContext {
  sidebarWidth: number
  sidebarCollapsed: boolean
}

interface ChatLocationState {
  initialQuestion?: string
}

export default function ChatPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const { sidebarWidth, sidebarCollapsed } = useOutletContext<ChatOutletContext>()
  const { setChatRouteActive, closeConversationDrawer, setMobileChatPanel } = useLayoutContext()
  const selectedConversationId = searchParams.get('conversation')
  const { showSuccess, showError } = useToast()

  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null)
  const bootstrapStarted = useRef(false)

  const { data, isLoading, isError, error } = useConversations()
  const createConversation = useCreateConversation()
  const renameConversation = useRenameConversation()
  const deleteConversation = useDeleteConversation()

  const conversations = data?.items ?? []

  useEffect(() => {
    setChatRouteActive(true)
    return () => setChatRouteActive(false)
  }, [setChatRouteActive])

  // Dashboard "Ask anything" deep-link: create a conversation and hand the
  // question to ChatArea once. Clears location state so refresh does not re-ask.
  useEffect(() => {
    const state = location.state as ChatLocationState | null
    const question = state?.initialQuestion?.trim()
    if (!question || bootstrapStarted.current) return

    bootstrapStarted.current = true
    let cancelled = false

    async function bootstrap() {
      try {
        const conversation = await createConversation.mutateAsync()
        if (cancelled) return
        setPendingQuestion(question!)
        navigate(`/chat?conversation=${conversation.id}`, {
          replace: true,
          state: {},
        })
      } catch (mutationError) {
        bootstrapStarted.current = false
        showError(getApiErrorMessage(mutationError))
      }
    }

    void bootstrap()
    return () => {
      cancelled = true
    }
  }, [location.state, createConversation, navigate, showError])

  function handleSelectConversation(conversationId: string) {
    setSearchParams({ conversation: conversationId })
    closeConversationDrawer()
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

  useEffect(() => {
    setMobileChatPanel({
      conversations,
      selectedId: selectedConversationId,
      isLoading,
      isCreating: createConversation.isPending,
      onSelect: handleSelectConversation,
      onCreate: () => void handleCreateConversation(),
    })
    return () => setMobileChatPanel(null)
  }, [
    conversations,
    selectedConversationId,
    isLoading,
    createConversation.isPending,
    setMobileChatPanel,
  ])

  async function handleInlineRename(conversationId: string, title: string) {
    try {
      await renameConversation.mutateAsync({ conversationId, title })
      showSuccess('Conversation renamed.')
    } catch (mutationError) {
      showError(getApiErrorMessage(mutationError))
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
      <ChatLayout
        sidebarWidth={sidebarWidth}
        sidebarCollapsed={sidebarCollapsed}
        conversationList={
          <ConversationList
            conversations={conversations}
            selectedId={selectedConversationId}
            isLoading={isLoading}
            isCreating={createConversation.isPending}
            error={isError ? resolveErrorMessage(error, 'Something went wrong. Please try again.') : null}
            onSelect={handleSelectConversation}
            onCreate={() => void handleCreateConversation()}
            onRename={(conversationId, title) => void handleInlineRename(conversationId, title)}
            onDelete={openDelete}
          />
        }
        chatArea={
          <ChatArea
            conversationId={selectedConversationId}
            initialQuestion={pendingQuestion}
            onInitialQuestionConsumed={() => setPendingQuestion(null)}
          />
        }      />

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
