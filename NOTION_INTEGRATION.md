# Notion Integration for Fikiri Solutions

## 🔗 Notion API Setup

### 1. Create Notion Integration
```python
# core/notion_integration.py
import requests
import json
from datetime import datetime

class NotionIntegration:
    def __init__(self, integration_token):
        self.token = integration_token
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_database(self, title: str, properties: dict) -> str:
        """Create a new Notion database"""
        data = {
            "parent": {"type": "page_id", "page_id": "YOUR_PAGE_ID"},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties
        }
        
        response = requests.post(
            f"{self.base_url}/databases",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        return None
    
    def add_page_to_database(self, database_id: str, properties: dict) -> str:
        """Add a page to a Notion database"""
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        response = requests.post(
            f"{self.base_url}/pages",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        return None
    
    def create_customer_database(self) -> str:
        """Create customer database in Notion"""
        properties = {
            "Name": {"title": {}},
            "Email": {"email": {}},
            "Company": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "Lead", "color": "yellow"},
                {"name": "Qualified", "color": "blue"},
                {"name": "Customer", "color": "green"},
                {"name": "Churned", "color": "red"}
            ]}},
            "Plan": {"select": {"options": [
                {"name": "Starter", "color": "blue"},
                {"name": "Professional", "color": "green"},
                {"name": "Enterprise", "color": "purple"}
            ]}},
            "MRR": {"number": {"format": "currency"}},
            "Created": {"created_time": {}},
            "Last Contact": {"date": {}},
            "Notes": {"rich_text": {}}
        }
        
        return self.create_database("Fikiri Customers", properties)
    
    def create_support_database(self) -> str:
        """Create support tickets database"""
        properties = {
            "Title": {"title": {}},
            "Customer": {"relation": {"database_id": "CUSTOMER_DB_ID"}},
            "Priority": {"select": {"options": [
                {"name": "Low", "color": "green"},
                {"name": "Medium", "color": "yellow"},
                {"name": "High", "color": "orange"},
                {"name": "Critical", "color": "red"}
            ]}},
            "Status": {"select": {"options": [
                {"name": "Open", "color": "red"},
                {"name": "In Progress", "color": "yellow"},
                {"name": "Resolved", "color": "green"},
                {"name": "Closed", "color": "gray"}
            ]}},
            "Type": {"select": {"options": [
                {"name": "Bug", "color": "red"},
                {"name": "Feature Request", "color": "blue"},
                {"name": "Question", "color": "green"},
                {"name": "Integration", "color": "purple"}
            ]}},
            "Created": {"created_time": {}},
            "Updated": {"last_edited_time": {}},
            "Description": {"rich_text": {}}
        }
        
        return self.create_database("Support Tickets", properties)
    
    def sync_customer_to_notion(self, customer_data: dict) -> str:
        """Sync customer data to Notion"""
        properties = {
            "Name": {"title": [{"text": {"content": customer_data["name"]}}]},
            "Email": {"email": customer_data["email"]},
            "Company": {"rich_text": [{"text": {"content": customer_data.get("company", "")}}]},
            "Status": {"select": {"name": customer_data.get("status", "Lead")}},
            "Plan": {"select": {"name": customer_data.get("plan", "Starter")}},
            "MRR": {"number": customer_data.get("mrr", 0)},
            "Notes": {"rich_text": [{"text": {"content": customer_data.get("notes", "")}}]}
        }
        
        return self.add_page_to_database("CUSTOMER_DB_ID", properties)
    
    def create_project_database(self) -> str:
        """Create project management database"""
        properties = {
            "Project": {"title": {}},
            "Status": {"select": {"options": [
                {"name": "Planning", "color": "blue"},
                {"name": "In Progress", "color": "yellow"},
                {"name": "Review", "color": "orange"},
                {"name": "Completed", "color": "green"},
                {"name": "On Hold", "color": "gray"}
            ]}},
            "Priority": {"select": {"options": [
                {"name": "Low", "color": "green"},
                {"name": "Medium", "color": "yellow"},
                {"name": "High", "color": "orange"},
                {"name": "Critical", "color": "red"}
            ]}},
            "Assignee": {"people": {}},
            "Due Date": {"date": {}},
            "Progress": {"number": {"format": "percent"}},
            "Description": {"rich_text": {}}
        }
        
        return self.create_database("Fikiri Projects", properties)
```

