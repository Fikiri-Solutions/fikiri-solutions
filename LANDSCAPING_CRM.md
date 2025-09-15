# Landscaping Business CRM Enhancement

## 🌱 Landscaping-Specific Data Model

### Enhanced Client Schema
```python
# core/landscaping_crm_schema.py
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass

@dataclass
class LandscapingClient:
    # Basic Info
    id: str
    name: str
    email: str
    phone: Optional[str]
    
    # Property Information
    property_address: str
    property_size: Optional[str]  # "small", "medium", "large", "commercial"
    property_type: Optional[str]   # "residential", "commercial", "hoa"
    
    # Service Information
    primary_service: str           # "mowing", "landscaping", "tree_trimming", etc.
    service_frequency: str         # "weekly", "bi-weekly", "monthly", "one-time"
    service_history: List[Dict]    # List of completed services
    
    # Scheduling
    last_service_date: Optional[datetime]
    next_service_date: Optional[datetime]
    preferred_service_day: Optional[str]
    preferred_service_time: Optional[str]
    
    # Business Information
    lead_source: str              # "email", "website", "referral", "walk-in"
    lead_score: int               # 1-100 based on value potential
    status: str                   # "new", "qualified", "scheduled", "active", "completed"
    
    # Custom Fields
    special_requests: Optional[str]
    notes: Optional[str]
    attachments: List[str]        # URLs to uploaded files/photos
    
    # Financial
    estimated_value: Optional[float]
    actual_revenue: float = 0.0
    payment_method: Optional[str]
    
    # Communication
    communication_preference: str  # "email", "phone", "text"
    last_contact_date: Optional[datetime]
    follow_up_date: Optional[datetime]

@dataclass
class ServiceRecord:
    id: str
    client_id: str
    service_type: str
    service_date: datetime
    duration_hours: float
    crew_size: int
    equipment_used: List[str]
    materials_used: List[str]
    notes: Optional[str]
    photos: List[str]
    cost: float
    status: str  # "scheduled", "in_progress", "completed", "cancelled"
```

## 🔧 Enhanced CRM Service

