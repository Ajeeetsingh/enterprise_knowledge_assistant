import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type {
  AnalyticsFilterParams,
  MonitoringTrends,
  PerformanceMetrics,
  ResourceMetrics,
  ServiceStatusAnalytics,
  SystemMonitoringOverview,
} from '../types'

const BASE_PATH = '/admin/analytics/monitoring'

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

export async function getSystemMonitoringOverview(
  filters: AnalyticsFilterParams = {},
): Promise<SystemMonitoringOverview> {
  return request(async () => {
    const { data } = await apiClient.get<SystemMonitoringOverview>(
      `${BASE_PATH}/overview`,
      buildParams(filters),
    )
    return data
  })
}

export async function getPerformanceMetrics(
  filters: AnalyticsFilterParams = {},
): Promise<PerformanceMetrics> {
  return request(async () => {
    const { data } = await apiClient.get<PerformanceMetrics>(
      `${BASE_PATH}/performance`,
      buildParams(filters),
    )
    return data
  })
}

export async function getResourceMetrics(
  filters: AnalyticsFilterParams = {},
): Promise<ResourceMetrics> {
  return request(async () => {
    const { data } = await apiClient.get<ResourceMetrics>(
      `${BASE_PATH}/resources`,
      buildParams(filters),
    )
    return data
  })
}

export async function getServiceStatus(
  filters: AnalyticsFilterParams = {},
): Promise<ServiceStatusAnalytics> {
  return request(async () => {
    const { data } = await apiClient.get<ServiceStatusAnalytics>(
      `${BASE_PATH}/services`,
      buildParams(filters),
    )
    return data
  })
}

export async function getMonitoringTrends(
  filters: AnalyticsFilterParams = {},
): Promise<MonitoringTrends> {
  return request(async () => {
    const { data } = await apiClient.get<MonitoringTrends>(
      `${BASE_PATH}/trends`,
      buildParams(filters),
    )
    return data
  })
}
