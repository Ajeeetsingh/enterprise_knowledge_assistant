import type { AnalyticsFilterParams } from '../types'

export const analyticsQueryKeys = {
  all: ['analytics'] as const,
  users: () => [...analyticsQueryKeys.all, 'users'] as const,
  overview: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.users(), 'overview', filters] as const,
  growth: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.users(), 'growth', filters] as const,
  activity: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.users(), 'activity', filters] as const,
  topUsers: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.users(), 'top-users', filters] as const,
  inactiveUsers: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.users(), 'inactive-users', filters] as const,
  ai: () => [...analyticsQueryKeys.all, 'ai'] as const,
  aiOverview: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.ai(), 'overview', filters] as const,
  aiTrends: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.ai(), 'trends', filters] as const,
  aiRetrieval: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.ai(), 'retrieval', filters] as const,
  aiQuestions: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.ai(), 'questions', filters] as const,
  aiFailures: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.ai(), 'failures', filters] as const,
  knowledge: () => [...analyticsQueryKeys.all, 'knowledge'] as const,
  knowledgeOverview: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'overview', filters] as const,
  knowledgeDocuments: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'documents', filters] as const,
  knowledgeCollections: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'collections', filters] as const,
  knowledgeSearches: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'searches', filters] as const,
  knowledgeGaps: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'gaps', filters] as const,
  knowledgeFreshness: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.knowledge(), 'freshness', filters] as const,
  monitoring: () => [...analyticsQueryKeys.all, 'monitoring'] as const,
  monitoringOverview: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.monitoring(), 'overview', filters] as const,
  monitoringPerformance: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.monitoring(), 'performance', filters] as const,
  monitoringResources: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.monitoring(), 'resources', filters] as const,
  monitoringServices: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.monitoring(), 'services', filters] as const,
  monitoringTrends: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.monitoring(), 'trends', filters] as const,
  errors: () => [...analyticsQueryKeys.all, 'errors'] as const,
  errorsOverview: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.errors(), 'overview', filters] as const,
  errorsTrends: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.errors(), 'trends', filters] as const,
  errorsCategories: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.errors(), 'categories', filters] as const,
  errorsEndpoints: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.errors(), 'endpoints', filters] as const,
  errorsFailures: (filters: AnalyticsFilterParams) =>
    [...analyticsQueryKeys.errors(), 'failures', filters] as const,
}
