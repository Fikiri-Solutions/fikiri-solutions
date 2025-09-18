import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { ApiClient, LeadData } from '../services/apiClient'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('ApiClient - CRM Data Mapping', () => {
  let apiClient: ApiClient
  let mockAxiosInstance: any

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks()
    
    // Create mock axios instance
    mockAxiosInstance = {
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }
    
    // Mock axios.create to return our mock instance
    mockedAxios.create.mockReturnValue(mockAxiosInstance)
    
    // Create ApiClient instance
    apiClient = new ApiClient()
  })

  describe('getLeads() - Data Mapping Tests', () => {
    it('should correctly map backend response to frontend LeadData interface', async () => {
      // Mock backend response (actual format from our API)
      const mockBackendResponse = {
        data: {
          success: true,
          leads: [
            {
              id: 'test-id-1',
              name: 'John Doe',
              email: 'john@example.com',
              company: 'Acme Corp',
              stage: 'new',
              score: 8,
              last_contact: '2025-09-18T10:00:00Z',
              source: 'web',
              created_at: '2025-09-18T09:00:00Z'
            },
            {
              id: 'test-id-2',
              name: 'Jane Smith',
              email: 'jane@example.com',
              // Missing company field
              stage: 'contacted',
              // Missing score field
              last_contact: null,
              source: 'manual',
              created_at: '2025-09-18T08:00:00Z'
            }
          ],
          count: 2,
          timestamp: '2025-09-18T10:00:00Z'
        }
      }

      mockAxiosInstance.get.mockResolvedValue(mockBackendResponse)

      // Call the method
      const result = await apiClient.getLeads()

      // Verify axios was called with correct endpoint
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/crm/leads')

      // Verify data mapping
      expect(result).toHaveLength(2)
      
      // Test first lead - complete data
      expect(result[0]).toEqual({
        id: 'test-id-1',
        name: 'John Doe',
        email: 'john@example.com',
        company: 'Acme Corp',
        stage: 'new',
        score: 8,
        lastContact: '2025-09-18T10:00:00Z',
        source: 'web'
      })

      // Test second lead - missing fields handled
      expect(result[1]).toEqual({
        id: 'test-id-2',
        name: 'Jane Smith',
        email: 'jane@example.com',
        company: '', // Should default to empty string
        stage: 'contacted',
        score: 0, // Should default to 0
        lastContact: '2025-09-18T08:00:00Z', // Should fallback to created_at
        source: 'manual'
      })
    })

    it('should handle empty leads array', async () => {
      const mockBackendResponse = {
        data: {
          success: true,
          leads: [],
          count: 0,
          timestamp: '2025-09-18T10:00:00Z'
        }
      }

      mockAxiosInstance.get.mockResolvedValue(mockBackendResponse)

      const result = await apiClient.getLeads()

      expect(result).toEqual([])
      expect(result).toHaveLength(0)
    })

    it('should handle missing leads property in response', async () => {
      const mockBackendResponse = {
        data: {
          success: true,
          // Missing leads property
          count: 0,
          timestamp: '2025-09-18T10:00:00Z'
        }
      }

      mockAxiosInstance.get.mockResolvedValue(mockBackendResponse)

      const result = await apiClient.getLeads()

      expect(result).toEqual([])
    })

    it('should handle API errors gracefully', async () => {
      const error = new Error('Network error')
      mockAxiosInstance.get.mockRejectedValue(error)

      await expect(apiClient.getLeads()).rejects.toThrow('Network error')
    })

    it('should handle malformed backend data', async () => {
      const mockBackendResponse = {
        data: {
          success: true,
          leads: [
            {
              id: 'test-id',
              name: 'Test User',
              email: 'test@example.com',
              // Missing required fields
              stage: 'new',
              source: 'web'
            }
          ]
        }
      }

      mockAxiosInstance.get.mockResolvedValue(mockBackendResponse)

      const result = await apiClient.getLeads()

      // Should handle missing fields gracefully
      expect(result[0]).toEqual({
        id: 'test-id',
        name: 'Test User',
        email: 'test@example.com',
        company: '', // Default value
        stage: 'new',
        score: 0, // Default value
        lastContact: undefined, // Will be undefined if both last_contact and created_at are missing
        source: 'web'
      })
    })
  })

  describe('addLead() - Data Validation Tests', () => {
    it('should send lead data in correct format', async () => {
      const mockLeadData: LeadData = {
        id: 'test-id',
        name: 'Test User',
        email: 'test@example.com',
        company: 'Test Corp',
        stage: 'new',
        score: 5,
        lastContact: '2025-09-18T10:00:00Z',
        source: 'web'
      }

      const mockResponse = {
        data: {
          success: true,
          lead: mockLeadData
        }
      }

      mockAxiosInstance.post.mockResolvedValue(mockResponse)

      const result = await apiClient.addLead(mockLeadData)

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/crm/leads', mockLeadData)
      expect(result).toEqual(mockLeadData)
    })

    it('should handle addLead API errors', async () => {
      const mockLeadData: LeadData = {
        id: 'test-id',
        name: 'Test User',
        email: 'test@example.com',
        company: 'Test Corp',
        stage: 'new',
        score: 5,
        lastContact: '2025-09-18T10:00:00Z',
        source: 'web'
      }

      const error = new Error('Validation error')
      mockAxiosInstance.post.mockRejectedValue(error)

      await expect(apiClient.addLead(mockLeadData)).rejects.toThrow('Validation error')
    })
  })
})

