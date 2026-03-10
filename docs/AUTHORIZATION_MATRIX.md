# Authorization Matrix

**Status**: Authorization model defined  
**Last Updated**: Feb 2026

---

## Overview

Fikiri Solutions uses JWT + sessions for authentication. This document defines the authorization (permissions) model for multi-user organizations.

**Current State:**
- ✅ Authentication: JWT + sessions working
- ✅ Basic user isolation: Users see only their own data
- ⚠️ **Gap**: No org-level access control or role-based permissions

---

## Permission Model

### Roles

| Role | Description | Permissions |
|------|------------|-------------|
| **owner** | Account owner | Full access to all resources |
| **admin** | Organization admin | Manage users, settings, all data |
| **member** | Team member | Read/write own data, read org data |
| **viewer** | Read-only access | Read-only access to org data |

### Permissions

| Permission | Description | Owner | Admin | Member | Viewer |
|------------|-------------|-------|-------|--------|--------|
| `crm:read` | View CRM data | ✅ | ✅ | ✅ | ✅ |
| `crm:write` | Create/update CRM data | ✅ | ✅ | ✅ | ❌ |
| `crm:delete` | Delete CRM data | ✅ | ✅ | ❌ | ❌ |
| `kb:read` | View knowledge base | ✅ | ✅ | ✅ | ✅ |
| `kb:write` | Create/update KB docs | ✅ | ✅ | ✅ | ❌ |
| `kb:delete` | Delete KB docs | ✅ | ✅ | ❌ | ❌ |
| `automation:read` | View automations | ✅ | ✅ | ✅ | ✅ |
| `automation:write` | Create/update automations | ✅ | ✅ | ✅ | ❌ |
| `automation:execute` | Execute automations | ✅ | ✅ | ❌ | ❌ |
| `billing:read` | View billing info | ✅ | ✅ | ❌ | ❌ |
| `billing:write` | Update billing | ✅ | ✅ | ❌ | ❌ |
| `users:read` | View users | ✅ | ✅ | ✅ | ✅ |
| `users:write` | Manage users | ✅ | ✅ | ❌ | ❌ |
| `settings:read` | View settings | ✅ | ✅ | ✅ | ✅ |
| `settings:write` | Update settings | ✅ | ✅ | ❌ | ❌ |

---

## Implementation Plan

### Phase 1: User Model Extension

**Add to `users` table:**
```sql
ALTER TABLE users ADD COLUMN organization_id INTEGER;
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'member';
ALTER TABLE users ADD COLUMN permissions_json TEXT;  -- JSON array of permissions
```

**Or create `user_roles` table:**
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    organization_id INTEGER,
    role TEXT NOT NULL,
    permissions TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Phase 2: Authorization Decorator

**Create `core/authorization.py`:**

```python
from functools import wraps
from flask import g, jsonify

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = get_user_permissions(g.user_id)
            if permission not in user_permissions:
                return jsonify({
                    'success': False,
                    'error': f'Permission required: {permission}',
                    'error_code': 'INSUFFICIENT_PERMISSIONS'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_permissions(user_id: int) -> List[str]:
    """Get user's permissions based on role"""
    # Check user role
    # Return permissions for that role
    # Owner gets all permissions
    pass
```

### Phase 3: Apply to Endpoints

**Update CRM endpoints:**
```python
@business_bp.route('/crm/leads', methods=['GET'])
@require_permission('crm:read')
def get_leads():
    ...

@business_bp.route('/crm/leads', methods=['POST'])
@require_permission('crm:write')
def create_lead():
    ...

@business_bp.route('/crm/leads/<id>', methods=['DELETE'])
@require_permission('crm:delete')
def delete_lead():
    ...
```

**Update KB endpoints:**
```python
@chatbot_bp.route('/knowledge/documents', methods=['POST'])
@require_permission('kb:write')
def create_knowledge_document():
    ...
```

---

## Organization-Level Access Control

### Data Isolation

**Current**: User-level isolation (users see only their data)  
**Target**: Organization-level isolation (users see org data based on permissions)

### Implementation

1. **Add `organization_id` to data models:**
   - CRM leads/contacts
   - KB documents
   - Automations
   - Workflows

2. **Filter queries by organization:**
   ```python
   # Get user's organization
   org_id = get_user_organization(g.user_id)
   
   # Filter queries
   leads = db.execute_query(
       "SELECT * FROM leads WHERE organization_id = ?",
       (org_id,)
   )
   ```

3. **Enforce on create/update:**
   ```python
   def create_lead(data):
       org_id = get_user_organization(g.user_id)
       data['organization_id'] = org_id
       # Create lead
   ```

---

## Permission Checking Functions

### Helper Functions