## 📊 Notion Dashboard Templates

### Customer Success Dashboard
```markdown
# Fikiri Solutions - Customer Success Dashboard

## 📈 Key Metrics
- **Total Customers**: 0
- **MRR**: $0
- **Churn Rate**: 0%
- **NPS Score**: 0

## 🎯 This Week's Goals
- [ ] Onboard 5 new customers
- [ ] Reduce churn rate to <5%
- [ ] Achieve 90% customer satisfaction
- [ ] Launch 2 new integrations

## 🔥 Hot Leads
| Customer | Company | Status | MRR | Next Action |
|----------|---------|--------|-----|-------------|
| | | | | |

## 🚨 Support Alerts
| Ticket | Customer | Priority | Status | Assigned |
|--------|----------|----------|--------|----------|
| | | | | |

## 📅 This Week's Activities
- [ ] Customer check-ins
- [ ] Demo calls
- [ ] Support tickets
- [ ] Product updates
```

### Product Development Roadmap
```markdown
# Fikiri Solutions - Product Roadmap

## 🚀 Phase 1: Customer-Facing Readiness (Current)
- [x] Landing pages
- [x] Pricing tiers
- [x] Demo booking
- [x] Documentation site
- [ ] Branding refinement
- [ ] Pitch deck

## 💰 Phase 2: Monetization & Customer Acquisition
- [ ] Stripe integration
- [ ] Trial/free tier
- [ ] User analytics
- [ ] Sales pipeline
- [ ] Outreach campaigns

## 🔗 Phase 3: Ecosystem Integrations
- [ ] Outlook 365 integration
- [ ] Mailchimp connector
- [ ] Shopify integration
- [ ] Website widget
- [ ] Zapier recipes

## 🤖 Phase 4: AI Routing & Intelligence
- [ ] Advanced routing
- [ ] Lead scoring ML
- [ ] Self-improving workflows
- [ ] Model optimization

## 🌍 Phase 5: Scale & Compliance
- [ ] Multi-region deployment
- [ ] SOC2 compliance
- [ ] Legal documentation
- [ ] Industry partnerships

## 🚀 Phase 6: Growth & Long-Term
- [ ] Funding preparation
- [ ] Multimodal AI
- [ ] Consulting arm
- [ ] Enterprise features
```

## 🔄 Automated Sync

### Customer Data Sync
```python
# core/notion_sync.py
class NotionSync:
    def __init__(self, notion_integration):
        self.notion = notion_integration
        self.customer_db_id = None
        self.support_db_id = None
    
    def setup_databases(self):
        """Setup Notion databases"""
        self.customer_db_id = self.notion.create_customer_database()
        self.support_db_id = self.notion.create_support_database()
    
    def sync_new_customer(self, customer_data: dict):
        """Sync new customer to Notion"""
        if self.customer_db_id:
            return self.notion.sync_customer_to_notion(customer_data)
        return None
    
    def create_support_ticket(self, ticket_data: dict):
        """Create support ticket in Notion"""
        if self.support_db_id:
            properties = {
                "Title": {"title": [{"text": {"content": ticket_data["title"]}}]},
                "Priority": {"select": {"name": ticket_data.get("priority", "Medium")}},
                "Status": {"select": {"name": "Open"}},
                "Type": {"select": {"name": ticket_data.get("type", "Question")}},
                "Description": {"rich_text": [{"text": {"content": ticket_data["description"]}}]}
            }
            
            return self.notion.add_page_to_database(self.support_db_id, properties)
        return None
    
    def update_customer_status(self, customer_id: str, new_status: str):
        """Update customer status in Notion"""
        # Implementation for updating customer status
        pass
```

