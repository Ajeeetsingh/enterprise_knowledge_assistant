import { Link } from 'react-router-dom'

import {
  useResourceMetrics,
  useSystemMonitoring,
} from '@/features/analytics/hooks'
import type { ServiceHealthStatus } from '@/features/analytics/types'
import { formatBytes } from '@/features/analytics/types'
import { cn } from '@/utils/cn'

import AdminHealthStatusCard from '../components/AdminHealthStatusCard'
import AdminMetricCard from '../components/AdminMetricCard'
import AdminQuickActionCard from '../components/AdminQuickActionCard'

const QUICK_ACTIONS = [
  {
    to: '/admin/users',
    title: 'Manage users',
    description: 'Create users, manage roles and access.',
    icon: 'users' as const,
  },
  {
    to: '/admin/documents',
    title: 'Manage documents',
    description: 'Review and manage organizational knowledge.',
    icon: 'documents' as const,
  },
  {
    to: '/admin/analytics',
    title: 'User analytics',
    description: 'Explore adoption and user activity.',
    icon: 'user-analytics' as const,
  },
  {
    to: '/admin/analytics/ai',
    title: 'AI analytics',
    description: 'Monitor assistant usage and performance.',
    icon: 'ai-analytics' as const,
  },
  {
    to: '/admin/analytics/knowledge',
    title: 'Knowledge analytics',
    description: 'Understand document and retrieval activity.',
    icon: 'knowledge-analytics' as const,
  },
] as const

function formatCount(value: number): string {
  return value.toLocaleString()
}

function metricValue(
  isLoading: boolean,
  isError: boolean,
  format: () => string,
): { value: string; isLoading: boolean } {
  if (isLoading) {
    return { value: '', isLoading: true }
  }
  if (isError) {
    return { value: 'Unavailable', isLoading: false }
  }
  return { value: format(), isLoading: false }
}

function resolveHealthStatus(
  isLoading: boolean,
  isError: boolean,
  value: ServiceHealthStatus | undefined,
): ServiceHealthStatus | null {
  if (isLoading || isError || !value) {
    return null
  }
  return value
}

export default function AdminDashboardPage() {
  const resourcesQuery = useResourceMetrics()
  const healthQuery = useSystemMonitoring()

  const resourcesLoading = resourcesQuery.isLoading && !resourcesQuery.data
  const resourcesError = resourcesQuery.isError && !resourcesQuery.data
  const resources = resourcesQuery.data

  const users = metricValue(resourcesLoading, resourcesError, () =>
    formatCount(resources!.total_users),
  )
  const documents = metricValue(resourcesLoading, resourcesError, () =>
    formatCount(resources!.total_documents),
  )
  const conversations = metricValue(resourcesLoading, resourcesError, () =>
    formatCount(resources!.total_conversations),
  )
  const storage = metricValue(resourcesLoading, resourcesError, () =>
    formatBytes(resources!.storage_usage_bytes),
  )

  const healthLoading = healthQuery.isLoading && !healthQuery.data
  const healthError = healthQuery.isError && !healthQuery.data
  const health = healthQuery.data

  const apiStatus = resolveHealthStatus(healthLoading, healthError, health?.api_health)
  const databaseStatus = resolveHealthStatus(
    healthLoading,
    healthError,
    health?.database_health,
  )
  const searchStatus = resolveHealthStatus(
    healthLoading,
    healthError,
    health?.search_service_health,
  )

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-foreground">
          Administration Dashboard
        </h2>
        <p className="mt-1 text-sm text-muted">
          Overview of platform activity and knowledge operations.
        </p>
      </div>

      <section aria-labelledby="admin-dashboard-metrics-heading">
        <h3 id="admin-dashboard-metrics-heading" className="sr-only">
          Dashboard metrics
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <AdminMetricCard
            label="Total Users"
            value={users.value}
            icon="users"
            isLoading={users.isLoading}
          />
          <AdminMetricCard
            label="Total Documents"
            value={documents.value}
            icon="documents"
            isLoading={documents.isLoading}
          />
          <AdminMetricCard
            label="Total Conversations"
            value={conversations.value}
            icon="ai"
            isLoading={conversations.isLoading}
          />
          <AdminMetricCard
            label="Storage Usage"
            value={storage.value}
            icon="storage"
            isLoading={storage.isLoading}
          />
        </div>
      </section>

      <section aria-labelledby="admin-dashboard-health-heading" className="flex flex-col gap-3">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3
              id="admin-dashboard-health-heading"
              className="text-sm font-semibold text-foreground"
            >
              System health
            </h3>
            <p className="mt-0.5 text-sm text-muted">
              Live service status from system monitoring.
            </p>
          </div>
          <Link
            to="/admin/analytics/monitoring"
            className={cn(
              'shrink-0 text-sm font-medium text-accent transition-colors hover:text-accent-hover',
              'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_var(--accent-muted)]',
            )}
          >
            View system monitoring →
          </Link>
        </div>

        <div
          className="grid gap-3 sm:grid-cols-3"
          aria-label={
            healthLoading
              ? 'System health: Loading'
              : healthError
                ? 'System health: Unavailable'
                : 'System health services'
          }
        >
          <AdminHealthStatusCard
            label="API"
            icon="monitoring"
            status={apiStatus}
            isLoading={healthLoading}
          />
          <AdminHealthStatusCard
            label="Database"
            icon="storage"
            status={databaseStatus}
            isLoading={healthLoading}
          />
          <AdminHealthStatusCard
            label="Search"
            icon="search"
            status={searchStatus}
            isLoading={healthLoading}
          />
        </div>
      </section>

      <section aria-labelledby="admin-dashboard-actions-heading" className="flex flex-col gap-3">
        <div>
          <h3
            id="admin-dashboard-actions-heading"
            className="text-sm font-semibold text-foreground"
          >
            Quick actions
          </h3>
          <p className="mt-0.5 text-sm text-muted">
            Jump to common administration and analytics areas.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {QUICK_ACTIONS.map((action) => (
            <AdminQuickActionCard
              key={action.to}
              to={action.to}
              title={action.title}
              description={action.description}
              icon={action.icon}
            />
          ))}
        </div>
      </section>
    </div>
  )
}
