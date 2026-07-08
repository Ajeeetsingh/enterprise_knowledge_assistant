export const userQueryKeys = {
  all: ['users'] as const,
  list: () => [...userQueryKeys.all, 'list'] as const,
  detail: (userId: string) => [...userQueryKeys.all, 'detail', userId] as const,
  roles: () => [...userQueryKeys.all, 'roles'] as const,
}
