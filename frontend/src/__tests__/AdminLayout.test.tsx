import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AdminLayout } from '../pages/admin/AdminLayout'

describe('AdminLayout', () => {
  beforeEach(() => {
    window.scrollTo = vi.fn()
  })

  it('renders Platform Admin header and resets scroll on tenants route', () => {
    render(
      <MemoryRouter initialEntries={['/admin/tenants']}>
        <Routes>
          <Route path="/admin" element={<AdminLayout />}>
            <Route path="tenants" element={<div>Tenants page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: 'Platform Admin' })).toBeInTheDocument()
    expect(screen.getByText('Tenants page')).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
    expect(window.scrollTo).toHaveBeenCalledWith(0, 0)
  })
})
