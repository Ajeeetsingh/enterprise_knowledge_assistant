import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AIAnalyticsPage from './AIAnalyticsPage'

vi.mock('../hooks', () => ({
  useAIAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_questions: 12,
      responses_generated: 10,
      average_response_time_seconds: 2.5,
      average_retrieval_time_seconds: null,
      average_retrieved_documents: 2.1,
      citation_usage_rate: 80,
      retrieval_success_rate: 83.3,
      retrieval_failure_rate: 16.7,
      ai_error_rate: 16.7,
      average_confidence_score: 0.87,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useAITrends: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      questions: { event_type: 'chat.question.asked', points: { '2026-06-27': 2 } },
      responses: { event_type: 'chat.answer.generated', points: { '2026-06-27': 2 } },
      retrieval_success: { event_type: 'retrieval_success', points: { '2026-06-27': 2 } },
      retrieval_failures: { event_type: 'chat.retrieval.failed', points: {} },
      average_response_time: { event_type: 'average_response_time_seconds', points: { '2026-06-27': 2 } },
      citation_usage: { event_type: 'citation_usage', points: { '2026-06-27': 1 } },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useRetrievalAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      average_retrieved_chunks: 2.1,
      average_retrieval_latency_seconds: null,
      retrieval_success_percentage: 83.3,
      empty_retrievals: 1,
      collection_distribution: { 'policy.txt': 2 },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useTopQuestions: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      items: [],
      total: 0,
      average_citations_per_response: 2,
      responses_without_citations: 1,
      questions_without_documents: 1,
      quality_summary: '10 responses generated',
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useFailureAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: { items: [], total: 0, limit: 10, offset: 0, start_date: '', end_date: '' },
    refetch: vi.fn(),
  }),
}))

describe('AIAnalyticsPage', () => {
  it('renders AI analytics dashboard sections', () => {
    render(<AIAnalyticsPage />)

    expect(screen.getByRole('heading', { name: 'AI Analytics' })).toBeInTheDocument()
    expect(screen.getByLabelText('Total AI Questions: 12')).toBeInTheDocument()
    expect(screen.getByText('Top Questions')).toBeInTheDocument()
    expect(screen.getByText('Failed Retrievals')).toBeInTheDocument()
  })
})
