import PlaceholderState from '@/components/ui/PlaceholderState'

import AdminMetricCard from '../components/AdminMetricCard'

const MOCK_METRICS = [
  { label: 'Total Users', value: '128', icon: 'users' as const },
  { label: 'Total Documents', value: '542', icon: 'documents' as const },
  { label: 'Collections', value: '12', icon: 'collections' as const },
  { label: 'Storage Usage', value: '24.6 GB', icon: 'storage' as const },
] as const

export default function AdminDashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="font-display text-2xl font-bold text-foreground">
          Administration Dashboard
        </h2>
        <p className="mt-1 text-sm text-muted">
          Overview of platform activity. Metrics shown are placeholders until analytics
          integration in a later phase.
        </p>
      </div>

      <section aria-labelledby="admin-dashboard-metrics-heading">
        <h3 id="admin-dashboard-metrics-heading" className="sr-only">
          Dashboard metrics
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {MOCK_METRICS.map(({ label, value, icon }) => (
            <AdminMetricCard key={label} label={label} value={value} icon={icon} />
          ))}
        </div>
      </section>

      <PlaceholderState>
        Live dashboard widgets will connect to analytics APIs in a future release.
      </PlaceholderState>
    </div>
  )
}
