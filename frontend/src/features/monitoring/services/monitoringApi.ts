/**
 * Monitoring API client (Phase 9.4B).
 */

import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type { MonitoringSummary, SystemMetrics } from '../types'

async function request<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation()
  } catch (error) {
    throw toApiError(error)
  }
}

export async function getMonitoringSummary(): Promise<MonitoringSummary> {
  return request(async () => {
    const { data } = await apiClient.get<MonitoringSummary>('/monitoring/summary')
    return data
  })
}

export async function getSystemMetrics(): Promise<SystemMetrics> {
  return request(async () => {
    const { data } = await apiClient.get<SystemMetrics>('/monitoring/metrics')
    return data
  })
}
