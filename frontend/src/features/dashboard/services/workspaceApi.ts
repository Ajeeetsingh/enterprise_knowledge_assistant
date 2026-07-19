import apiClient from '@/services/api'
import { toApiError } from '@/utils/apiError'

import type { WorkspaceSummary } from '../types'

export async function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  try {
    const { data } = await apiClient.get<WorkspaceSummary>('/workspace/summary')
    return data
  } catch (error) {
    throw toApiError(error)
  }
}
