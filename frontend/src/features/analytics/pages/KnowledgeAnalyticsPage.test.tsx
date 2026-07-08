import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import KnowledgeAnalyticsPage from './KnowledgeAnalyticsPage'

vi.mock('../hooks', () => ({
  useKnowledgeAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      total_documents: 24,
      active_documents: 22,
      stale_documents: 3,
      unused_documents: 5,
      average_document_views: 2.4,
      average_citations_per_document: 1.8,
      search_success_rate: 78.5,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useDocumentAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      most_viewed: [
        {
          document_id: '1',
          filename: 'policy.txt',
          collection: 'HR',
          view_count: 8,
          citation_count: 8,
        },
      ],
      least_viewed: [],
      total_most_viewed: 1,
      total_least_viewed: 0,
      average_document_views: 2.4,
      average_citations_per_document: 1.8,
      document_usage_trend: { event_type: 'document_usage', points: { '2026-06-27': 3 } },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useCollectionAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      items: [],
      total: 0,
      documents_per_collection: { HR: 5 },
      collection_popularity: { HR: 8 },
      retrieval_distribution: { HR: 8 },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useSearchAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      topics: [],
      documents: [],
      collections: [],
      total_topics: 0,
      total_documents: 0,
      total_collections: 0,
      searches_with_no_results: 2,
      search_success_rate: 78.5,
      search_trend: { event_type: 'chat.question.asked', points: { '2026-06-27': 4 } },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useKnowledgeGapAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      items: [],
      total: 0,
      questions_without_documents: 1,
      never_cited_documents: 2,
      never_searched_documents: 3,
      low_engagement_collections: 1,
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
  useFreshnessAnalytics: () => ({
    isLoading: false,
    isFetching: false,
    isError: false,
    data: {
      recent_uploads: [],
      oldest_documents: [],
      recently_updated: [],
      longest_inactive: [],
      total_recent_uploads: 0,
      total_oldest_documents: 0,
      total_recently_updated: 0,
      total_longest_inactive: 0,
      upload_trend: { event_type: 'document.uploaded', points: {} },
      start_date: '2026-06-20T00:00:00Z',
      end_date: '2026-06-27T23:59:59Z',
    },
    refetch: vi.fn(),
  }),
}))

describe('KnowledgeAnalyticsPage', () => {
  it('renders knowledge analytics dashboard sections', () => {
    render(<KnowledgeAnalyticsPage />)

    expect(screen.getByRole('heading', { name: 'Knowledge Analytics' })).toBeInTheDocument()
    expect(screen.getByText('Total Documents')).toBeInTheDocument()
    expect(screen.getByText('Document Usage')).toBeInTheDocument()
    expect(screen.getByText('policy.txt')).toBeInTheDocument()
  })
})
