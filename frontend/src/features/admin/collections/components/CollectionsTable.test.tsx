import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import CollectionsTable from './CollectionsTable'
import { SEED_COLLECTIONS } from '../data/seedCollections'

describe('CollectionsTable', () => {
  it('renders collection rows', () => {
    render(
      <CollectionsTable
        collections={SEED_COLLECTIONS.slice(0, 2)}
        onView={vi.fn()}
        onRename={vi.fn()}
        onArchive={vi.fn()}
      />,
    )

    expect(screen.getByText('HR Policies')).toBeInTheDocument()
    expect(screen.getByText('Finance')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders empty state', () => {
    render(
      <CollectionsTable
        collections={[]}
        onView={vi.fn()}
        onRename={vi.fn()}
        onArchive={vi.fn()}
      />,
    )

    expect(screen.getByText('No collections found')).toBeInTheDocument()
  })
})
