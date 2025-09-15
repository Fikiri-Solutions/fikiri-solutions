# 🎯 Lightweight Frontend Development Workflow

## 🚀 **Quick Start**

```bash
cd frontend
./dev.sh
```

This script will:
- ✅ Install dependencies
- ✅ Run type check
- ✅ Run linter
- ✅ Format code
- ✅ Start dev server with hot reload

## 🔧 **Development Commands**

### **Essential Commands**
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run type-check   # TypeScript type checking
npm run lint         # ESLint code analysis
npm run lint:fix     # Auto-fix linting issues
npm run format       # Prettier code formatting
```

### **Quality Checks**
```bash
npm run check-all    # Run all checks (type, lint, format)
```

## 🎛️ **Feature Flags**

Edit `src/config.ts` to toggle features:

```typescript
export const features = {
  onboarding: true,     // Show onboarding wizard
  crmPage: false,       // Hide CRM page until ready
  darkMode: false,      // Dark mode toggle
  mockData: true,       // Use mock data for testing
  debugMode: false,     // Show debug info
}
```

## 🧪 **Testing Workflow**

### **Before Each Commit**
1. **Type check**: `npm run type-check`
2. **Lint**: `npm run lint`
3. **Format**: `npm run format`
4. **Visual check**: Open browser, scan for issues

### **UI Testing Checklist**
- [ ] **Spacing**: Consistent padding/margins
- [ ] **Hover states**: All buttons have hover feedback
- [ ] **Mobile**: Test on phone-sized screen
- [ ] **Loading states**: Show spinners during async ops
- [ ] **Error handling**: User-friendly error messages

## 📱 **Mock Data Testing**

The app uses mock data by default for local testing:

- **Services**: Mock service status and metrics
- **Activity**: Mock recent activity feed
- **API Responses**: Simulated API delays and responses

To switch to real API:
```typescript
// In config.ts
mockData: false  // Use real backend API
```

## 🐛 **Common Issues & Fixes**

### **TypeScript Errors**
```bash
npm run type-check  # See all type errors
```

### **Linting Issues**
```bash
npm run lint:fix    # Auto-fix most issues
```

### **Build Issues**
```bash
npm run build       # Check production build
```

## 🎯 **Development Philosophy**

### **Local-First**
- ✅ No CI/CD complexity
- ✅ No production hosting yet
- ✅ Quick restart cycle
- ✅ Focus on UI/UX

### **Error-Proofing**
- ✅ Strict TypeScript everywhere
- ✅ ESLint + Prettier auto-fix
- ✅ Consistent spacing with Tailwind
- ✅ Feature flags for safe testing

### **Customer-Focused**
- ✅ Human-friendly copy
- ✅ Mobile-first design
- ✅ Intuitive navigation
- ✅ Visual feedback everywhere

## 🚀 **Next Steps**

1. **Start development**: `./dev.sh`
2. **Test features**: Use feature flags to toggle
3. **Fix UI issues**: Use testing checklist
4. **Iterate quickly**: Hot reload for instant feedback

---

**Remember: Perfect is the enemy of good. Fix obvious issues first, polish later!** 🎯

