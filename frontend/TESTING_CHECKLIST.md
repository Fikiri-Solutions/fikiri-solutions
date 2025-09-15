# 🧪 UI Testing Checklist - "Stupid Proof" Edition

## 🎯 **Quick Visual Checks** (30 seconds per page)

### **Spacing & Alignment**
- [ ] **Card spacing**: All cards have consistent padding (16px/24px)
- [ ] **Button alignment**: Buttons are properly aligned in forms
- [ ] **Text spacing**: Headers have proper margin-bottom (16px/24px)
- [ ] **Grid gaps**: Dashboard cards have consistent gaps (16px/24px)

### **Interactive Elements**
- [ ] **Button hover**: All buttons have hover state (darker color)
- [ ] **Button disabled**: Disabled buttons are grayed out
- [ ] **Input focus**: Input fields show blue border on focus
- [ ] **Link hover**: Links change color on hover

### **Text & Copy**
- [ ] **Human-friendly**: No technical jargon in user-facing text
- [ ] **Consistent tone**: Professional but approachable
- [ ] **No typos**: Spell-check all visible text
- [ ] **Proper capitalization**: Titles use Title Case, buttons use Sentence case

### **Mobile Responsiveness**
- [ ] **Mobile view**: Test on phone-sized screen (375px width)
- [ ] **Touch targets**: Buttons are at least 44px tall
- [ ] **Text readable**: No horizontal scrolling needed
- [ ] **Navigation**: Sidebar collapses properly on mobile

## 🔍 **Component-Specific Checks**

### **Dashboard Page**
- [ ] **Metrics cards**: All 4 cards display properly
- [ ] **Service status**: Green/red indicators work
- [ ] **Activity feed**: Recent items show with timestamps
- [ ] **Loading states**: Shows loading spinner during API calls

### **Login Page**
- [ ] **Form validation**: Shows errors for empty fields
- [ ] **Password visibility**: Eye icon toggles password visibility
- [ ] **Remember me**: Checkbox works
- [ ] **Forgot password**: Link is clickable

### **Onboarding Wizard**
- [ ] **Step indicators**: Progress bar shows current step
- [ ] **Navigation**: Previous/Next buttons work
- [ ] **Form validation**: Can't proceed with empty required fields
- [ ] **Service selection**: Checkboxes toggle properly

### **Services Page**
- [ ] **Service toggles**: Enable/disable works visually
- [ ] **Settings panels**: Expand/collapse when service enabled
- [ ] **Save button**: Only enabled when changes made
- [ ] **Test buttons**: Show loading state when clicked

## 🐛 **Common Bug Patterns**

### **Layout Issues**
- [ ] **Overflow**: Text doesn't break out of containers
- [ ] **Z-index**: Modals appear above other content
- [ ] **Sticky elements**: Sidebar stays in place when scrolling
- [ ] **Responsive breakpoints**: No layout breaks at 768px, 1024px

### **State Management**
- [ ] **Loading states**: Show spinners during async operations
- [ ] **Error states**: Show user-friendly error messages
- [ ] **Empty states**: Show helpful messages when no data
- [ ] **Success states**: Show confirmation when actions complete

### **Accessibility**
- [ ] **Focus indicators**: Keyboard navigation shows focus
- [ ] **Alt text**: Images have descriptive alt text
- [ ] **Color contrast**: Text is readable on background
- [ ] **Screen reader**: Logical tab order

## 🚀 **Testing Workflow**

### **Before Each Commit**
1. **Run type check**: `npm run type-check`
2. **Run linter**: `npm run lint`
3. **Format code**: `npm run format`
4. **Visual check**: Open browser, scan for obvious issues

### **Before Each Feature**
1. **Enable feature flag**: Update `config.ts`
2. **Test feature**: Use checklist above
3. **Test integration**: Make sure it works with other features
4. **Disable if broken**: Turn off feature flag if issues found

### **Weekly Deep Check**
1. **Full checklist**: Go through entire checklist
2. **Cross-browser**: Test in Chrome, Firefox, Safari
3. **Mobile testing**: Test on actual mobile device
4. **Performance**: Check for slow loading or janky animations

## 🎯 **Success Criteria**

### **Must Have** (Blocking)
- [ ] No console errors
- [ ] All buttons have hover states
- [ ] Mobile layout works
- [ ] No typos in user-facing text

### **Should Have** (Important)
- [ ] Loading states for all async operations
- [ ] Error handling with user-friendly messages
- [ ] Consistent spacing throughout
- [ ] Proper focus indicators

### **Nice to Have** (Polish)
- [ ] Smooth animations
- [ ] Micro-interactions
- [ ] Advanced accessibility features
- [ ] Performance optimizations

## 🔧 **Quick Fixes**

### **Common Issues & Solutions**
```css
/* Fix button hover states */
.btn:hover { transform: translateY(-1px); }

/* Fix spacing consistency */
.card { padding: 1.5rem; margin-bottom: 1rem; }

/* Fix mobile touch targets */
button { min-height: 44px; }

/* Fix text readability */
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
```

### **TypeScript Fixes**
```typescript
// Fix unused variables
const { unused, ...used } = data; // Use rest operator

// Fix any types
const response: ApiResponse = await api.get('/endpoint');

// Fix missing return types
const handleClick = (): void => { /* ... */ };
```

---

**Remember: Perfect is the enemy of good. Fix the obvious issues first, polish later!** 🎯
