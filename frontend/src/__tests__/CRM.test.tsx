import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CRM } from '../pages/CRM'
import { ApiClient, LeadData } from '../services/apiClient'

// Mock the API client
vi.mock('../services/apiClient', () => ({
  ApiClient: vi.fn().mockImplementation(() => ({
    getLeads: vi.fn(),
    addLead: vi.fn()
  })),
  LeadData: {}
}))

// Mock the FeatureStatus component
vi.mock('../components/FeatureStatus', () => ({
  FeatureStatus: ({ status }: { status: any }) => (
    <div data-testid="feature-status">{status}</div>
  ),
  getFeatureStatus: vi.fn().mockReturnValue('active')
}))

// Mock the EmptyState component
vi.mock('../components/EmptyState', () => ({
  EmptyState: ({ title, description }: { title: string; description: string }) => (
    <div data-testid="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}))

// Mock the ErrorMessage component
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

describe('CRM Component - Data Loading and Display', () => {
  let queryClient: QueryClient
  let mockApiClient: any

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()
    
    // Create fresh query client for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          staleTime: 0,
          gcTime: 0
        }
      }
    })

    // Create mock API client
    mockApiClient = {
      getLeads: vi.fn(),
      addLead: vi.fn()
    }

    // Mock the ApiClient constructor
    vi.mocked(ApiClient).mockImplementation(() => mockApiClient)
  })

  const renderCRM = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CRM />
      </QueryClientProvider>
    )
  }

  describe('Data Loading Tests', () => {
    it('should display loading state initially', () => {
      mockApiClient.getLeads.mockImplementation(() => new Promise(() => {})) // Never resolves
      
      renderCRM()
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })

    it('should display leads data when loaded successfully', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'John Doe',
          email: 'john@example.com',
          company: 'Acme Corp',
          stage: 'new',
          score: 8,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        },
        {
          id: '2',
          name: 'Jane Smith',
          email: 'jane@example.com',
          company: 'Tech Inc',
          stage: 'contacted',
          score: 6,
          lastContact: '2025-09-17T15:30:00Z',
          source: 'manual'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
        expect(screen.getByText('jane@example.com')).toBeInTheDocument()
      })

      // Verify stats are calculated correctly
      expect(screen.getByText('2')).toBeInTheDocument() // Total leads
      expect(screen.getByText('0')).toBeInTheDocument() // Qualified leads (none in mock data)
      expect(screen.getByText('1')).toBeInTheDocument() // Contacted leads
    })

    it('should display empty state when no leads', async () => {
      mockApiClient.getLeads.mockResolvedValue([])

      renderCRM()

      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument()
      })
    })

    it('should display error message when API fails', async () => {
      const error = new Error('Failed to fetch leads')
      mockApiClient.getLeads.mockRejectedValue(error)

      renderCRM()

      await waitFor(() => {
        expect(screen.getByTestId('error-message')).toBeInTheDocument()
      })
    })
  })

  describe('Dark Mode Text Visibility Tests', () => {
    it('should have proper dark mode classes on main heading', async () => {
      mockApiClient.getLeads.mockResolvedValue([])
      
      renderCRM()
      
      const heading = screen.getByText('CRM - Lead Management')
      expect(heading).toHaveClass('text-gray-900', 'dark:text-white')
    })

    it('should have proper dark mode classes on description text', async () => {
      mockApiClient.getLeads.mockResolvedValue([])
      
      renderCRM()
      
      const description = screen.getByText('Track and manage your customer leads and relationships.')
      expect(description).toHaveClass('text-gray-600', 'dark:text-gray-400')
    })

    it('should have proper dark mode classes on stats labels', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'Test User',
          email: 'test@example.com',
          company: 'Test Corp',
          stage: 'new',
          score: 5,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        const totalLeadsLabel = screen.getByText('Total Leads')
        expect(totalLeadsLabel).toHaveClass('text-gray-500', 'dark:text-gray-400')
        
        const totalLeadsValue = screen.getByText('1')
        expect(totalLeadsValue).toHaveClass('text-gray-900', 'dark:text-white')
      })
    })

    it('should have proper dark mode classes on table headers', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'Test User',
          email: 'test@example.com',
          company: 'Test Corp',
          stage: 'new',
          score: 5,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        const leadHeader = screen.getByText('Lead')
        expect(leadHeader).toHaveClass('text-gray-500', 'dark:text-gray-400')
        
        const companyHeader = screen.getByText('Company')
        expect(companyHeader).toHaveClass('text-gray-500', 'dark:text-gray-400')
      })
    })

    it('should have proper dark mode classes on table content', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'Test User',
          email: 'test@example.com',
          company: 'Test Corp',
          stage: 'new',
          score: 5,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        const leadName = screen.getByText('Test User')
        expect(leadName).toHaveClass('text-gray-900', 'dark:text-white')
        
        const leadEmail = screen.getByText('test@example.com')
        expect(leadEmail).toHaveClass('text-gray-500', 'dark:text-gray-400')
        
        const companyName = screen.getByText('Test Corp')
        expect(companyName).toHaveClass('text-gray-900', 'dark:text-white')
      })
    })
  })

  describe('Add Lead Modal Tests', () => {
    it('should open add lead modal when button is clicked', async () => {
      mockApiClient.getLeads.mockResolvedValue([])

      renderCRM()

      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        expect(screen.getByText('Add New Lead')).toBeInTheDocument()
      })
    })

    it('should have proper dark mode classes on modal elements', async () => {
      mockApiClient.getLeads.mockResolvedValue([])

      renderCRM()

      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        const modalTitle = screen.getByText('Add New Lead')
        expect(modalTitle).toHaveClass('text-gray-900', 'dark:text-white')
        
        const nameLabel = screen.getByText('Name *')
        expect(nameLabel).toHaveClass('text-gray-700', 'dark:text-gray-300')
        
        const emailLabel = screen.getByText('Email *')
        expect(emailLabel).toHaveClass('text-gray-700', 'dark:text-gray-300')
      })
    })

    it('should validate required fields before submitting', async () => {
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
    })

    it('should submit lead data when form is valid', async () => {
      const mockLeads: LeadData[] = []
      mockApiClient.getLeads.mockResolvedValue(mockLeads)
      mockApiClient.addLead.mockResolvedValue({
        id: 'new-id',
        name: 'New User',
        email: 'new@example.com',
        company: 'New Corp',
        stage: 'new',
        score: 0,
        lastContact: '2025-09-18T10:00:00Z',
        source: 'web'
      })

      renderCRM()

      const addButton = screen.getByText('Add Lead')
      fireEvent.click(addButton)

      await waitFor(() => {
        const nameInput = screen.getByPlaceholderText('Enter lead name')
        const emailInput = screen.getByPlaceholderText('Enter email address')
        const submitButton = screen.getByText('Add Lead')

        fireEvent.change(nameInput, { target: { value: 'New User' } })
        fireEvent.change(emailInput, { target: { value: 'new@example.com' } })
        fireEvent.click(submitButton)
      })

      await waitFor(() => {
        expect(mockApiClient.addLead).toHaveBeenCalledWith({
          id: '',
          name: 'New User',
          email: 'new@example.com',
          phone: '',
          company: '',
          stage: 'new',
          score: 0,
          lastContact: expect.any(String),
          source: 'web'
        })
      })
    })
  })

  describe('Search and Filter Tests', () => {
    it('should filter leads by search term', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'John Doe',
          email: 'john@example.com',
          company: 'Acme Corp',
          stage: 'new',
          score: 8,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        },
        {
          id: '2',
          name: 'Jane Smith',
          email: 'jane@example.com',
          company: 'Tech Inc',
          stage: 'contacted',
          score: 6,
          lastContact: '2025-09-17T15:30:00Z',
          source: 'manual'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
      })

      const searchInput = screen.getByPlaceholderText('Search leads...')
      fireEvent.change(searchInput, { target: { value: 'John' } })

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument()
      })
    })

    it('should filter leads by stage', async () => {
      const mockLeads: LeadData[] = [
        {
          id: '1',
          name: 'John Doe',
          email: 'john@example.com',
          company: 'Acme Corp',
          stage: 'new',
          score: 8,
          lastContact: '2025-09-18T10:00:00Z',
          source: 'web'
        },
        {
          id: '2',
          name: 'Jane Smith',
          email: 'jane@example.com',
          company: 'Tech Inc',
          stage: 'contacted',
          score: 6,
          lastContact: '2025-09-17T15:30:00Z',
          source: 'manual'
        }
      ]

      mockApiClient.getLeads.mockResolvedValue(mockLeads)

      renderCRM()

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('Jane Smith')).toBeInTheDocument()
      })

      const stageFilter = screen.getByDisplayValue('all')
      fireEvent.change(stageFilter, { target: { value: 'new' } })

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.queryByText('Jane Smith')).not.toBeInTheDocument()
      })
    })
  })
})

