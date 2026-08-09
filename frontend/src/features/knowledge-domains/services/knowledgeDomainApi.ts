/**
 * Knowledge Domains API client (Phase 2 upload assignment).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  KnowledgeDomain,
  KnowledgeDomainCreateRequest,
  KnowledgeDomainListResponse,
} from '../types'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

export async function listKnowledgeDomains(): Promise<KnowledgeDomain[]> {
  return request(async () => {
    const { data } = await apiClient.get<KnowledgeDomainListResponse>(
      '/knowledge-domains',
    )
    return data.items
  })
}

export async function createKnowledgeDomain(
  body: KnowledgeDomainCreateRequest,
): Promise<KnowledgeDomain> {
  return request(async () => {
    const { data } = await apiClient.post<KnowledgeDomain>('/knowledge-domains', body)
    return data
  })
}
