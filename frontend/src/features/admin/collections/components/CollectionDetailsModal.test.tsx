import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import CollectionDetailsModal from './CollectionDetailsModal'
import { SEED_COLLECTIONS } from '../data/seedCollections'

describe('CollectionDetailsModal', () => {
  it('opens collection details modal', () => {
    render(
      <CollectionDetailsModal
        isOpen
        collection={SEED_COLLECTIONS[0]!}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('dialog', { name: 'Collection Details' })).toBeInTheDocument()
    expect(screen.getByText('HR Policies')).toBeInTheDocument()
    expect(screen.getByText('col-hr-policies')).toBeInTheDocument()
  })
})
