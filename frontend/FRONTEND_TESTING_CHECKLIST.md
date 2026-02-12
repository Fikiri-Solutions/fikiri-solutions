# 🧪 Frontend Testing Checklist - Localhost Testing

## 🚀 Quick Start

1. **Start Frontend Dev Server:**
   ```bash
   cd frontend
   npm run dev
   ```
   - Server runs on: `http://localhost:5174`
   - Hot reload enabled

2. **Start Backend (if testing with real API):**
   ```bash
   python app.py
   ```
   - Backend runs on: `http://localhost:5000`
   - Or use production: `https://fikirisolutions.onrender.com`

---

## ✅ Testing Checklist

### **1. Landing Page** (`/`)
- [ ] Page loads without errors
- [ ] Hero section displays correctly
- [ ] Navigation menu works
- [ ] "Get Started" button links to signup
- [ ] "Sign In" button links to login
- [ ] Responsive on mobile (check at 375px width)
- [ ] No console errors

### **2. Authentication Pages**

#### **Login Page** (`/login`)
- [ ] Form renders correctly
- [ ] Email input accepts valid email
- [ ] Password input toggles visibility (eye icon)
- [ ] "Remember me" checkbox works
- [ ] "Forgot password?" link works
- [ ] Social login buttons visible (Gmail, Microsoft, GitHub)
- [ ] Form validation shows errors for:
  - [ ] Empty email
  - [ ] Invalid email format
  - [ ] Empty password
  - [ ] Password too short (< 6 characters)
- [ ] Submit button shows loading state
- [ ] Error messages display correctly
- [ ] Success redirects to dashboard/onboarding

#### **Signup Page** (`/signup`)
- [ ] Form renders correctly
- [ ] All required fields present
- [ ] Password confirmation matches
- [ ] Terms of service checkbox works
- [ ] Form validation works
- [ ] Submit creates account
- [ ] Redirects to onboarding after signup

### **3. Onboarding Flow** (`/onboarding`)
- [ ] Step 1: Welcome screen displays
- [ ] Progress indicator shows current step
- [ ] "Next" button advances to next step
- [ ] "Previous" button goes back
- [ ] Step 2: Business information form
  - [ ] Company name field
  - [ ] Industry dropdown
  - [ ] Company size selection
- [ ] Step 3: Service selection
  - [ ] Checkboxes for each service
  - [ ] Services can be toggled
  - [ ] Service descriptions visible
- [ ] Step 4: Gmail connection
  - [ ] "Connect Gmail" button works
  - [ ] OAuth flow initiates
- [ ] Step 5: Confirmation
  - [ ] Summary displays
  - [ ] "Complete Setup" button works
- [ ] Completion redirects to dashboard

### **4. Dashboard** (`/home` or `/dashboard`)
- [ ] Requires authentication (redirects if not logged in)
- [ ] Metrics cards display:
  - [ ] Total leads
  - [ ] Active campaigns
  - [ ] Response rate
  - [ ] Email volume
- [ ] Service status indicators show:
  - [ ] Green for active services
  - [ ] Red for inactive services
- [ ] Activity feed displays recent actions
- [ ] Charts render correctly (if applicable)
- [ ] Loading states show during data fetch
- [ ] Empty states display when no data
- [ ] Responsive layout on mobile

### **5. Services Page** (`/services`)
- [ ] List of all services displays
- [ ] Each service shows:
  - [ ] Name and description
  - [ ] Enable/disable toggle
  - [ ] Status indicator
  - [ ] Settings panel (when enabled)
- [ ] Toggle switches work
- [ ] "Test" buttons work for each service
- [ ] Test results display
- [ ] "Save" button persists changes
- [ ] Loading states during API calls
- [ ] Error handling for failed tests

### **6. CRM Page** (`/crm`)
- [ ] Leads list displays
- [ ] Search functionality works
- [ ] Filter by stage works
- [ ] "Add Lead" button opens form
- [ ] Lead form validation works
- [ ] Lead cards display correctly
- [ ] Edit/Delete actions work
- [ ] Responsive table/cards on mobile

### **7. UI Components**

#### **Navigation**
- [ ] Sidebar opens/closes on mobile
- [ ] Active route highlighted
- [ ] All links navigate correctly
- [ ] User menu dropdown works
- [ ] Logout button works

#### **Toast Notifications**
- [ ] Success toasts appear
- [ ] Error toasts appear
- [ ] Toasts auto-dismiss
- [ ] Toasts can be manually dismissed
- [ ] Multiple toasts stack correctly

#### **Loading States**
- [ ] Spinners show during API calls
- [ ] Skeleton loaders display
- [ ] Buttons show loading state

#### **Error Handling**
- [ ] Error boundary catches errors
- [ ] Error pages display correctly
- [ ] 404 page works
- [ ] Network error handling
- [ ] API error messages display

### **8. Responsive Design**

#### **Mobile (375px width)**
- [ ] All pages are readable
- [ ] No horizontal scrolling
- [ ] Touch targets are at least 44px
- [ ] Navigation is accessible
- [ ] Forms are usable
- [ ] Buttons are easily tappable

#### **Tablet (768px width)**
- [ ] Layout adapts correctly
- [ ] Sidebar behavior appropriate
- [ ] Cards grid properly

#### **Desktop (1024px+)**
- [ ] Full layout displays
- [ ] Sidebar always visible
- [ ] Optimal use of space

### **9. Performance**
- [ ] Page load time < 3 seconds
- [ ] No layout shift (CLS)
- [ ] Images load efficiently
- [ ] No console errors
- [ ] No memory leaks (check DevTools)

### **10. Accessibility**
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Screen reader friendly (test with VoiceOver/NVDA)
- [ ] Color contrast meets WCAG AA
- [ ] Alt text on images
- [ ] Form labels associated correctly

---

## 🐛 Common Issues to Check

### **Console Errors**
- [ ] No React errors
- [ ] No API errors (unless testing error handling)
- [ ] No CORS errors
- [ ] No missing dependency warnings

### **Network Tab**
- [ ] API calls succeed (200 status)
- [ ] Failed calls show proper error handling
- [ ] No unnecessary duplicate requests
- [ ] Caching works correctly

### **Application Tab (DevTools)**
- [ ] LocalStorage stores auth tokens
- [ ] Session data persists
- [ ] No memory leaks

---

## 🎯 Quick Test Scenarios

### **Scenario 1: New User Signup Flow**
1. Go to landing page
2. Click "Get Started"
3. Fill signup form
4. Complete onboarding
5. Verify dashboard loads

### **Scenario 2: Existing User Login**
1. Go to login page
2. Enter credentials
3. Verify dashboard loads
4. Check user data displays

### **Scenario 3: Service Configuration**
1. Navigate to Services page
2. Enable a service
3. Configure settings
4. Test the service
5. Save changes
6. Verify changes persist

### **Scenario 4: Mobile Experience**
1. Open DevTools
2. Toggle device toolbar
3. Select iPhone/Android
4. Test all major pages
5. Verify usability

---

## 📝 Testing Notes

**Date:** _______________  
**Tester:** _______________  
**Browser:** _______________  
**OS:** _______________  

**Issues Found:**
1. 
2. 
3. 

**Notes:**
- 

---

## 🚀 Next Steps After Testing

1. **Fix Critical Issues** - Blocking bugs
2. **Document Findings** - Create bug reports
3. **Update Tests** - Add test cases for new issues
4. **Performance Optimization** - Address slow areas
5. **Accessibility Improvements** - Fix a11y issues

---

**Happy Testing! 🎉**





