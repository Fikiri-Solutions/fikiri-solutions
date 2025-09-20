# 🔐 **GitHub Secrets Configuration Guide**

## Required Secrets for CI/CD Pipeline

### **1. Deployment Secrets (Required for deployments)**

#### **Render (Backend)**
- `RENDER_API_KEY` - Your Render API key
- `RENDER_STAGING_SERVICE_ID` - Staging service ID from Render
- `RENDER_PRODUCTION_SERVICE_ID` - Production service ID from Render

#### **Vercel (Frontend)**
- `VERCEL_TOKEN` - Your Vercel API token
- `VERCEL_ORG_ID` - Your Vercel organization ID
- `VERCEL_PROJECT_ID` - Your Vercel project ID

### **2. Docker Secrets (Required for container builds)**
- `DOCKER_USERNAME` - Your Docker Hub username
- `DOCKER_PASSWORD` - Your Docker Hub password/token

### **3. Monitoring Secrets (Optional but recommended)**
- `SLACK_WEBHOOK_URL` - Slack webhook for deployment notifications
- `BACKEND_URL` - Your production backend URL (for smoke tests)
- `FRONTEND_URL` - Your production frontend URL (for smoke tests)

### **4. Performance Testing (Optional)**
- `LHCI_GITHUB_APP_TOKEN` - Lighthouse CI token for performance testing

---

## 🚀 **How to Add Secrets to GitHub**

### **Step 1: Go to Repository Settings**
1. Navigate to your GitHub repository
2. Click **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

### **Step 2: Add Each Secret**
1. Click **New repository secret**
2. Enter the secret name (exactly as listed above)
3. Enter the secret value
4. Click **Add secret**

### **Step 3: Verify Secrets**
- You should see all secrets listed (values are hidden for security)
- Secrets are available to all workflows in the repository

---

## 📋 **Quick Setup Checklist**

### **Essential for Basic Deployment:**
- [ ] `RENDER_API_KEY`
- [ ] `RENDER_PRODUCTION_SERVICE_ID`
- [ ] `VERCEL_TOKEN`
- [ ] `VERCEL_ORG_ID`
- [ ] `VERCEL_PROJECT_ID`

### **For Full CI/CD Pipeline:**
- [ ] `DOCKER_USERNAME`
- [ ] `DOCKER_PASSWORD`
- [ ] `SLACK_WEBHOOK_URL`
- [ ] `BACKEND_URL`
- [ ] `FRONTEND_URL`

### **Optional Enhancements:**
- [ ] `LHCI_GITHUB_APP_TOKEN`
- [ ] `RENDER_STAGING_SERVICE_ID`

---

## 🔍 **How to Get Each Secret**

### **Render API Key:**
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click your profile → **Account Settings**
3. Scroll to **API Keys** section
4. Click **Create API Key**
5. Copy the generated key

### **Render Service IDs:**
1. Go to your service in Render dashboard
2. Click **Settings** tab
3. Copy the **Service ID** from the URL or settings

### **Vercel Token:**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click your profile → **Settings**
3. Go to **Tokens** tab
4. Click **Create Token**
5. Copy the generated token

### **Vercel Project/Org IDs:**
1. Go to your project in Vercel
2. Click **Settings** tab
3. Copy **Project ID** and **Team ID** (Org ID)

### **Docker Hub Credentials:**
1. Go to [Docker Hub](https://hub.docker.com)
2. Create account or login
3. Go to **Account Settings** → **Security**
4. Create access token for password

---

## ⚠️ **Important Notes**

1. **Secrets are encrypted** - GitHub encrypts all secrets
2. **Values are hidden** - You can't see secret values after saving
3. **Environment-specific** - Secrets are available to all workflows
4. **Case-sensitive** - Secret names must match exactly
5. **No spaces** - Use underscores instead of spaces

---

## 🧪 **Test Your Setup**

After adding secrets, you can test by:

1. **Push to main branch** - Triggers production deployment
2. **Push to develop branch** - Triggers staging deployment
3. **Create pull request** - Runs tests and security scans

The workflow will automatically use the secrets when available and skip steps gracefully when they're not configured.

---

## 🆘 **Troubleshooting**

### **Common Issues:**
- **"Context access might be invalid"** - Secret not configured
- **"Invalid action input"** - Wrong parameter name
- **"Authentication failed"** - Invalid secret value

### **Solutions:**
- Check secret names match exactly
- Verify secret values are correct
- Ensure secrets are added to the right repository
- Check if secrets have proper permissions

**Your CI/CD pipeline will work perfectly once you add the essential secrets! 🚀**
