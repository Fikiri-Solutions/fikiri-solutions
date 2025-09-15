# 🎯 Fikiri Solutions Frontend QA Checklist

## 🚀 **Quick Start**
```bash
cd frontend
./dev.sh
# Open http://localhost:3000 in Chrome + mobile simulator
```

## 1. 🖼️ **Visual & Layout Checks**

### **Spacing Consistency**
- [ ] **Cards**: All cards use `p-6` (24px) padding
- [ ] **Sections**: Consistent `space-y-6` (24px) between sections
- [ ] **Buttons**: Consistent `py-2 px-4` (8px/16px) padding
- [ ] **Inputs**: Consistent `px-3 py-2` (12px/8px) padding
- [ ] **Margins**: Use Tailwind scale (4px, 8px, 16px, 24px, 32px)

### **Alignment**
- [ ] **Grid alignment**: All elements align to invisible grid
- [ ] **Button alignment**: Buttons in forms are properly aligned
- [ ] **Text alignment**: Headers and body text are consistent
- [ ] **Icon alignment**: Icons are centered with text

### **Typography**
- [ ] **Font family**: Inter font loads correctly (no fallbacks)
- [ ] **Font weights**: Consistent use of 400, 500, 600, 700
- [ ] **Font sizes**: Proper scale (text-sm, text-base, text-lg, text-xl)
- [ ] **Line heights**: Proper line-height for readability

### **Color Scheme**
- [ ] **Primary blue**: `#2563eb` (blue-600) for buttons and links
- [ ] **Success green**: `#059669` (green-600) for success states
- [ ] **Neutral grays**: `#6b7280` (gray-500) for text, `#f9fafb` (gray-50) for backgrounds
- [ ] **No random colors**: All colors come from Tailwind palette

### **Icons & Images**
- [ ] **Icon sizing**: Consistent `h-5 w-5` or `h-6 w-6` sizing
- [ ] **Icon centering**: Properly centered with text
- [ ] **No blurry icons**: Lucide React icons are crisp
- [ ] **Proper spacing**: Icons have consistent margins

## 2. 📱 **Responsive Design Checks**

### **Mobile (≤ 375px)**
- [ ] **Sidebar**: Collapses to hamburger menu
- [ ] **Text overflow**: No horizontal scrolling
- [ ] **Touch targets**: Buttons are ≥44px tall
- [ ] **Form inputs**: Full width, proper spacing
- [ ] **Cards**: Stack vertically, no side-by-side

### **Tablet (768px)**
- [ ] **Layout adaptation**: Grid adjusts to 2 columns
- [ ] **Spacing**: No weird gaps or overlaps
- [ ] **Navigation**: Sidebar works properly
- [ ] **Forms**: Proper spacing and alignment

### **Desktop (≥1024px)**
- [ ] **Dashboard**: Fills space properly, no huge gaps
- [ ] **Sidebar**: Fixed width, content adjusts
- [ ] **Grid**: Proper 4-column layout for metrics
- [ ] **Max width**: Content doesn't stretch too wide

### **Orientation Testing**
- [ ] **Portrait → Landscape**: Layout adapts smoothly
- [ ] **Landscape → Portrait**: No layout breaks
- [ ] **Rotation**: No content gets cut off

## 3. 🖱️ **Interaction Checks**

### **Hover States**
- [ ] **Buttons**: Change color on hover (`hover:bg-blue-700`)
- [ ] **Links**: Underline or color change on hover
- [ ] **Cards**: Subtle shadow or color change
- [ ] **Icons**: Color change on hover

### **Focus States**
- [ ] **Inputs**: Blue border on focus (`focus:ring-blue-500`)
- [ ] **Buttons**: Visible focus outline
- [ ] **Links**: Keyboard navigation works
- [ ] **Accessibility**: Screen reader friendly

### **Click Feedback**
- [ ] **Loading states**: Spinners during async operations
- [ ] **Disabled states**: Grayed out when disabled
- [ ] **Success feedback**: Visual confirmation of actions
- [ ] **Error feedback**: Clear error messages

### **Navigation**
- [ ] **Routing**: All links navigate correctly
- [ ] **Back button**: Browser back button works
- [ ] **Breadcrumbs**: Show current location
- [ ] **Sidebar**: All menu items work

### **Error Handling**
- [ ] **Form validation**: Clear error messages
- [ ] **API errors**: User-friendly error messages
- [ ] **Network errors**: Graceful fallbacks
- [ ] **No console errors**: Clean browser console

## 4. ⚡ **Mock Data Flow**

### **Dashboard Metrics**
- [ ] **Total Emails**: Shows "156" (not undefined)
- [ ] **Active Leads**: Shows "23" (not undefined)
- [ ] **AI Responses**: Shows "89" (not undefined)
- [ ] **Response Time**: Shows "2.3h" (not undefined)

### **Service Cards**
- [ ] **AI Assistant**: Shows "active" status
- [ ] **CRM Service**: Shows "active" status
- [ ] **Email Parser**: Shows "active" status
- [ ] **ML Scoring**: Shows "inactive" status

