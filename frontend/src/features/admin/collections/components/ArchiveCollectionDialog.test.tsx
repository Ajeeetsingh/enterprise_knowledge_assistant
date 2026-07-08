import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import ArchiveCollectionDialog from './ArchiveCollectionDialog'
import { SEED_COLLECTIONS } from '../data/seedCollections'

describe('ArchiveCollectionDialog', () => {
  it('opens archive confirmation dialog', () => {
    render(
      <ArchiveCollectionDialog
        collection={SEED_COLLECTIONS[0]!}
        isOpen
        isSubmitting={false}
        error={null}
        onClose={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )

    expect(screen.getByRole('alertdialog', { name: 'Archive collection?' })).toBeInTheDocument()
  })
})
