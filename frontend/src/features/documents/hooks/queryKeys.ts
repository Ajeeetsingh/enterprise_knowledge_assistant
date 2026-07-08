export const documentQueryKeys = {
  all: ['documents'] as const,
  list: () => [...documentQueryKeys.all, 'list'] as const,
  detail: (documentId: string) => [...documentQueryKeys.all, 'detail', documentId] as const,
}
