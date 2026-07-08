import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AnalyticsFilterParams,
  CollectionAnalytics,
  DocumentAnalytics,
  FreshnessAnalytics,
  KnowledgeAnalyticsOverview,
  KnowledgeGapAnalytics,
  SearchAnalytics,
} from '../types'

const BASE_PATH = '/admin/analytics/knowledge'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

function buildParams(filters: AnalyticsFilterParams = {}) {
  return {
    params: {
      range_preset: filters.range_preset,
      start_date: filters.start_date,
      end_date: filters.end_date,
      limit: filters.limit,
      offset: filters.offset,
    },
  }
}

export async function getKnowledgeAnalyticsOverview(
  filters: AnalyticsFilterParams = {},
): Promise<KnowledgeAnalyticsOverview> {
  return request(async () => {
    const { data } = await apiClient.get<KnowledgeAnalyticsOverview>(
      `${BASE_PATH}/overview`,
      buildParams(filters),
    )
    return data
  })
}

export async function getDocumentAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<DocumentAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<DocumentAnalytics>(
      `${BASE_PATH}/documents`,
      buildParams(filters),
    )
    return data
  })
}

export async function getCollectionAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<CollectionAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<CollectionAnalytics>(
      `${BASE_PATH}/collections`,
      buildParams(filters),
    )
    return data
  })
}

export async function getSearchAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<SearchAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<SearchAnalytics>(
      `${BASE_PATH}/searches`,
      buildParams(filters),
    )
    return data
  })
}

export async function getKnowledgeGapAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<KnowledgeGapAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<KnowledgeGapAnalytics>(
      `${BASE_PATH}/gaps`,
      buildParams(filters),
    )
    return data
  })
}

export async function getFreshnessAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<FreshnessAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<FreshnessAnalytics>(
      `${BASE_PATH}/freshness`,
      buildParams(filters),
    )
    return data
  })
}
