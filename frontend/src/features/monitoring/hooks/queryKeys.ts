export const monitoringQueryKeys = {
  all: ['monitoring'] as const,
  summary: () => [...monitoringQueryKeys.all, 'summary'] as const,
  metrics: () => [...monitoringQueryKeys.all, 'metrics'] as const,
}
