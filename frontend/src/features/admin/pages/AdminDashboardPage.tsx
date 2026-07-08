import AdminMetricCard from '../components/AdminMetricCard'

const MOCK_METRICS = [
  { label: 'Total Users', value: '128' },
  { label: 'Total Documents', value: '542' },
  { label: 'Collections', value: '12' },
  { label: 'Storage Usage', value: '24.6 GB' },
] as const

export default function AdminDashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">
          Administration Dashboard
        </h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Overview of platform activity. Metrics shown are placeholders until analytics
          integration in a later phase.
        </p>
      </div>

      <section aria-labelledby="admin-dashboard-metrics-heading">
        <h3 id="admin-dashboard-metrics-heading" className="sr-only">
          Dashboard metrics
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {MOCK_METRICS.map(({ label, value }) => (
            <AdminMetricCard key={label} label={label} value={value} />
          ))}
        </div>
      </section>
    </div>
  )
}
