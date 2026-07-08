import { Card } from '@/components/ui'

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4 text-center sm:text-left">
      <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-50">Dashboard</h1>
      <Card>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">
          Dashboard features will be implemented in a future phase. This page uses
          AppLayout with Sidebar, TopNavbar, and PageContainer.
        </p>
      </Card>
    </div>
  )
}
