#!/usr/bin/env node
/**
 * Frontend Feature Test Script
 * Tests key frontend functionality without requiring a running dev server
 */

const fs = require('fs')
const path = require('path')

const colors = {
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  reset: '\x1b[0m',
  bold: '\x1b[1m'
}

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`)
}

function checkFile(filePath, description) {
  const fullPath = path.join(process.cwd(), filePath)
  const exists = fs.existsSync(fullPath)
  if (exists) {
    log(`✓ ${description}`, 'green')
    return true
  } else {
    log(`✗ ${description} - File not found: ${filePath}`, 'red')
    return false
  }
}

function checkFileContent(filePath, searchString, description) {
  const fullPath = path.join(process.cwd(), filePath)
  if (!fs.existsSync(fullPath)) {
    log(`✗ ${description} - File not found`, 'red')
    return false
  }
  
  const content = fs.readFileSync(fullPath, 'utf-8')
  if (content.includes(searchString)) {
    log(`✓ ${description}`, 'green')
    return true
  } else {
    log(`✗ ${description} - Pattern not found: ${searchString}`, 'yellow')
    return false
  }
}

function checkRoute(route, description) {
  // Check if route is defined in App.tsx
  const appPath = path.join(process.cwd(), 'src/App.tsx')
  if (!fs.existsSync(appPath)) {
    log(`✗ ${description} - App.tsx not found`, 'red')
    return false
  }
  
  const content = fs.readFileSync(appPath, 'utf-8')
  if (content.includes(`path="${route}"`) || content.includes(`path='${route}'`)) {
    log(`✓ ${description}`, 'green')
    return true
  } else {
    log(`✗ ${description} - Route not found: ${route}`, 'yellow')
    return false
  }
}

log('\n🧪 Frontend Feature Tests\n', 'bold')
log('=' .repeat(60), 'blue')

let passed = 0
let failed = 0

// Test 1: Core Pages
log('\n📄 Core Pages', 'bold')
const pages = [
  { file: 'src/pages/Login.tsx', desc: 'Login page' },
  { file: 'src/pages/Signup.tsx', desc: 'Signup page' },
  { file: 'src/pages/Dashboard.tsx', desc: 'Dashboard page' },
  { file: 'src/pages/CRM.tsx', desc: 'CRM page' },
  { file: 'src/pages/AIAssistant.tsx', desc: 'AI Assistant page' },
  { file: 'src/pages/Services.tsx', desc: 'Services page' },
  { file: 'src/pages/PricingPage.tsx', desc: 'Pricing page' },
  { file: 'src/pages/LandingPage.tsx', desc: 'Landing page' },
  { file: 'src/pages/GmailConnect.tsx', desc: 'Gmail Connect page' },
  { file: 'src/pages/Automations.tsx', desc: 'Automations page' },
  { file: 'src/pages/ChatbotBuilder.tsx', desc: 'Chatbot Builder page' }
]

pages.forEach(({ file, desc }) => {
  if (checkFile(file, desc)) passed++
  else failed++
})

// Test 2: Key Components
log('\n🧩 Key Components', 'bold')
const components = [
  { file: 'src/components/FikiriLogo.tsx', desc: 'FikiriLogo component' },
  { file: 'src/components/Layout.tsx', desc: 'Layout component' },
  { file: 'src/components/ErrorMessage.tsx', desc: 'ErrorMessage component' },
  { file: 'src/components/EmptyState.tsx', desc: 'EmptyState component' },
  { file: 'src/components/Skeleton.tsx', desc: 'Skeleton loaders' },
  { file: 'src/components/GmailConnection.tsx', desc: 'GmailConnection component' },
  { file: 'src/components/AccessibilityProvider.tsx', desc: 'AccessibilityProvider' }
]

components.forEach(({ file, desc }) => {
  if (checkFile(file, desc)) passed++
  else failed++
})

// Test 3: API Client
log('\n🔌 API Integration', 'bold')
if (checkFile('src/lib/api.ts', 'API client (lib/api.ts)')) {
  passed++
  // Check for key API methods
  if (checkFileContent('src/lib/api.ts', 'sendEmail', 'sendEmail method')) passed++
  else failed++
  
  if (checkFileContent('src/lib/api.ts', 'getAutomationRules', 'getAutomationRules method')) passed++
  else failed++
  
  if (checkFileContent('src/lib/api.ts', 'processDocument', 'processDocument method')) passed++
  else failed++
} else {
  failed++
}

// Test 4: Routes
log('\n🛣️  Routes', 'bold')
const routes = [
  { route: '/login', desc: 'Login route' },
  { route: '/signup', desc: 'Signup route' },
  { route: '/dashboard', desc: 'Dashboard route' },
  { route: '/crm', desc: 'CRM route' },
  { route: '/ai-assistant', desc: 'AI Assistant route' },
  { route: '/services', desc: 'Services route' },
  { route: '/pricing', desc: 'Pricing route' },
  { route: '/integrations/gmail', desc: 'Gmail integration route' }
]

routes.forEach(({ route, desc }) => {
  if (checkRoute(route, desc)) passed++
  else failed++
})

// Test 5: Configuration
log('\n⚙️  Configuration', 'bold')
const configs = [
  { file: 'src/config.ts', desc: 'Frontend config' },
  { file: 'vite.config.ts', desc: 'Vite config' },
  { file: 'tailwind.config.js', desc: 'Tailwind config' },
  { file: 'eslint.config.mjs', desc: 'ESLint config' }
]

configs.forEach(({ file, desc }) => {
  if (checkFile(file, desc)) passed++
  else failed++
})

// Test 6: Key Features
log('\n✨ Key Features', 'bold')
if (checkFileContent('src/pages/AIAssistant.tsx', 'sendEmail', 'AI Assistant email sending')) {
  passed++
} else {
  failed++
}

if (checkFileContent('src/pages/CRM.tsx', 'Kanban', 'CRM Kanban board')) {
  passed++
} else {
  failed++
}

if (checkFileContent('src/pages/Automations.tsx', 'createAutomationRule', 'Automation creation')) {
  passed++
} else {
  failed++
}

if (checkFileContent('src/pages/ChatbotBuilder.tsx', 'processDocument', 'Document processing')) {
  passed++
} else {
  failed++
}

if (checkFileContent('src/components/FikiriLogo.tsx', 'theme', 'Logo theme prop')) {
  passed++
} else {
  failed++
}

// Test 7: TypeScript & Build
log('\n🔨 Build & Type Safety', 'bold')
if (checkFile('tsconfig.json', 'TypeScript config')) {
  passed++
} else {
  failed++
}

if (checkFile('package.json', 'Package.json')) {
  passed++
} else {
  failed++
}

// Summary
log('\n' + '='.repeat(60), 'blue')
log(`\n📊 Test Summary`, 'bold')
log(`   Passed: ${passed}`, 'green')
log(`   Failed: ${failed}`, failed > 0 ? 'red' : 'green')
log(`   Total:  ${passed + failed}`, 'blue')

if (failed === 0) {
  log('\n✅ All frontend feature checks passed!', 'green')
  process.exit(0)
} else {
  log('\n⚠️  Some checks failed. Review the output above.', 'yellow')
  process.exit(1)
}

