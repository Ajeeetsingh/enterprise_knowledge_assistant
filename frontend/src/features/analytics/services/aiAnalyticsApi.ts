import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AIFailuresAnalytics,
  AIAnalyticsOverview,
  AIQuestionsAnalytics,
  AIRetrievalAnalytics,
  AITrends,
  AnalyticsFilterParams,
} from '../types'

const BASE_PATH = '/admin/analytics/ai'

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

export async function getAIAnalyticsOverview(
  filters: AnalyticsFilterParams = {},
): Promise<AIAnalyticsOverview> {
  return request(async () => {
    const { data } = await apiClient.get<AIAnalyticsOverview>(
      `${BASE_PATH}/overview`,
      buildParams(filters),
    )
    return data
  })
}

export async function getAITrends(filters: AnalyticsFilterParams = {}): Promise<AITrends> {
  return request(async () => {
    const { data } = await apiClient.get<AITrends>(`${BASE_PATH}/trends`, buildParams(filters))
    return data
  })
}

export async function getRetrievalAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<AIRetrievalAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<AIRetrievalAnalytics>(
      `${BASE_PATH}/retrieval`,
      buildParams(filters),
    )
    return data
  })
}

export async function getTopQuestions(
  filters: AnalyticsFilterParams = {},
): Promise<AIQuestionsAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<AIQuestionsAnalytics>(
      `${BASE_PATH}/questions`,
      buildParams(filters),
    )
    return data
  })
}

export async function getFailureAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<AIFailuresAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<AIFailuresAnalytics>(
      `${BASE_PATH}/failures`,
      buildParams(filters),
    )
    return data
  })
}