### Landscaping CRM Implementation
```python
# core/landscaping_crm_service.py
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class LandscapingCRMService:
    def __init__(self):
        self.clients_file = 'data/landscaping_clients.json'
        self.services_file = 'data/service_records.json'
        self.load_data()
    
    def load_data(self):
        """Load existing data from files"""
        try:
            with open(self.clients_file, 'r') as f:
                self.clients = json.load(f)
        except FileNotFoundError:
            self.clients = {}
        
        try:
            with open(self.services_file, 'r') as f:
                self.service_records = json.load(f)
        except FileNotFoundError:
            self.service_records = {}
    
    def save_data(self):
        """Save data to files"""
        with open(self.clients_file, 'w') as f:
            json.dump(self.clients, f, indent=2, default=str)
        
        with open(self.services_file, 'w') as f:
            json.dump(self.service_records, f, indent=2, default=str)
    
    def create_client_from_email(self, parsed_email: Dict) -> Dict:
        """Create new client from parsed email"""
        client_id = f"client_{len(self.clients) + 1}"
        
        # Extract basic information
        name = self._extract_name_from_email(parsed_email['from_email'])
        service_type = parsed_email.get('service_type', 'general')
        
        # Determine property size from email content
        property_size = self._estimate_property_size(parsed_email['body'])
        
        # Calculate lead score
        lead_score = self._calculate_lead_score(parsed_email)
        
        client = {
            'id': client_id,
            'name': name,
            'email': parsed_email['from_email'],
            'phone': None,
            'property_address': parsed_email.get('addresses', [''])[0],
            'property_size': property_size,
            'property_type': 'residential',  # Default, can be updated
            'primary_service': service_type,
            'service_frequency': 'one-time',  # Default, can be updated
            'service_history': [],
            'last_service_date': None,
            'next_service_date': None,
            'preferred_service_day': None,
            'preferred_service_time': None,
            'lead_source': 'email',
            'lead_score': lead_score,
            'status': 'new',
            'special_requests': parsed_email.get('special_requests', ''),
            'notes': f"Initial inquiry: {parsed_email['subject']}",
            'attachments': [],
            'estimated_value': self._estimate_service_value(service_type, property_size),
            'actual_revenue': 0.0,
            'payment_method': None,
            'communication_preference': 'email',
            'last_contact_date': datetime.now(),
            'follow_up_date': datetime.now() + timedelta(days=1),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        self.clients[client_id] = client
        self.save_data()
        
        return client
    
    def _extract_name_from_email(self, email: str) -> str:
        """Extract name from email address"""
        local_part = email.split('@')[0]
        # Remove common separators and capitalize
        name = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        return ' '.join(word.capitalize() for word in name.split())
    
    def _estimate_property_size(self, email_body: str) -> str:
        """Estimate property size from email content"""
        body_lower = email_body.lower()
        
        if any(word in body_lower for word in ['large', 'big', 'acre', 'commercial']):
            return 'large'
        elif any(word in body_lower for word in ['small', 'tiny', 'apartment']):
            return 'small'
        else:
            return 'medium'
    
    def _calculate_lead_score(self, parsed_email: Dict) -> int:
        """Calculate lead score based on email content"""
        score = 50  # Base score
        
        # Service type scoring
        service_scores = {
            'landscaping': 90,
            'tree_trimming': 80,
            'mowing': 70,
            'maintenance': 60,
            'general': 50
        }
        
        service_type = parsed_email.get('service_type', 'general')
        score += service_scores.get(service_type, 50) - 50
        
        # Urgency bonus
        if parsed_email.get('is_urgent', False):
            score += 20
        
        # Address provided bonus
        if parsed_email.get('addresses'):
            score += 15
        
        # Multiple services mentioned
        if len(parsed_email.get('detected_services', [])) > 1:
            score += 10
        
        return min(100, max(0, score))
    
    def _estimate_service_value(self, service_type: str, property_size: str) -> float:
        """Estimate service value based on type and property size"""
        base_prices = {
            'mowing': {'small': 35, 'medium': 50, 'large': 75},
            'landscaping': {'small': 200, 'medium': 500, 'large': 1000},
            'tree_trimming': {'small': 150, 'medium': 300, 'large': 500},
            'maintenance': {'small': 100, 'medium': 200, 'large': 350}
        }
        
        return base_prices.get(service_type, {}).get(property_size, 100)
    
    def get_clients_by_status(self, status: str) -> List[Dict]:
        """Get clients filtered by status"""
        return [client for client in self.clients.values() if client['status'] == status]
    
    def get_clients_by_service_type(self, service_type: str) -> List[Dict]:
        """Get clients filtered by service type"""
        return [client for client in self.clients.values() if client['primary_service'] == service_type]
    
    def get_upcoming_services(self, days_ahead: int = 7) -> List[Dict]:
        """Get clients with services scheduled in the next N days"""
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        upcoming = []
        for client in self.clients.values():
            if client['next_service_date']:
                next_date = datetime.fromisoformat(client['next_service_date']) if isinstance(client['next_service_date'], str) else client['next_service_date']
                if next_date <= cutoff_date:
                    upcoming.append(client)
        
        return sorted(upcoming, key=lambda x: x['next_service_date'])
    
    def update_client_status(self, client_id: str, new_status: str) -> bool:
        """Update client status"""
        if client_id in self.clients:
            self.clients[client_id]['status'] = new_status
            self.clients[client_id]['updated_at'] = datetime.now()
            self.save_data()
            return True
        return False
    
    def schedule_service(self, client_id: str, service_date: datetime, service_type: str) -> bool:
        """Schedule a service for a client"""
        if client_id in self.clients:
            self.clients[client_id]['next_service_date'] = service_date
            self.clients[client_id]['status'] = 'scheduled'
            self.clients[client_id]['updated_at'] = datetime.now()
            self.save_data()
            return True
        return False
    
    def add_service_record(self, client_id: str, service_data: Dict) -> str:
        """Add a completed service record"""
        service_id = f"service_{len(self.service_records) + 1}"
        
        service_record = {
            'id': service_id,
            'client_id': client_id,
            'service_type': service_data['service_type'],
            'service_date': service_data['service_date'],
            'duration_hours': service_data.get('duration_hours', 1.0),
            'crew_size': service_data.get('crew_size', 1),
            'equipment_used': service_data.get('equipment_used', []),
            'materials_used': service_data.get('materials_used', []),
            'notes': service_data.get('notes', ''),
            'photos': service_data.get('photos', []),
            'cost': service_data.get('cost', 0.0),
            'status': 'completed',
            'created_at': datetime.now()
        }
        
        self.service_records[service_id] = service_record
        
        # Update client's last service date and revenue
        if client_id in self.clients:
            self.clients[client_id]['last_service_date'] = service_data['service_date']
            self.clients[client_id]['actual_revenue'] += service_data.get('cost', 0.0)
            self.clients[client_id]['updated_at'] = datetime.now()
        
        self.save_data()
        return service_id
    
    def get_client_analytics(self) -> Dict:
        """Get analytics data for all clients"""
        total_clients = len(self.clients)
        active_clients = len([c for c in self.clients.values() if c['status'] == 'active'])
        new_clients = len([c for c in self.clients.values() if c['status'] == 'new'])
        
        # Service type distribution
        service_distribution = {}
        for client in self.clients.values():
            service = client['primary_service']
            service_distribution[service] = service_distribution.get(service, 0) + 1
        
        # Revenue analytics
        total_revenue = sum(client['actual_revenue'] for client in self.clients.values())
        avg_client_value = total_revenue / total_clients if total_clients > 0 else 0
        
        # Lead score distribution
        high_value_leads = len([c for c in self.clients.values() if c['lead_score'] >= 80])
        
        return {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'new_clients': new_clients,
            'service_distribution': service_distribution,
            'total_revenue': total_revenue,
            'avg_client_value': avg_client_value,
            'high_value_leads': high_value_leads,
            'conversion_rate': (active_clients / total_clients * 100) if total_clients > 0 else 0
        }
```

