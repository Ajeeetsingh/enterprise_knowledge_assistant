import Card from '@/components/ui/Card'

export interface AdminMetricCardProps {
  label: string
  value: string
}

export default function AdminMetricCard({ label, value }: AdminMetricCardProps) {
  return (
    <Card>
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">{label}</p>
      <p
        className="mt-2 text-3xl font-bold tabular-nums text-neutral-900 dark:text-neutral-50"
        aria-label={`${label}: ${value}`}
      >
        {value}
      </p>
    </Card>
  )
}
