export type DateRangePreset =
  | 'today'
  | 'last_7_days'
  | 'last_30_days'
  | 'last_90_days'
  | 'custom'

export interface AnalyticsFilterParams {
  range_preset?: DateRangePreset
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface ChartSeries {
  event_type: string
  points: Record<string, number>
}

export interface UserAnalyticsOverview {
  total_users: number
  new_users: number
  daily_active_users: number
  weekly_active_users: number
  monthly_active_users: number
  active_user_percentage: number
  average_conversations_per_user: number
  average_questions_per_user: number
  start_date: string
  end_date: string
}

export interface UserGrowthTrends {
  user_registrations: ChartSeries
  active_users: ChartSeries
  login_activity: ChartSeries
  conversation_creation: ChartSeries
  questions_asked: ChartSeries
  start_date: string
  end_date: string
}

export interface UserActivityAnalytics {
  average_conversations_per_user: number
  average_questions_per_user: number
  average_engagement_score: number
  active_users: ChartSeries
  questions_asked: ChartSeries
  start_date: string
  end_date: string
}

export interface UserActivityItem {
  user_id: string
  email: string
  full_name: string
  is_active: boolean
  conversation_count: number
  question_count: number
  last_active_at: string | null
}

export interface PaginatedUserActivity {
  items: UserActivityItem[]
  total: number
  limit: number
  offset: number
}

export interface AIAnalyticsOverview {
  total_questions: number
  responses_generated: number
  average_response_time_seconds: number | null
  average_retrieval_time_seconds: number | null
  average_retrieved_documents: number | null
  citation_usage_rate: number
  retrieval_success_rate: number
  retrieval_failure_rate: number
  ai_error_rate: number
  average_confidence_score: number | null
  start_date: string
  end_date: string
}

export interface AITrends {
  questions: ChartSeries
  responses: ChartSeries
  retrieval_success: ChartSeries
  retrieval_failures: ChartSeries
  average_response_time: ChartSeries
  citation_usage: ChartSeries
  start_date: string
  end_date: string
}

export interface AIRetrievalAnalytics {
  average_retrieved_chunks: number | null
  average_retrieval_latency_seconds: number | null
  retrieval_success_percentage: number
  empty_retrievals: number
  collection_distribution: Record<string, number>
  start_date: string
  end_date: string
}

export interface QuestionFrequencyItem {
  question: string
  count: number
}

export interface AIQuestionsAnalytics {
  items: QuestionFrequencyItem[]
  total: number
  average_citations_per_response: number | null
  responses_without_citations: number
  questions_without_documents: number
  quality_summary: string
  start_date: string
  end_date: string
}

export interface FailureAnalysisItem {
  reason: string
  count: number
}

export interface AIFailuresAnalytics {
  items: FailureAnalysisItem[]
  total: number
  limit: number
  offset: number
  start_date: string
  end_date: string
}

export interface KnowledgeAnalyticsOverview {
  total_documents: number
  active_documents: number
  stale_documents: number
  unused_documents: number
  average_document_views: number | null
  average_citations_per_document: number | null
  search_success_rate: number
  start_date: string
  end_date: string
}

export interface DocumentUsageItem {
  document_id: string
  filename: string
  collection: string
  view_count: number
  citation_count: number
}

export interface DocumentAnalytics {
  most_viewed: DocumentUsageItem[]
  least_viewed: DocumentUsageItem[]
  total_most_viewed: number
  total_least_viewed: number
  average_document_views: number | null
  average_citations_per_document: number | null
  document_usage_trend: ChartSeries
  start_date: string
  end_date: string
}

export interface CollectionUsageItem {
  collection: string
  document_count: number
  usage_count: number
  search_count: number
}

export interface CollectionAnalytics {
  items: CollectionUsageItem[]
  total: number
  documents_per_collection: Record<string, number>
  collection_popularity: Record<string, number>
  retrieval_distribution: Record<string, number>
  start_date: string
  end_date: string
}

export interface SearchTopicItem {
  topic: string
  count: number
}

export interface SearchAnalytics {
  topics: SearchTopicItem[]
  documents: DocumentUsageItem[]
  collections: CollectionUsageItem[]
  total_topics: number
  total_documents: number
  total_collections: number
  searches_with_no_results: number
  search_success_rate: number
  search_trend: ChartSeries
  start_date: string
  end_date: string
}

export interface KnowledgeGapItem {
  category: string
  label: string
  count: number
}

export interface KnowledgeGapAnalytics {
  items: KnowledgeGapItem[]
  total: number
  questions_without_documents: number
  never_cited_documents: number
  never_searched_documents: number
  low_engagement_collections: number
  start_date: string
  end_date: string
}

export interface FreshnessItem {
  document_id: string
  filename: string
  collection: string
  uploaded_at: string
  updated_at: string
  days_inactive: number
}

export interface FreshnessAnalytics {
  recent_uploads: FreshnessItem[]
  oldest_documents: FreshnessItem[]
  recently_updated: FreshnessItem[]
  longest_inactive: FreshnessItem[]
  total_recent_uploads: number
  total_oldest_documents: number
  total_recently_updated: number
  total_longest_inactive: number
  upload_trend: ChartSeries
  start_date: string
  end_date: string
}

export type ServiceHealthStatus = 'healthy' | 'degraded' | 'unavailable'

export interface SystemMonitoringOverview {
  api_health: ServiceHealthStatus
  database_health: ServiceHealthStatus
  search_service_health: ServiceHealthStatus
  vector_index_health: ServiceHealthStatus
  overall_system_status: ServiceHealthStatus
  uptime_seconds: number
  version: string
  start_date: string
  end_date: string
}

export interface PerformanceMetrics {
  average_api_response_time_seconds: number | null
  average_search_time_seconds: number | null
  average_retrieval_time_seconds: number | null
  database_query_time_seconds: number | null
  embedding_generation_time_seconds: number | null
  start_date: string
  end_date: string
}

export interface ResourceMetrics {
  total_documents: number
  total_users: number
  total_conversations: number
  storage_usage_bytes: number
  vector_index_size_bytes: number | null
  uploaded_file_count: number
  start_date: string
  end_date: string
}

export interface ServiceStatusItem {
  service: string
  status: ServiceHealthStatus
  detail: string
}

export interface ServiceStatusAnalytics {
  items: ServiceStatusItem[]
  start_date: string
  end_date: string
}

export interface HealthTimelineItem {
  timestamp: string
  service: string
  status: ServiceHealthStatus
  event_type: string
  detail: string
}

export interface MonitoringTrends {
  api_latency: ChartSeries
  search_latency: ChartSeries
  errors: ChartSeries
  health_events: ChartSeries
  timeline_items: HealthTimelineItem[]
  timeline_total: number
  timeline_limit: number
  timeline_offset: number
  start_date: string
  end_date: string
}

export function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }
  if (value < 1024 * 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`
  }
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

export interface ErrorAnalyticsOverview {
  total_errors: number
  authentication_failures: number
  authorization_failures: number
  upload_failures: number | null
  indexing_failures: number | null
  retrieval_failures: number
  api_errors: number | null
  background_job_failures: number | null
  error_rate: number
  error_free_requests_percentage: number
  start_date: string
  end_date: string
}

export interface ErrorTrends {
  total_errors: ChartSeries
  authentication_failures: ChartSeries
  retrieval_failures: ChartSeries
  upload_failures: ChartSeries
  api_exceptions: ChartSeries
  permission_denials: ChartSeries
  start_date: string
  end_date: string
}

export interface ErrorFrequencyItem {
  label: string
  count: number
  category: string
}

export interface ErrorCategoryAnalytics {
  by_category: Record<string, number>
  by_service: Record<string, number>
  by_severity: Record<string, number> | null
  recurring_errors: ErrorFrequencyItem[]
  total_recurring_errors: number
  start_date: string
  end_date: string
}

export interface EndpointFailureItem {
  endpoint: string
  count: number
  service: string
}

export interface EndpointFailureAnalytics {
  items: EndpointFailureItem[]
  total: number
  limit: number
  offset: number
  start_date: string
  end_date: string
}

export interface FailureAnalysisAnalytics {
  failed_operations: ErrorFrequencyItem[]
  retrieval_failures: ErrorFrequencyItem[]
  upload_failures: ErrorFrequencyItem[]
  authentication_failures: ErrorFrequencyItem[]
  total_failed_operations: number
  total_retrieval_failures: number
  total_upload_failures: number
  total_authentication_failures: number
  limit: number
  offset: number
  start_date: string
  end_date: string
}

export function formatMetricValue(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)
}

export function formatPercentValue(value: number): string {
  return `${formatMetricValue(value)}%`
}