## 📊 Frontend CRM Dashboard

### Landscaping CRM Dashboard Component
```typescript
// frontend/src/components/LandscapingCRMDashboard.tsx
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Users, 
  Calendar, 
  DollarSign, 
  TrendingUp, 
  MapPin, 
  Clock,
  Star,
  Filter
} from 'lucide-react';

interface LandscapingClient {
  id: string;
  name: string;
  email: string;
  phone?: string;
  property_address: string;
  property_size: string;
  primary_service: string;
  service_frequency: string;
  status: string;
  lead_score: number;
  estimated_value: number;
  actual_revenue: number;
  next_service_date?: string;
  last_contact_date: string;
}

export const LandscapingCRMDashboard: React.FC = () => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterService, setFilterService] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('lead_score');

  const { data: clients, isLoading } = useQuery({
    queryKey: ['landscaping-clients'],
    queryFn: async () => {
      const response = await fetch('/api/landscaping/clients');
      return response.json();
    },
    staleTime: 30 * 1000
  });

  const { data: analytics } = useQuery({
    queryKey: ['landscaping-analytics'],
    queryFn: async () => {
      const response = await fetch('/api/landscaping/analytics');
      return response.json();
    },
    staleTime: 60 * 1000
  });

  const filteredClients = clients?.filter((client: LandscapingClient) => {
    const statusMatch = filterStatus === 'all' || client.status === filterStatus;
    const serviceMatch = filterService === 'all' || client.primary_service === filterService;
    return statusMatch && serviceMatch;
  }) || [];

  const sortedClients = filteredClients.sort((a: LandscapingClient, b: LandscapingClient) => {
    switch (sortBy) {
      case 'lead_score':
        return b.lead_score - a.lead_score;
      case 'estimated_value':
        return b.estimated_value - a.estimated_value;
      case 'name':
        return a.name.localeCompare(b.name);
      default:
        return 0;
    }
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="fikiri-card p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Analytics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="fikiri-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Clients</p>
              <p className="text-2xl font-bold text-gray-900">{analytics?.total_clients || 0}</p>
            </div>
            <Users className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="fikiri-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Active Clients</p>
              <p className="text-2xl font-bold text-green-600">{analytics?.active_clients || 0}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="fikiri-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Revenue</p>
              <p className="text-2xl font-bold text-gray-900">${analytics?.total_revenue?.toFixed(2) || '0.00'}</p>
            </div>
            <DollarSign className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="fikiri-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">High Value Leads</p>
              <p className="text-2xl font-bold text-purple-600">{analytics?.high_value_leads || 0}</p>
            </div>
            <Star className="h-8 w-8 text-purple-500" />
          </div>
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="fikiri-card p-4">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm"
            >
              <option value="all">All Status</option>
              <option value="new">New</option>
              <option value="qualified">Qualified</option>
              <option value="scheduled">Scheduled</option>
              <option value="active">Active</option>
            </select>
          </div>

          <select
            value={filterService}
            onChange={(e) => setFilterService(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1 text-sm"
          >
            <option value="all">All Services</option>
            <option value="mowing">Mowing</option>
            <option value="landscaping">Landscaping</option>
            <option value="tree_trimming">Tree Trimming</option>
            <option value="maintenance">Maintenance</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1 text-sm"
          >
            <option value="lead_score">Sort by Lead Score</option>
            <option value="estimated_value">Sort by Value</option>
            <option value="name">Sort by Name</option>
          </select>
        </div>
      </div>

      {/* Client List */}
      <div className="fikiri-card">
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-lg font-semibold">Client List</h3>
        </div>
        
        <div className="divide-y divide-gray-200">
          {sortedClients.map((client: LandscapingClient) => (
            <div key={client.id} className="p-6 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h4 className="text-lg font-medium text-gray-900">{client.name}</h4>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      client.status === 'new' ? 'bg-blue-100 text-blue-800' :
                      client.status === 'qualified' ? 'bg-yellow-100 text-yellow-800' :
                      client.status === 'scheduled' ? 'bg-purple-100 text-purple-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {client.status}
                    </span>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-400" />
                      <span className="text-sm font-medium">{client.lead_score}</span>
                    </div>
                  </div>
                  
                  <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                    <div className="flex items-center space-x-1">
                      <MapPin className="h-4 w-4" />
                      <span>{client.property_address}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <span className="font-medium">Service:</span>
                      <span>{client.primary_service}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <DollarSign className="h-4 w-4" />
                      <span>${client.estimated_value}</span>
                    </div>
                    {client.next_service_date && (
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{new Date(client.next_service_date).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <button className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
                    View Details
                  </button>
                  <button className="px-3 py-1 text-sm border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50">
                    Schedule
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

## 🚀 API Endpoints

### Flask Routes for Landscaping CRM
```python
# app.py - Add these routes
@app.route('/api/landscaping/clients', methods=['GET'])
def get_landscaping_clients():
    """Get all landscaping clients"""
    crm_service = LandscapingCRMService()
    clients = list(crm_service.clients.values())
    return jsonify(clients)