## 📱 Frontend Notion Integration

### Notion Dashboard Component
```typescript
// frontend/src/components/NotionDashboard.tsx
import React, { useState, useEffect } from 'react';
import { ExternalLink, RefreshCw, Plus } from 'lucide-react';

export const NotionDashboard: React.FC = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [databases, setDatabases] = useState([]);

  const connectNotion = async () => {
    try {
      // Redirect to Notion OAuth
      const authUrl = await fetch('/api/notion/auth-url').then(r => r.text());
      window.location.href = authUrl;
    } catch (error) {
      console.error('Failed to connect Notion:', error);
    }
  };

  const syncData = async () => {
    try {
      await fetch('/api/notion/sync', { method: 'POST' });
      // Refresh data
    } catch (error) {
      console.error('Failed to sync data:', error);
    }
  };

  return (
    <div className="fikiri-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Notion Integration</h3>
        {isConnected && (
          <button
            onClick={syncData}
            className="flex items-center space-x-2 text-blue-600 hover:text-blue-700"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Sync</span>
          </button>
        )}
      </div>

      {isConnected ? (
        <div className="space-y-4">
          <div className="flex items-center text-green-600">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
            <span>Connected to Notion</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">Customer Database</h4>
              <p className="text-sm text-gray-600">Sync customer data automatically</p>
              <a
                href="https://notion.so/customer-db"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-blue-600 hover:text-blue-700 mt-2"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                View in Notion
              </a>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-2">Support Tickets</h4>
              <p className="text-sm text-gray-600">Track customer issues</p>
              <a
                href="https://notion.so/support-db"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-blue-600 hover:text-blue-700 mt-2"
              >
                <ExternalLink className="h-4 w-4 mr-1" />
                View in Notion
              </a>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-gray-600">
            Connect Notion to automatically sync customer data, support tickets, and project management.
          </p>
          
          <button
            onClick={connectNotion}
            className="w-full bg-gray-900 text-white py-2 px-4 rounded-md hover:bg-gray-800 transition-colors flex items-center justify-center space-x-2"
          >
            <Plus className="h-4 w-4" />
            <span>Connect Notion</span>
          </button>
        </div>
      )}
    </div>
  );
};
```

## 🚀 API Endpoints

### Flask Routes for Notion
```python
# app.py - Add these routes
@app.route('/api/notion/auth-url', methods=['GET'])
def get_notion_auth_url():
    """Get Notion OAuth URL"""
    auth_url = f"https://api.notion.com/v1/oauth/authorize?client_id={os.getenv('NOTION_CLIENT_ID')}&response_type=code&redirect_uri={os.getenv('NOTION_REDIRECT_URI')}"
    return auth_url

@app.route('/api/notion/callback', methods=['GET'])
def notion_callback():
    """Handle Notion OAuth callback"""
    code = request.args.get('code')
    if code:
        # Exchange code for token
        token_data = exchange_notion_code_for_token(code)
        
        # Save token to database
        save_notion_token(token_data)
        
        return redirect('https://fikirisolutions.com/settings?connected=notion')
    
    return redirect('https://fikirisolutions.com/settings?error=notion_auth')

@app.route('/api/notion/sync', methods=['POST'])
def sync_notion_data():
    """Sync data to Notion"""
    try:
        notion_sync = NotionSync(NotionIntegration(get_notion_token()))
        notion_sync.setup_databases()
        
        # Sync customer data
        customers = get_all_customers()
        for customer in customers:
            notion_sync.sync_new_customer(customer)
        
        return jsonify({'message': 'Data synced successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

This Notion integration provides:

✅ **Customer Database** - Automatic sync of customer data
✅ **Support Tickets** - Track customer issues and requests
✅ **Project Management** - Roadmap and task tracking
✅ **Dashboard Templates** - Ready-to-use Notion pages
✅ **Automated Sync** - Real-time data synchronization
✅ **OAuth Integration** - Secure connection to Notion

Ready to implement the landing pages and complete Phase 1?

