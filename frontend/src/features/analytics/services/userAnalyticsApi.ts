import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AnalyticsFilterParams,
  PaginatedUserActivity,
  UserActivityAnalytics,
  UserAnalyticsOverview,
  UserGrowthTrends,
} from '../types'

const BASE_PATH = '/admin/analytics/users'

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

export async function getUserAnalyticsOverview(
  filters: AnalyticsFilterParams = {},
): Promise<UserAnalyticsOverview> {
  return request(async () => {
    const { data } = await apiClient.get<UserAnalyticsOverview>(
      `${BASE_PATH}/overview`,
      buildParams(filters),
    )
    return data
  })
}

export async function getUserGrowthTrends(
  filters: AnalyticsFilterParams = {},
): Promise<UserGrowthTrends> {
  return request(async () => {
    const { data } = await apiClient.get<UserGrowthTrends>(
      `${BASE_PATH}/trends`,
      buildParams(filters),
    )
    return data
  })
}

export async function getUserActivityAnalytics(
  filters: AnalyticsFilterParams = {},
): Promise<UserActivityAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<UserActivityAnalytics>(
      `${BASE_PATH}/activity`,
      buildParams(filters),
    )
    return data
  })
}

export async function getTopUsers(
  filters: AnalyticsFilterParams = {},
): Promise<PaginatedUserActivity> {
  return request(async () => {
    const { data } = await apiClient.get<PaginatedUserActivity>(
      `${BASE_PATH}/top-users`,
      buildParams(filters),
    )
    return data
  })
}

export async function getInactiveUsers(
  filters: AnalyticsFilterParams = {},
): Promise<PaginatedUserActivity> {
  return request(async () => {
    const { data } = await apiClient.get<PaginatedUserActivity>(
      `${BASE_PATH}/inactive`,
      buildParams(filters),
    )
    return data
  })
}
