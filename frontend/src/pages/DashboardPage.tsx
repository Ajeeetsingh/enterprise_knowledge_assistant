import { useAuth } from '@/contexts/AuthContext'
import {
  ContinueWorkPanel,
  DashboardAskBar,
  DashboardStatsRow,
  QuickActionsGrid,
  RecentDocumentsPanel,
  SystemOverviewCard,
  buildDashboardGreeting,
  useWorkspaceSummary,
} from '@/features/dashboard'
import { useConversations } from '@/features/chat/hooks/useConversations'
import { useDocuments } from '@/features/documents/hooks/useDocuments'
import { isAdminUser } from '@/types/permissions'

export default function DashboardPage() {
  const { user } = useAuth()
  const greeting = buildDashboardGreeting(user?.full_name)

  const summaryQuery = useWorkspaceSummary()
  const conversationsQuery = useConversations()
  const documentsQuery = useDocuments({ limit: 10, offset: 0 })

  const showSystemOverview = isAdminUser(user)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <header className="space-y-1">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-[1.75rem]">
          {greeting.title}
        </h1>
        <p className="text-sm text-muted sm:text-base">{greeting.subtitle}</p>
      </header>

      <section aria-label="Ask the knowledge assistant" className="w-full">
        <DashboardAskBar />
      </section>

      <DashboardStatsRow
        summary={summaryQuery.data}
        isLoading={summaryQuery.isLoading}
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ContinueWorkPanel
          conversations={conversationsQuery.data?.items ?? []}
          isLoading={conversationsQuery.isLoading}
        />
        <RecentDocumentsPanel
          documents={documentsQuery.data?.items ?? []}
          isLoading={documentsQuery.isLoading}
        />
      </div>

      <QuickActionsGrid user={user} />

      {showSystemOverview && <SystemOverviewCard />}
    </div>
  )
}
