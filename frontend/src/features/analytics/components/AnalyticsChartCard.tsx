import Card from '@/components/ui/Card'

export interface AnalyticsChartCardProps {
  title: string
  description?: string
  children: React.ReactNode
}

export default function AnalyticsChartCard({
  title,
  description,
  children,
}: AnalyticsChartCardProps) {
  return (
    <Card className="flex flex-col gap-4">
      <div>
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">{title}</h3>
        {description ? (
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{description}</p>
        ) : null}
      </div>
      {children}
    </Card>
  )
}
