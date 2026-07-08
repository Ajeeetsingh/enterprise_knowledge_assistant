import { Card } from '@/components/ui'

export interface AdminComingSoonPageProps {
  title: string
  phaseLabel: string
}

export default function AdminComingSoonPage({ title, phaseLabel }: AdminComingSoonPageProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">{title}</h2>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          This section is part of the admin portal foundation.
        </p>
      </div>

      <Card className="max-w-lg">
        <p className="text-base font-medium text-neutral-900 dark:text-neutral-50">Coming Soon</p>
        <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          {title} will be available in {phaseLabel}.
        </p>
      </Card>
    </div>
  )
}
