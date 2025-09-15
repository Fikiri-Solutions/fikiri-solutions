# Performance Budget Configuration

## 📊 Performance Targets

### Core Web Vitals
- **Largest Contentful Paint (LCP)**: ≤ 2.5s
- **Cumulative Layout Shift (CLS)**: ≤ 0.1
- **First Input Delay (FID)**: ≤ 200ms
- **Interaction to Next Paint (INP)**: ≤ 200ms

### Bundle Size Limits
- **Total JS (gzipped)**: ≤ 300-350KB for core app
- **CSS (gzipped)**: ≤ 50KB
- **Images**: ≤ 100KB per image
- **Fonts**: ≤ 100KB total

### API Performance
- **API latency (p95)**: ≤ 400ms for status/metrics
- **Database queries**: ≤ 200ms
- **External API calls**: ≤ 1s timeout

## 🛡️ Monitoring Setup

### Frontend Monitoring
```javascript
// Vercel Analytics (already configured)
// Add to vercel.json:
{
  "analytics": {
    "enabled": true
  }
}

// Sentry for error tracking (optional)
// npm install @sentry/react @sentry/tracing
```

### Backend Monitoring
```python
# Health check endpoint (already implemented)
@app.route('/api/health', methods=['GET'])
def api_health():
    # Returns service status and health metrics
    pass

# Rate limiting (add to Flask app)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

## 🚀 Production Optimizations

### Frontend
- ✅ **Code Splitting**: Dynamic imports for large components
- ✅ **Tree Shaking**: Remove unused code
- ✅ **Image Optimization**: WebP format, lazy loading
- ✅ **Caching**: Service worker for offline support
- ✅ **Compression**: Gzip/Brotli compression

### Backend
- ✅ **Database Indexing**: Optimize query performance
- ✅ **Caching**: Redis for frequently accessed data
- ✅ **CDN**: Static asset delivery
- ✅ **Load Balancing**: Multiple server instances
- ✅ **Monitoring**: Uptime and performance tracking

## 📈 Performance Testing

### Automated Testing
```bash
# Lighthouse CI
npm install -g @lhci/cli
lhci autorun

# WebPageTest
# Use webpagetest.org for detailed analysis

# Bundle Analyzer
npm install --save-dev webpack-bundle-analyzer
```

### Manual Testing Checklist
- [ ] **Mobile Performance**: Test on actual devices
- [ ] **Network Conditions**: Slow 3G, offline scenarios
- [ ] **Browser Compatibility**: Chrome, Safari, Firefox, Edge
- [ ] **Accessibility**: Screen readers, keyboard navigation
- [ ] **Security**: HTTPS, CSP headers, XSS protection

## 🔧 Performance Budget Enforcement

### Build-time Checks
```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['recharts'],
          ui: ['@headlessui/react', 'framer-motion']
        }
      }
    },
    chunkSizeWarningLimit: 350000 // 350KB
  }
})
```

### Runtime Monitoring
```javascript
// Performance observer
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (entry.entryType === 'largest-contentful-paint') {
      console.log('LCP:', entry.startTime);
      if (entry.startTime > 2500) {
        console.warn('LCP exceeds budget:', entry.startTime);
      }
    }
  }
});
observer.observe({ entryTypes: ['largest-contentful-paint'] });
```
