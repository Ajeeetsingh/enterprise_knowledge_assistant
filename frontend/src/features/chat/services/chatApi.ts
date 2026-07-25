/**
 * Chat and conversation API client (Phase 9.1).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationCreateRequest,
  ConversationDeleteResponse,
  ConversationHistoryResponse,
  ConversationListResponse,
  ConversationUpdateRequest,
  SuggestedQuestionsResponse,
} from '../types'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getConversations(
  limit = 50,
  offset = 0,
): Promise<ConversationListResponse> {
  return request(async () => {
    const { data } = await apiClient.get<ConversationListResponse>('/conversations', {
      params: { limit, offset },
    })
    return data
  })
}

export async function createConversation(
  body: ConversationCreateRequest = {},
): Promise<Conversation> {
  return request(async () => {
    const { data } = await apiClient.post<Conversation>('/conversations', body)
    return data
  })
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  return request(async () => {
    const { data } = await apiClient.get<Conversation>(`/conversations/${conversationId}`)
    return data
  })
}

export async function updateConversation(
  conversationId: string,
  body: ConversationUpdateRequest,
): Promise<Conversation> {
  return request(async () => {
    const { data } = await apiClient.put<Conversation>(
      `/conversations/${conversationId}`,
      body,
    )
    return data
  })
}

export async function deleteConversation(conversationId: string): Promise<ConversationDeleteResponse> {
  return request(async () => {
    const { data } = await apiClient.delete<ConversationDeleteResponse>(
      `/conversations/${conversationId}`,
    )
    return data
  })
}

export async function getMessages(conversationId: string): Promise<ConversationHistoryResponse> {
  return request(async () => {
    const { data } = await apiClient.get<ConversationHistoryResponse>(
      `/conversations/${conversationId}/messages`,
    )
    return data
  })
}

export async function askQuestion(body: ChatRequest): Promise<ChatResponse> {
  return request(async () => {
    const { data } = await apiClient.post<ChatResponse>('/chat/ask', body)
    return data
  })
}

export interface GuestImportMessagePayload {
  role: 'user' | 'assistant'
  content: string
}

export interface GuestImportRequest {
  messages: GuestImportMessagePayload[]
  title?: string | null
}

export async function importGuestConversation(
  body: GuestImportRequest,
): Promise<Conversation> {
  return request(async () => {
    const { data } = await apiClient.post<Conversation>(
      '/conversations/import-guest',
      body,
    )
    return data
  })
}

export async function getSuggestedQuestions(): Promise<SuggestedQuestionsResponse> {
  return request(async () => {
    const { data } = await apiClient.get<SuggestedQuestionsResponse>(
      '/chat/suggested-questions',
    )
    return data
  })
}
