import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import TopQuestionsTable from './TopQuestionsTable'

describe('TopQuestionsTable', () => {
  it('renders question rows', () => {
    render(
      <TopQuestionsTable
        items={[{ question: 'What is the leave policy?', count: 3 }]}
      />,
    )

    expect(screen.getByText('What is the leave policy?')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders empty state', () => {
    render(<TopQuestionsTable items={[]} />)

    expect(screen.getByText('No questions recorded')).toBeInTheDocument()
  })
})
