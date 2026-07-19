import type { ComponentProps } from 'react'

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Conversation } from '../types'
import ConversationList from './ConversationList'

function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: 'conv-1',
    title: 'Commercial Paper Issuers',
    created_at: '2026-07-12T10:00:00Z',
    updated_at: '2026-07-12T10:00:00Z',
    ...overrides,
  }
}

function renderList(overrides: Partial<ComponentProps<typeof ConversationList>> = {}) {
  const props: ComponentProps<typeof ConversationList> = {
    conversations: [makeConversation()],
    selectedId: null,
    isLoading: false,
    isCreating: false,
    error: null,
    onSelect: vi.fn(),
    onCreate: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  }
  render(<ConversationList {...props} />)
  return props
}

async function openRenameMenu(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Conversation actions' }))
  await user.click(screen.getByRole('menuitem', { name: 'Rename' }))
}

describe('ConversationList inline rename', () => {
  it('renders conversation titles', () => {
    renderList()
    expect(screen.getByText('Commercial Paper Issuers')).toBeInTheDocument()
  })

  it('opens an inline textbox (not a modal) when Rename is clicked', async () => {
    const user = userEvent.setup()
    renderList()

    await openRenameMenu(user)

    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    expect(input).toBeInTheDocument()
    expect(input).toHaveValue('Commercial Paper Issuers')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('saves the new title on Enter', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.clear(input)
    await user.type(input, 'New Title{Enter}')

    expect(onRename).toHaveBeenCalledWith('conv-1', 'New Title')
    expect(screen.queryByRole('textbox', { name: 'Conversation title' })).not.toBeInTheDocument()
  })

  it('discards changes on Escape without calling onRename', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.clear(input)
    await user.type(input, 'Discarded Title{Escape}')

    expect(onRename).not.toHaveBeenCalled()
    expect(screen.queryByRole('textbox', { name: 'Conversation title' })).not.toBeInTheDocument()
    expect(screen.getByText('Commercial Paper Issuers')).toBeInTheDocument()
  })

  it('saves on blur (click outside)', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.clear(input)
    await user.type(input, 'Blurred Title')
    await user.click(document.body)

    expect(onRename).toHaveBeenCalledWith('conv-1', 'Blurred Title')
  })

  it('does not call onRename when the title is unchanged', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.type(input, '{Enter}')

    expect(onRename).not.toHaveBeenCalled()
  })

  it('does not call onRename when the trimmed title is blank', async () => {
    const user = userEvent.setup()
    const onRename = vi.fn()
    renderList({ onRename })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.clear(input)
    await user.type(input, '   {Enter}')

    expect(onRename).not.toHaveBeenCalled()
  })

  it('does not select the conversation when clicking into the rename input', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    renderList({ onSelect })

    await openRenameMenu(user)
    const input = screen.getByRole('textbox', { name: 'Conversation title' })
    await user.click(input)

    expect(onSelect).not.toHaveBeenCalled()
  })
})
