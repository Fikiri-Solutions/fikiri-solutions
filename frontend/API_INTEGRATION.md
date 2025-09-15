# 🔌 API Integration Guide

## Current Status
- **Frontend**: React app running at http://localhost:3000 ✅
- **Backend**: Flask API running at https://fikirisolutions.onrender.com ✅
- **Integration**: Mock data currently used, ready for real API

## API Endpoints Available

### **Authentication**
```
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/status
```

### **Dashboard Data**
```
GET  /api/dashboard/metrics
GET  /api/dashboard/services
GET  /api/dashboard/activity
```

### **Services Management**
```
GET    /api/services
POST   /api/services
PUT    /api/services/:id
DELETE /api/services/:id
```

### **CRM Operations**
```
GET    /api/leads
POST   /api/leads
PUT    /api/leads/:id
DELETE /api/leads/:id
```

## Integration Steps

### 1. **Update API Configuration**
```typescript
// In config.ts, change:
mockData: false  // Switch to real API
```

### 2. **Create API Client**
```typescript
// services/apiClient.ts
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'https://fikirisolutions.onrender.com/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
})
```

### 3. **Replace Mock Data**
- **Login**: Use `/api/auth/login`
- **Dashboard**: Use `/api/dashboard/*`
- **Services**: Use `/api/services/*`

### 4. **Add Error Handling**
```typescript
// Handle API errors gracefully
try {
  const response = await apiClient.get('/dashboard/metrics')
  setMetrics(response.data)
} catch (error) {
  console.error('API Error:', error)
  // Fallback to mock data or show error
}
```

## Testing API Integration

### **Test Backend Endpoints**
```bash
# Test if backend is responding
curl https://fikirisolutions.onrender.com/api/health

# Test authentication
curl -X POST https://fikirisolutions.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

### **Frontend Integration**
1. **Switch to Real API**: Set `mockData: false` in config
2. **Test Login**: Use real authentication
3. **Test Dashboard**: Load real metrics
4. **Test Services**: Manage real service states

## Current Mock Data vs Real API

### **Mock Data** (Current)
- **Source**: `mockData.ts`
- **Purpose**: Development and testing
- **Status**: ✅ Working perfectly

### **Real API** (Target)
- **Source**: https://fikirisolutions.onrender.com/api/*
- **Purpose**: Production data
- **Status**: 🔄 Ready for integration

## Next Steps

1. **Test Backend**: Verify all endpoints work
2. **Create API Client**: Replace mock calls
3. **Update Components**: Use real data
4. **Error Handling**: Graceful fallbacks
5. **Deploy**: Production-ready integration

---
*Ready for API integration when you're ready to connect to the backend!*
