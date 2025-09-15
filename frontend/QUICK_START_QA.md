# 🚀 Quick Start: Frontend QA Testing

## **Step 1: Start Development Server**
```bash
cd frontend
./dev.sh
```

## **Step 2: Open Browser**
- **URL**: http://localhost:3000
- **DevTools**: Press F12 → Device toolbar
- **Mobile**: Select iPhone SE (375px width)

## **Step 3: Test Login**
- **Email**: `test@example.com`
- **Password**: `password`
- **Expected**: Redirects to dashboard

## **Step 4: Run QA Checklist**

### **✅ Visual Checks (2 minutes)**
- [ ] **Spacing**: Cards have consistent padding
- [ ] **Colors**: Blue buttons, green success states
- [ ] **Hover**: Buttons change color on hover
- [ ] **Focus**: Inputs show blue border on focus

### **✅ Mobile Checks (2 minutes)**
- [ ] **Sidebar**: Collapses to hamburger menu
- [ ] **Touch**: Buttons are ≥44px tall
- [ ] **Text**: No horizontal scrolling
- [ ] **Layout**: Cards stack vertically

### **✅ Interaction Checks (3 minutes)**
- [ ] **Login**: Shows error for invalid credentials
- [ ] **Loading**: Spinners during async operations
- [ ] **Navigation**: All links work correctly
- [ ] **Forms**: Validation shows clear errors

### **✅ Mock Data Checks (2 minutes)**
- [ ] **Metrics**: Shows "156", "23", "89", "2.3h"
- [ ] **Services**: Shows "active" status
- [ ] **Activity**: Shows recent items with timestamps
- [ ] **No undefined**: All data displays properly

### **✅ Feature Flags (1 minute)**
- [ ] **Debug mode**: Shows "Mock Data" label when enabled
- [ ] **Onboarding**: Route works when enabled
- [ ] **CRM page**: Hidden when disabled

## **Step 5: Report Issues**
- **Critical**: Blocks user from completing tasks
- **High**: Significantly impacts user experience
- **Medium**: Minor visual or interaction issues
- **Low**: Nice-to-have improvements

## **🎯 Success Criteria**
- ✅ **No console errors**
- ✅ **Mobile layout works**
- ✅ **All buttons have hover states**
- ✅ **Mock data displays correctly**
- ✅ **No typos in user-facing text**

---

**Total testing time: ~10 minutes**
**Focus on critical issues first, polish later!** 🎯

