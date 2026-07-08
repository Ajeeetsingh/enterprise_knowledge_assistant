export const reportsQueryKeys = {
  all: ['reports'] as const,
  modules: () => [...reportsQueryKeys.all, 'modules'] as const,
  formats: () => [...reportsQueryKeys.all, 'formats'] as const,
}
