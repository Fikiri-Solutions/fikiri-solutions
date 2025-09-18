import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CRM } from '../pages/CRM'
import { ApiClient } from '../services/apiClient'

// Mock the API client with realistic responses
vi.mock('../services/apiClient', () => ({
  ApiClient: vi.fn().mockImplementation(() => ({
    getLeads: vi.fn(),
    addLead: vi.fn()
  })),
  LeadData: {}
}))

// Mock components
vi.mock('../components/FeatureStatus', () => ({
  FeatureStatus: ({ status }: { status: any }) => (
    <div data-testid="feature-status">{status}</div>
  ),
  getFeatureStatus: vi.fn().mockReturnValue('active')
}))

vi.mock('../components/EmptyState', () => ({
  EmptyState: ({ title, description }: { title: string; description: string }) => (
    <div data-testid="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}))

vi.mock('../components/ErrorMessage', () => ({
  ErrorMessage: ({ error }: { error: any }) => (
    <div data-testid="error-message">{error?.message}</div>
  ),
  getUserFriendlyError: vi.fn().mockReturnValue({
    type: 'error',
    title: 'Error',
    message: 'Something went wrong'
  })
}))

describe('CRM Integration Tests - End-to-End Workflow', () => {
  let queryClient: QueryClient
  let mockApiClient: any

  beforeEach(() => {
    vi.clearAllMocks()
    
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          staleTime: 0,
          gcTime: 0
        }
      }
    })

    mockApiClient = {
      getLeads: vi.fn(),
      addLead: vi.fn()
    }

    vi.mocked(ApiClient).mockImplementation(() => mockApiClient)
  })

  const renderCRM = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CRM />
      </QueryClientProvider>
    )
  }

  describe('Complete CRM Workflow Tests', () => {
    it('should handle complete lead management workflow', async () => {
      // Initial state - empty leads
      mockApiClient.getLeads.mockResolvedValueOnce([])

      renderCRM()

      // Should show empty state initially
      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument()
      })

      // Open add lead modal
      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add New Lead')).toBeInTheDocument()
      })

      // Fill out form
      const nameInput = screen.getByPlaceholderText('Enter lead name')
      const emailInput = screen.getByPlaceholderText('Enter email address')
      const companyInput = screen.getByPlaceholderText('Enter company name')
      const phoneInput = screen.getByPlaceholderText('Enter phone number')

      fireEvent.change(nameInput, { target: { value: 'Integration Test User' } })
      fireEvent.change(emailInput, { target: { value: 'integration@test.com' } })
      fireEvent.change(companyInput, { target: { value: 'Test Company' } })
      fireEvent.change(phoneInput, { target: { value: '555-1234' } })

      // Mock successful add lead response
      const newLead = {
        id: 'new-lead-id',
        name: 'Integration Test User',
        email: 'integration@test.com',
        company: 'Test Company',
        stage: 'new',
        score: 0,
        lastContact: '2025-09-18T10:00:00Z',
        source: 'web'
      }

      mockApiClient.addLead.mockResolvedValue(newLead)
      
      // Mock updated leads list after adding
      mockApiClient.getLeads.mockResolvedValueOnce([newLead])

      // Submit form
      const submitButton = screen.getByText('Add Lead')
      fireEvent.click(submitButton)

      // Should call addLead API
      await waitFor(() => {
        expect(mockApiClient.addLead).toHaveBeenCalledWith({
          id: '',
          name: 'Integration Test User',
          email: 'integration@test.com',
          phone: '555-1234',
          company: 'Test Company',
          stage: 'new',
          score: 0,
          lastContact: expect.any(String),
          source: 'web'
        })
      })

      // Should refresh leads list and show new lead
      await waitFor(() => {
        expect(screen.getByText('Integration Test User')).toBeInTheDocument()
        expect(screen.getByText('integration@test.com')).toBeInTheDocument()
        expect(screen.getByText('Test Company')).toBeInTheDocument()
      })

      // Verify stats are updated
      expect(screen.getByText('1')).toBeInTheDocument() // Total leads
    })

    it('should handle search and filter workflow', async () => {
      const mockLeads = [
        {
          id: '1',
          name: 'Alice Johnson',
          email: 'alice@example.com',
          company: 'Alpha Corp',
          stage: 'new',
          score: 7,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        },
        {
          id: '2',
          name: 'Bob Smith',
          email: 'bob@example.com',
          company: 'Beta Inc',
          stage: 'contacted',
          score: 9,
          lastContact: '2025-09-17T15:30:00Z',
          source: 'manual'
        },
        {
          id: '3',
          name: 'Charlie Brown',
          email: 'charlie@example.com',
          company: 'Gamma LLC',
          stage: 'qualified',
          score: 8,
          lastContact: '2025-09-16T12:00:00Z',
          source: 'referral'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      // Wait for leads to load
      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
        expect(screen.getByText('Bob Smith')).toBeInTheDocument()
        expect(screen.getByText('Charlie Brown')).toBeInTheDocument()
      })

      // Test search functionality
      const searchInput = screen.getByPlaceholderText('Search leads...')
      fireEvent.change(searchInput, { target: { value: 'Alice' } })

      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
        expect(screen.queryByText('Bob Smith')).not.toBeInTheDocument()
        expect(screen.queryByText('Charlie Brown')).not.toBeInTheDocument()
      })

      // Clear search
      fireEvent.change(searchInput, { target: { value: '' } })

      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
        expect(screen.getByText('Bob Smith')).toBeInTheDocument()
        expect(screen.getByText('Charlie Brown')).toBeInTheDocument()
      })

      // Test stage filter
      const stageFilter = screen.getByDisplayValue('all')
      fireEvent.change(stageFilter, { target: { value: 'contacted' } })

      await waitFor(() => {
        expect(screen.queryByText('Alice Johnson')).not.toBeInTheDocument()
        expect(screen.getByText('Bob Smith')).toBeInTheDocument()
        expect(screen.queryByText('Charlie Brown')).not.toBeInTheDocument()
      })

      // Test combined search and filter
      fireEvent.change(searchInput, { target: { value: 'Bob' } })
      fireEvent.change(stageFilter, { target: { value: 'all' } })

      await waitFor(() => {
        expect(screen.getByText('Bob Smith')).toBeInTheDocument()
        expect(screen.queryByText('Alice Johnson')).not.toBeInTheDocument()
        expect(screen.queryByText('Charlie Brown')).not.toBeInTheDocument()
      })
    })

    it('should handle error scenarios gracefully', async () => {
      // Test API error on initial load
      const error = new Error('Failed to fetch leads')
      mockApiClient.getLeads.mockRejectedValue(error)

      renderCRM()

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument()
      })

      // Test add lead validation error
      mockApiClient.getLeads.mockResolvedValue([])

      renderCRM()

      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        const submitButton = screen.getByText('Add Lead')
        fireEvent.click(submitButton)
      })

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText('Missing Information')).toBeInTheDocument()
      })

      // Test add lead API error
      const nameInput = screen.getByPlaceholderText('Enter lead name')
      const emailInput = screen.getByPlaceholderText('Enter email address')

      fireEvent.change(nameInput, { target: { value: 'Test User' } })
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })

      const addError = new Error('Failed to add lead')
      mockApiClient.addLead.mockRejectedValue(addError)

      const submitButton = screen.getByText('Add Lead')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument()
      })
    })

    it('should maintain state consistency during operations', async () => {
      const initialLeads = [
        {
          id: '1',
          name: 'Initial User',
          email: 'initial@example.com',
          company: 'Initial Corp',
          stage: 'new',
          score: 5,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(initialLeads)

      renderCRM()

      // Verify initial state
      await waitFor(() => {
        expect(screen.getByText('Initial User')).toBeInTheDocument()
        expect(screen.getByText('1')).toBeInTheDocument() // Total leads
      })

      // Open modal and verify stats don't change
      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add New Lead')).toBeInTheDocument()
        // Stats should still show original count
        expect(screen.getByText('1')).toBeInTheDocument()
      })

      // Cancel modal and verify state is preserved
      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)

      await waitFor(() => {
        expect(screen.queryByText('Add New Lead')).not.toBeInTheDocument()
        expect(screen.getByText('Initial User')).toBeInTheDocument()
        expect(screen.getByText('1')).toBeInTheDocument()
      })
    })
  })

  describe('Performance and UX Tests', () => {
    it('should handle large datasets efficiently', async () => {
      // Create a large dataset
      const largeLeadsList = Array.from({ length: 100 }, (_, i) => ({
        id: `lead-${i}`,
        name: `User ${i}`,
        email: `user${i}@example.com`,
        company: `Company ${i}`,
        stage: ['new', 'contacted', 'qualified'][i % 3],
        score: Math.floor(Math.random() * 10),
        lastContact: '2025-09-18T10:00:00Z',
        source: ['web', 'manual', 'referral'][i % 3]
      }))

      mockApiClient.getLeads.mockResolvedValue(largeLeadsList)

      renderCRM()

      // Should load without performance issues
      await waitFor(() => {
        expect(screen.getByText('100')).toBeInTheDocument() // Total leads
      })

      // Search should work efficiently
      const searchInput = screen.getByPlaceholderText('Search leads...')
      fireEvent.change(searchInput, { target: { value: 'User 50' } })

      await waitFor(() => {
        expect(screen.getByText('User 50')).toBeInTheDocument()
        expect(screen.queryByText('User 51')).not.toBeInTheDocument()
      })
    })

    it('should provide proper loading states', async () => {
      // Mock slow API response
      mockApiClient.getLeads.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve([]), 100))
      )

      renderCRM()

      // Should show loading state
      expect(screen.getByRole('progressbar')).toBeInTheDocument()

      // Should hide loading state when data loads
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
        expect(screen.getByTestId('empty-state')).toBeInTheDocument()
      })
    })
  })
})

