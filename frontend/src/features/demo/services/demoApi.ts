import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

export interface GuestHistoryMessagePayload {
  role: 'user' | 'assistant'
  content: string
  answer_kind?: string | null
}

export interface GuestAskRequest {
  question: string
  history?: GuestHistoryMessagePayload[]
}

export interface GuestAskResponse {
  answer: string
  confidence_score: number
  message: string
  answer_kind: string | null
  requires_auth: boolean
}

export async function askGuestQuestion(
  payload: GuestAskRequest,
): Promise<GuestAskResponse> {
  try {
    const { data } = await apiClient.post<GuestAskResponse>('/demo/ask', payload)
    return data
  } catch (error) {
    throw toApiError(error)
  }
}
