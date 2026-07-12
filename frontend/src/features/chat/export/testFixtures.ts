import type { Conversation, Message } from '../types'

export const fixtureConversation: Conversation = {
  id: 'conv-1',
  title: 'Remote work policy questions',
  created_at: '2026-01-05T10:00:00.000Z',
  updated_at: '2026-01-05T10:05:00.000Z',
}

export const fixtureMessages: Message[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'What is our remote work policy?',
    citations: [],
    confidence_score: null,
    created_at: '2026-01-05T10:00:10.000Z',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'Employees may work remotely up to 3 days per week with manager approval.',
    citations: [
      {
        source: 'GTFS-HR-002_Remote_Work_Policy.pdf',
        excerpt: 'Employees may work remotely up to three (3) days per week...',
        confidence: 0.91,
        page: 2,
      },
      {
        source: 'GTFS-HR-001_Employee_Handbook.pdf',
        excerpt: 'All remote arrangements require written manager approval.',
        confidence: 0.74,
        page: 14,
      },
    ],
    confidence_score: 0.88,
    created_at: '2026-01-05T10:00:15.000Z',
  },
]
