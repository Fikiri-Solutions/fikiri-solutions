import React from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CRM } from '../pages/CRM'

const { apiClientMock, addToastMock } = vi.hoisted(() => ({
  apiClientMock: {
    getLeads: vi.fn(),
    previewLeadsCsv: vi.fn(),
    importLeadsCsv: vi.fn(),
    exportLeadsCsv: vi.fn(),
    addLead: vi.fn(),
    updateLead: vi.fn(),
  },
  addToastMock: vi.fn(),
}))

vi.mock('../services/apiClient', () => ({
  apiClient: apiClientMock,
}))

vi.mock('../components/Toast', () => ({
  useToast: () => ({ addToast: addToastMock }),
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
  Droppable: ({ children }: { children: (provided: any, snapshot: any) => React.ReactNode }) => (
    <div>{children({ droppableProps: {}, innerRef: vi.fn(), placeholder: null }, { isDraggingOver: false })}</div>
  ),
  Draggable: ({ children }: { children: (provided: any, snapshot: any) => React.ReactNode }) => (
    <div>{children({ draggableProps: {}, dragHandleProps: {}, innerRef: vi.fn() }, { isDragging: false })}</div>
  ),
}))

const uploadCsv = (container: HTMLElement, file = new File(['email,name\na@example.com,Ada'], 'leads.csv', { type: 'text/csv' })) => {
  const input = container.querySelector('input[type="file"]') as HTMLInputElement
  expect(input).toBeTruthy()
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

describe('CRM CSV import preview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiClientMock.getLeads.mockResolvedValue([])
    apiClientMock.previewLeadsCsv.mockResolvedValue({
      rows: [{ row: 2, email: 'a@example.com', name: 'Ada', status: 'ok' }],
      summary: { ok: 1, duplicate: 0, invalid: 0, total: 1 },
    })
    apiClientMock.importLeadsCsv.mockResolvedValue({
      imported: 1,
      created: 1,
      updated: 0,
      skipped: 0,
      skipped_details: [],
      total_rows: 1,
    })
  })

  it('previews a selected CSV before allowing import confirmation', async () => {
    const { container } = render(<CRM />)
    const file = uploadCsv(container)

    await waitFor(() => expect(apiClientMock.previewLeadsCsv).toHaveBeenCalledWith(file))
    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalled()
    expect(await screen.findByText(/CSV preview ready: leads\.csv/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm import/i })).toBeEnabled()
  })

  it('imports only after explicit confirmation', async () => {
    const { container } = render(<CRM />)
    const file = uploadCsv(container)

    await screen.findByText(/CSV preview ready: leads\.csv/i)
    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /confirm import/i }))

    await waitFor(() => expect(apiClientMock.importLeadsCsv).toHaveBeenCalledWith(file))
    expect(await screen.findByText(/✔ 1 leads imported/i)).toBeInTheDocument()
  })

  it('cancels a preview without importing', async () => {
    const { container } = render(<CRM />)
    uploadCsv(container)

    await screen.findByText(/CSV preview ready: leads\.csv/i)
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.queryByText(/CSV preview ready/i)).not.toBeInTheDocument())
  })

  it('blocks import and displays preview errors for invalid rows', async () => {
    apiClientMock.previewLeadsCsv.mockResolvedValueOnce({
      rows: [
        { row: 2, email: '', name: 'No Email', status: 'invalid', reason: 'missing email' },
        { row: 3, email: 'duplicate@example.com', name: 'Duplicate', status: 'duplicate' },
      ],
      summary: { ok: 0, duplicate: 1, invalid: 1, total: 2 },
    })

    const { container } = render(<CRM />)
    uploadCsv(container)

    expect(await screen.findByText(/Import blocked until invalid rows are fixed/i)).toBeInTheDocument()
    expect(screen.getByText(/Row 2: missing email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm import/i })).toBeDisabled()
    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalled()
  })

  it('allows duplicate-only previews to be confirmed because duplicates are not blocking errors', async () => {
    apiClientMock.previewLeadsCsv.mockResolvedValueOnce({
      rows: [{ row: 2, email: 'duplicate@example.com', name: 'Duplicate', status: 'duplicate' }],
      summary: { ok: 0, duplicate: 1, invalid: 0, total: 1 },
    })

    const { container } = render(<CRM />)
    const file = uploadCsv(container)

    await screen.findByText(/CSV preview ready: leads\.csv/i)
    expect(screen.getByText('Duplicate rows')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm import/i })).toBeEnabled()

    fireEvent.click(screen.getByRole('button', { name: /confirm import/i }))

    await waitFor(() => expect(apiClientMock.importLeadsCsv).toHaveBeenCalledWith(file))
  })

  it('clears the previous pending file when a new CSV preview is selected', async () => {
    const { container } = render(<CRM />)
    const firstFile = uploadCsv(container, new File(['email,name\nfirst@example.com,First'], 'first.csv', { type: 'text/csv' }))

    await screen.findByText(/CSV preview ready: first\.csv/i)

    apiClientMock.previewLeadsCsv.mockResolvedValueOnce({
      rows: [{ row: 2, email: '', name: 'No Email', status: 'invalid', reason: 'missing email' }],
      summary: { ok: 0, duplicate: 0, invalid: 1, total: 1 },
    })
    const secondFile = uploadCsv(container, new File(['email,name\n,No Email'], 'second.csv', { type: 'text/csv' }))

    await waitFor(() => expect(apiClientMock.previewLeadsCsv).toHaveBeenLastCalledWith(secondFile))
    expect(screen.queryByText(/CSV preview ready: first\.csv/i)).not.toBeInTheDocument()
    expect(await screen.findByText(/CSV preview ready: second\.csv/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /confirm import/i })).toBeDisabled()
    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalledWith(firstFile)
  })

  it('shows user-friendly preview errors when preview fails', async () => {
    apiClientMock.previewLeadsCsv.mockRejectedValueOnce(new Error('CSV must have email and name columns'))

    const { container } = render(<CRM />)
    uploadCsv(container)

    expect(await screen.findByText(/CSV must have email and name columns/i)).toBeInTheDocument()
    expect(apiClientMock.importLeadsCsv).not.toHaveBeenCalled()
  })
})