@app.route('/api/landscaping/clients/<client_id>', methods=['GET'])
def get_landscaping_client(client_id):
    """Get specific landscaping client"""
    crm_service = LandscapingCRMService()
    if client_id in crm_service.clients:
        return jsonify(crm_service.clients[client_id])
    return jsonify({'error': 'Client not found'}), 404

@app.route('/api/landscaping/clients/<client_id>/status', methods=['PUT'])
def update_client_status(client_id):
    """Update client status"""
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status required'}), 400
    
    crm_service = LandscapingCRMService()
    success = crm_service.update_client_status(client_id, new_status)
    
    if success:
        return jsonify({'message': 'Status updated successfully'})
    return jsonify({'error': 'Client not found'}), 404

@app.route('/api/landscaping/analytics', methods=['GET'])
def get_landscaping_analytics():
    """Get landscaping CRM analytics"""
    crm_service = LandscapingCRMService()
    analytics = crm_service.get_client_analytics()
    return jsonify(analytics)

@app.route('/api/landscaping/services/schedule', methods=['POST'])
def schedule_service():
    """Schedule a service for a client"""
    data = request.get_json()
    client_id = data.get('client_id')
    service_date = data.get('service_date')
    service_type = data.get('service_type')
    
    if not all([client_id, service_date, service_type]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    crm_service = LandscapingCRMService()
    success = crm_service.schedule_service(
        client_id, 
        datetime.fromisoformat(service_date), 
        service_type
    )
    
    if success:
        return jsonify({'message': 'Service scheduled successfully'})
    return jsonify({'error': 'Client not found'}), 404
```

This enhanced CRM system provides landscaping businesses with:

1. **Service-Specific Fields**: Property size, service frequency, equipment tracking
2. **Lead Scoring**: AI-powered lead scoring based on email content
3. **Scheduling Integration**: Service scheduling and calendar management
4. **Revenue Tracking**: Actual vs estimated revenue tracking
5. **Analytics Dashboard**: Business insights and performance metrics
6. **Mobile-Optimized UI**: Responsive design for field workers

The system automatically creates client records from Outlook emails and provides a comprehensive view of all landscaping business operations.