```python
def has_permission(user_id: int, permission: str) -> bool:
    """Check if user has specific permission"""
    permissions = get_user_permissions(user_id)
    return permission in permissions

def require_org_member(user_id: int, org_id: int) -> bool:
    """Check if user belongs to organization"""
    user_org = get_user_organization(user_id)
    return user_org == org_id

def get_user_role(user_id: int) -> str:
    """Get user's role"""
    # Query database
    return role

def get_user_permissions(user_id: int) -> List[str]:
    """Get user's permissions based on role"""
    role = get_user_role(user_id)
    return ROLE_PERMISSIONS.get(role, [])
```

---

## Role Permissions Map

```python
ROLE_PERMISSIONS = {
    'owner': [
        'crm:read', 'crm:write', 'crm:delete',
        'kb:read', 'kb:write', 'kb:delete',
        'automation:read', 'automation:write', 'automation:execute',
        'billing:read', 'billing:write',
        'users:read', 'users:write',
        'settings:read', 'settings:write'
    ],
    'admin': [
        'crm:read', 'crm:write', 'crm:delete',
        'kb:read', 'kb:write', 'kb:delete',
        'automation:read', 'automation:write', 'automation:execute',
        'billing:read', 'billing:write',
        'users:read', 'users:write',
        'settings:read', 'settings:write'
    ],
    'member': [
        'crm:read', 'crm:write',
        'kb:read', 'kb:write',
        'automation:read', 'automation:write',
        'users:read',
        'settings:read'
    ],
    'viewer': [
        'crm:read',
        'kb:read',
        'automation:read',
        'users:read',
        'settings:read'
    ]
}
```

---

## Endpoint Authorization Matrix

### CRM Endpoints

| Endpoint | Method | Required Permission |
|----------|--------|---------------------|
| `/api/crm/leads` | GET | `crm:read` |
| `/api/crm/leads` | POST | `crm:write` |
| `/api/crm/leads/<id>` | PUT | `crm:write` |
| `/api/crm/leads/<id>` | DELETE | `crm:delete` |
| `/api/crm/pipeline` | GET | `crm:read` |

### Knowledge Base Endpoints

| Endpoint | Method | Required Permission |
|----------|--------|---------------------|
| `/api/chatbot/knowledge/documents` | GET | `kb:read` |
| `/api/chatbot/knowledge/documents` | POST | `kb:write` |
| `/api/chatbot/knowledge/document/<id>` | PUT | `kb:write` |
| `/api/chatbot/knowledge/document/<id>` | DELETE | `kb:delete` |

### Automation Endpoints

| Endpoint | Method | Required Permission |
|----------|--------|---------------------|
| `/api/automation/rules` | GET | `automation:read` |
| `/api/automation/rules` | POST | `automation:write` |
| `/api/automation/execute` | POST | `automation:execute` |

### Billing Endpoints

| Endpoint | Method | Required Permission |
|----------|--------|---------------------|
| `/api/billing/subscription` | GET | `billing:read` |
| `/api/billing/subscription` | POST | `billing:write` |

---

## Implementation Checklist

- [ ] Add `organization_id` and `role` to user model
- [ ] Create `user_roles` table (if using separate table)
- [ ] Implement `require_permission()` decorator
- [ ] Implement `get_user_permissions()` function
- [ ] Add `organization_id` to CRM leads/contacts
- [ ] Add `organization_id` to KB documents
- [ ] Filter queries by `organization_id`
- [ ] Apply permission checks to all endpoints
- [ ] Add role management endpoints
- [ ] Add permission checking to frontend
- [ ] Document in API docs

---

## Migration Path

### For Existing Users

1. **Assign default organization:**
   - Single-user accounts: `organization_id = user_id`
   - Multi-user accounts: Assign to existing org or create new

2. **Assign default role:**
   - First user: `owner`
   - Subsequent users: `member`

3. **Migrate existing data:**
   - Set `organization_id` on all existing records
   - Use user's organization_id

---

## Testing

### Unit Tests

```python
def test_require_permission_decorator():
    """Test permission decorator"""
    # Test with valid permission
    # Test with invalid permission
    # Test with missing user
    pass

def test_org_isolation():
    """Test organization-level data isolation"""
    # Create two orgs
    # Verify users can't see other org's data
    pass
```

### Integration Tests

```python
def test_crm_endpoint_permissions():
    """Test CRM endpoints respect permissions"""
    # Test each endpoint with different roles
    # Verify 403 for insufficient permissions
    pass
```

---

## Next Steps

1. [ ] Design organization model (single vs multi-org)
2. [ ] Implement user roles table
3. [ ] Implement permission checking
4. [ ] Apply to endpoints
5. [ ] Add role management UI
6. [ ] Test thoroughly

---

*Last updated: Feb 2026*
