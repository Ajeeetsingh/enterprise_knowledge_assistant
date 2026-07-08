import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AnalyticsFilterParams,
  EndpointFailureAnalytics,
  ErrorAnalyticsOverview,
  ErrorCategoryAnalytics,
  ErrorTrends,
  FailureAnalysisAnalytics,
} from '../types'

const BASE_PATH = '/admin/analytics/errors'

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

export async function getErrorAnalyticsOverview(
  filters: AnalyticsFilterParams = {},
): Promise<ErrorAnalyticsOverview> {
  return request(async () => {
    const { data } = await apiClient.get<ErrorAnalyticsOverview>(
      `${BASE_PATH}/overview`,
      buildParams(filters),
    )
    return data
  })
}

export async function getErrorTrends(filters: AnalyticsFilterParams = {}): Promise<ErrorTrends> {
  return request(async () => {
    const { data } = await apiClient.get<ErrorTrends>(`${BASE_PATH}/trends`, buildParams(filters))
    return data
  })
}

export async function getErrorCategories(
  filters: AnalyticsFilterParams = {},
): Promise<ErrorCategoryAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<ErrorCategoryAnalytics>(
      `${BASE_PATH}/categories`,
      buildParams(filters),
    )
    return data
  })
}

export async function getEndpointFailures(
  filters: AnalyticsFilterParams = {},
): Promise<EndpointFailureAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<EndpointFailureAnalytics>(
      `${BASE_PATH}/endpoints`,
      buildParams(filters),
    )
    return data
  })
}

export async function getFailureAnalysis(
  filters: AnalyticsFilterParams = {},
): Promise<FailureAnalysisAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<FailureAnalysisAnalytics>(
      `${BASE_PATH}/failures`,
      buildParams(filters),
    )
    return data
  })
}
