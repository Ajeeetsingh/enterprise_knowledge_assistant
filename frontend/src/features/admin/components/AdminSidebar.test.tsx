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

  it('renders grouped section labels', () => {
    renderSidebar()

    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.getByText('People')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('highlights the active route', () => {
    renderSidebar('/admin/documents')

    const documentsLink = screen.getByRole('link', { name: 'Documents' })
    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' })

    expect(documentsLink.className).toContain('text-accent')
    expect(dashboardLink.className).not.toContain('text-accent')
  })

  it('renders distinct icons when collapsed instead of ambiguous letters', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <AdminSidebar collapsed mobileOpen={false} onCloseMobile={() => {}} />
      </MemoryRouter>,
    )

    const documentsLink = screen.getByRole('link', { name: 'Documents' })
    const uploadsLink = screen.getByRole('link', { name: 'Uploads' })

    expect(documentsLink.querySelector('.nav-icon')).toBeInTheDocument()
    expect(uploadsLink.querySelector('.nav-icon')).toBeInTheDocument()
    expect(documentsLink.textContent).not.toMatch(/^D$/i)
    expect(uploadsLink.textContent).not.toMatch(/^U$/i)
  })
})
