import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import AdminSidebar from '../components/AdminSidebar'
import { ADMIN_NAV_ITEMS } from '../constants/navigation'

function renderSidebar(initialRoute = '/admin') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <AdminSidebar collapsed={false} mobileOpen={false} onCloseMobile={() => {}} />
    </MemoryRouter>,
  )
}

describe('AdminSidebar', () => {
  it('renders admin navigation items', () => {
    renderSidebar()

    for (const item of ADMIN_NAV_ITEMS) {
      expect(screen.getByRole('link', { name: item.label })).toHaveAttribute('href', item.path)
    }
  })

  it('highlights the active route', () => {
    renderSidebar('/admin/documents')

    const documentsLink = screen.getByRole('link', { name: 'Documents' })
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' })

    expect(documentsLink.className).toContain('text-primary-700')
    expect(dashboardLink.className).not.toContain('text-primary-700')
  })
})
