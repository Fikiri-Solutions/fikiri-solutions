import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CRM } from '../pages/CRM'

const emptyPagination = {
  total_count: 0,
  returned_count: 0,
  limit: 50,
  offset: 0,
  has_more: false,
}

const sampleLead = {
  id: '1',
  name: 'Ada Lovelace',
  email: 'ada@example.com',
  company: 'Analytical',
  stage: 'new',
  score: 10,
  lastContact: '2025-01-01T00:00:00Z',
  source: 'web',
}

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
    getLeads: vi.fn(),
    getLeadsPage: vi.fn(),
    previewLeadsCsv: vi.fn(),
    importLeadsCsv: vi.fn(),
    exportLeadsCsv: vi.fn(),
    addLead: vi.fn(),
    updateLeadStage: vi.fn(),
  },
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

vi.mock('../components/ErrorMessage', () => ({
  ErrorMessage: ({ title, message }: { title: string; message: string }) => (
    <div role="alert">
      <strong>{title}</strong>
      <span>{message}</span>
    </div>
  ),
  getUserFriendlyError: (error: Error) => ({
    type: 'error',
    title: 'Something went wrong',
    message: error.message || 'Please try again.',
  }),
}))

vi.mock('@hello-pangea/dnd', () => ({
  DragDropContext: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Droppable: ({ children }: { children: (provided: unknown, snapshot: unknown) => React.ReactNode }) => (
    <div>{children({ droppableProps: {}, innerRef: vi.fn(), placeholder: null }, { isDraggingOver: false })}</div>
  ),
  Draggable: ({ children }: { children: (provided: unknown, snapshot: unknown) => React.ReactNode }) => (
    <div>{children({ draggableProps: {}, dragHandleProps: {}, innerRef: vi.fn() }, { isDragging: false })}</div>
  ),
}))

describe('CRM table server pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClientMock.getLeads.mockResolvedValue([sampleLead])
    apiClientMock.getLeadsPage.mockResolvedValue({
      leads: [sampleLead],
      pagination: { ...emptyPagination, total_count: 51, returned_count: 1, has_more: true },
    })
  })

  it('loads table with default limit 50 and offset 0', async () => {
    render(<CRM />)
    await waitFor(() =>
      expect(apiClientMock.getLeadsPage).toHaveBeenCalledWith(
        expect.objectContaining({ limit: 50, offset: 0 })
      )
    )
    expect(apiClientMock.getLeads).toHaveBeenCalled()
  })

  it('sends q on search and resets offset', async () => {
    render(<CRM />)
    await waitFor(() => expect(apiClientMock.getLeadsPage).toHaveBeenCalled())

    apiClientMock.getLeadsPage.mockClear()
    fireEvent.change(screen.getByLabelText(/search leads/i), { target: { value: 'ada' } })

    await waitFor(
      () =>
        expect(apiClientMock.getLeadsPage).toHaveBeenCalledWith(
          expect.objectContaining({ q: 'ada', offset: 0 })
        ),
      { timeout: 800 }
    )
  })

  it('sends stage filter and resets offset', async () => {
    render(<CRM />)
    await waitFor(() => expect(apiClientMock.getLeadsPage).toHaveBeenCalled())

    apiClientMock.getLeadsPage.mockClear()
    fireEvent.change(screen.getByLabelText(/filter by pipeline stage/i), {
      target: { value: 'qualified' },
    })

    await waitFor(() =>
      expect(apiClientMock.getLeadsPage).toHaveBeenCalledWith(
        expect.objectContaining({ stage: 'qualified', offset: 0 })
      )
    )
  })

  it('Previous is disabled at offset 0 and Next advances offset', async () => {
    render(<CRM />)
    await waitFor(() => screen.getByRole('button', { name: 'Next' }))

    const previous = screen.getByRole('button', { name: 'Previous' })
    const next = screen.getByRole('button', { name: 'Next' })
    expect(previous).toBeDisabled()
    expect(next).not.toBeDisabled()

    apiClientMock.getLeadsPage.mockClear()
    fireEvent.click(next)

    await waitFor(() =>
      expect(apiClientMock.getLeadsPage).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 50 })
      )
    )
  })

  it('disables Next when has_more is false', async () => {
    apiClientMock.getLeadsPage.mockResolvedValue({
      leads: [sampleLead],
      pagination: { total_count: 1, returned_count: 1, limit: 50, offset: 0, has_more: false },
    })
    render(<CRM />)
    await waitFor(() => screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  })

  it('shows paginated range text from server total_count', async () => {
    render(<CRM />)
    expect(await screen.findByText(/showing 1–1 of 51/i)).toBeInTheDocument()
  })
})
