export const dashboardQueryKeys = {
  all: ['dashboard'] as const,
  summary: () => [...dashboardQueryKeys.all, 'summary'] as const,
}
