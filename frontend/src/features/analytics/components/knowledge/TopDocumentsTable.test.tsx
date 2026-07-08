import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import TopDocumentsTable from './TopDocumentsTable'

describe('TopDocumentsTable', () => {
  it('renders document rows', () => {
    render(
      <TopDocumentsTable
        items={[
          {
            document_id: '1',
            filename: 'policy.txt',
            collection: 'HR',
            view_count: 5,
            citation_count: 5,
          },
        ]}
      />,
    )

    expect(screen.getByText('policy.txt')).toBeInTheDocument()
    expect(screen.getByText('HR')).toBeInTheDocument()
    expect(screen.getAllByText('5')).toHaveLength(2)
  })

  it('renders empty state', () => {
    render(<TopDocumentsTable items={[]} />)

    expect(screen.getByText('No document usage recorded')).toBeInTheDocument()
  })
})