### **Activity Feed**
- [ ] **Recent items**: Shows mock activity items
- [ ] **Timestamps**: Shows "2 minutes ago", "15 minutes ago"
- [ ] **Status icons**: Green/yellow/red icons
- [ ] **No raw JSON**: Clean, formatted display

### **Mock API Responses**
- [ ] **Health check**: Returns mock health data
- [ ] **Service tests**: Return mock responses
- [ ] **Loading states**: Show during mock delays
- [ ] **Error handling**: Graceful fallbacks

## 5. 🔐 **Auth & Onboarding**

### **Login Form**
- [ ] **Invalid login**: Shows error message
- [ ] **Valid login**: Redirects to dashboard
- [ ] **Form validation**: Required fields show errors
- [ ] **Password visibility**: Eye icon toggles

### **Onboarding Wizard**
- [ ] **Step progression**: Each step advances properly
- [ ] **Back button**: Works on all steps
- [ ] **Progress bar**: Updates at every step
- [ ] **Form validation**: Can't proceed with empty fields

### **Navigation**
- [ ] **Skip onboarding**: Doesn't crash app
- [ ] **Refresh during onboarding**: Maintains state
- [ ] **Direct URL access**: Works properly
- [ ] **Logout**: Returns to login page

## 6. 🧪 **Feature Flags Testing**

### **Toggle Testing**
- [ ] **Onboarding off**: Route disappears cleanly
- [ ] **CRM page off**: Route disappears cleanly
- [ ] **Debug mode on**: Shows debug info
- [ ] **Mock data off**: Calls real API

### **Mock Mode**
- [ ] **Mock data on**: All services use mock data
- [ ] **Mock data off**: Calls real backend API
- [ ] **API errors**: Falls back to mock data
- [ ] **Loading states**: Show during API calls

### **Debug Mode**
- [ ] **Debug info**: Shows "Mock Data" / "Live Data" labels
- [ ] **Console logs**: Extra debugging information
- [ ] **Performance**: No performance impact
- [ ] **Production**: Debug mode off in production

## 7. 📝 **Copy & Language**

### **Content Quality**
- [ ] **No Lorem ipsum**: All text is real content
- [ ] **No typos**: Spell-check all visible text
- [ ] **Grammar**: Proper grammar throughout
- [ ] **Consistency**: Professional but friendly tone

### **Button Labels**
- [ ] **Action verbs**: "Save Lead", "Send Email", "Test Service"
- [ ] **Not generic**: Avoid "Save", "Submit", "OK"
- [ ] **Clear intent**: User knows what will happen
- [ ] **Consistent style**: Title Case for buttons

### **Error Messages**
- [ ] **User-friendly**: No technical jargon
- [ ] **Actionable**: Tell user what to do next
- [ ] **Specific**: Not generic "Something went wrong"
- [ ] **Helpful**: Provide solutions when possible

## 8. 🛠️ **Dev Hygiene**

### **Code Quality**
- [ ] **ESLint**: `npm run lint` passes with no warnings
- [ ] **TypeScript**: `npm run type-check` passes with no errors
- [ ] **Prettier**: `npm run format` cleans code style
- [ ] **Build**: `npm run build` creates production build

### **Git Hygiene**
- [ ] **Commit messages**: Clear, descriptive messages
- [ ] **No console.log**: Remove debug logs before commit
- [ ] **No TODO comments**: Complete or remove TODOs
- [ ] **Clean diffs**: Only relevant changes

### **Performance**
- [ ] **Bundle size**: Reasonable JavaScript bundle size
- [ ] **Load time**: Fast initial page load
- [ ] **No memory leaks**: Clean up event listeners
- [ ] **Optimized images**: Proper image formats and sizes

## 🚀 **How to Use This Checklist**

### **Step 1: Setup**
```bash
cd frontend
# Ensure mockData = true in config.ts
./dev.sh
```

### **Step 2: Testing**
1. **Open http://localhost:3000** in Chrome
2. **Open DevTools** → Device toolbar
3. **Test mobile** (375px width)
4. **Work through each section** (10-15 minutes)

### **Step 3: Bug Tracking**
- **Log bugs** in GitHub Issues or Notion
- **Include screenshots** for visual issues
- **Include steps to reproduce**
- **Priority**: Critical → High → Medium → Low

### **Step 4: Iteration**
- **Fix → re-run checklist → repeat**
- **Focus on critical issues first**
- **Test after each fix**
- **Commit working changes**

## 🎯 **Success Criteria**

### **Must Pass (Blocking)**
- [ ] No console errors
- [ ] Mobile layout works
- [ ] All buttons have hover states
- [ ] Mock data displays correctly
- [ ] No typos in user-facing text

### **Should Pass (Important)**
- [ ] All feature flags work
- [ ] Loading states everywhere
- [ ] Error handling graceful
- [ ] Accessibility basics
- [ ] Performance acceptable

### **Nice to Pass (Polish)**
- [ ] Smooth animations
- [ ] Micro-interactions
- [ ] Advanced accessibility
- [ ] Performance optimized

---

**Remember: Perfect is the enemy of good. Fix critical issues first, polish later!** 🎯
