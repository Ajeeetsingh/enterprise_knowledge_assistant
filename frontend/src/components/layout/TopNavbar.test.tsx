import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import TopNavbar from './TopNavbar'

let mobileMatches = true
let desktopMatches = false

vi.mock('@/hooks/useMinWidthMediaQuery', () => ({
  useMinWidthMediaQuery: (minWidth: number) => {
    if (minWidth >= 1024) return desktopMatches
    return mobileMatches
  },
}))

vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({ theme: 'light', toggleTheme: vi.fn() }),
}))

vi.mock('@/contexts/LayoutContext', () => ({
  useLayoutContext: () => ({
    isChatRoute: false,
    openConversationDrawer: vi.fn(),
    openMobileShell: vi.fn(),
    mobileChatPanel: null,
  }),
}))

vi.mock('@/components/layout/UserMenu', () => ({
  default: () => <button type="button" aria-label="User menu">User</button>,
}))

function renderTopNavbar(initialPath = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <TopNavbar sidebarCollapsed={false} onToggleSidebar={() => undefined} />
    </MemoryRouter>,
  )
}

describe('TopNavbar', () => {
  it('renders without hook errors when breakpoints change', () => {
    mobileMatches = true
    desktopMatches = true
    const { rerender } = renderTopNavbar()

    expect(screen.getByRole('button', { name: 'Collapse sidebar' })).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()

    mobileMatches = false
    desktopMatches = false
    rerender(
      <MemoryRouter initialEntries={['/dashboard']}>
        <TopNavbar sidebarCollapsed={false} onToggleSidebar={() => undefined} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: 'Open menu' })).toBeInTheDocument()
  })
})
