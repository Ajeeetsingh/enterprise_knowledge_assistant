export const chatQueryKeys = {
  all: ['chat'] as const,
  conversations: () => [...chatQueryKeys.all, 'conversations'] as const,
  messages: (conversationId: string) =>
    [...chatQueryKeys.all, 'messages', conversationId] as const,
  suggestedQuestions: () => [...chatQueryKeys.all, 'suggested-questions'] as const,
}
