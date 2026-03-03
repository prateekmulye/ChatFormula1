# 🚀 Deployment Guide

Deploy Chat P1 Agent to Render for free in 15 minutes.

---

## Overview

This guide will help you deploy Chat P1 to Render's free tier, making it publicly accessible and shareable.

**What You'll Get:**
- Public URL: `https://your-app.onrender.com`
- Free hosting (750 hours/month)
- Auto-sleep after 15 minutes of inactivity
- Professional, shareable demo

**Estimated Cost:** $0-5/month (using free tiers)

---

## Prerequisites

### 1. Accounts (All Free)

- **GitHub**: https://github.com/
- **Render**: https://render.com/ (sign up with GitHub)
- **OpenAI**: https://platform.openai.com/ ($5 free credit)
- **Pinecone**: https://www.pinecone.io/ (free starter plan)
- **Tavily**: https://tavily.com/ (1000 free searches/month)

### 2. API Keys

Collect these before starting:
- OpenAI API Key: `sk-...`
- Pinecone API Key: `pcsk_...`
- Tavily API Key: `tvly-...`

---

## Quick Deploy (15 Minutes)

### Step 1: Prepare Repository (2 min)

```bash
# Navigate to project
cd chatp1

# Initialize git (if not already)
git init
git add .
git commit -m "Ready for deployment"

# Create GitHub repository at https://github.com/new
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/chatp1.git
git branch -M main
git push -u origin main
```

### Step 2: Setup Pinecone Index (2 min)

```bash
# Set your Pinecone API key
export PINECONE_API_KEY='your-pinecone-api-key'

# Create the index
python scripts/setup_production_pinecone.py
```

This creates a Pinecone index named `f1-knowledge-free` optimized for the free tier.

### Step 3: Deploy to Render (10 min)

#### Option A: Automated Script

```bash
# Run deployment helper
./scripts/deploy_to_render.sh
```

Follow the prompts to enter your API keys.

#### Option B: Manual Deployment (Recommended First Time)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com
   - Click **"New +"** → **"Web Service"**

2. **Connect Repository**
   - Connect your GitHub account
   - Select your `chatp1` repository
   - Click **"Connect"**

3. **Configure Service**
   - **Name**: `chatp1-ui`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: Leave empty (or specify if in subdirectory)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```
     pip install poetry && poetry install --no-dev
     ```
   - **Start Command**: 
     ```
     poetry run streamlit run src/ui/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
     ```
   - **Instance Type**: **Free**

4. **Add Environment Variables**
   
   Click **"Environment"** tab and add:
   
   ```
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-3.5-turbo
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   
   PINECONE_API_KEY=pcsk-your-key-here
   PINECONE_INDEX_NAME=f1-knowledge-free
   
   TAVILY_API_KEY=tvly-your-key-here
   TAVILY_MAX_RESULTS=3
   
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   
   # Rate Limiting (stay in free tier)
   MAX_REQUESTS_PER_MINUTE=3
   MAX_REQUESTS_PER_DAY=100
   ENABLE_RATE_LIMITING=true
   
   # Caching (reduce API calls)
   ENABLE_CACHING=true
   CACHE_TTL_SECONDS=3600
   ```

5. **Create Web Service**
   - Click **"Create Web Service"**
   - Wait 5-10 minutes for deployment

### Step 4: Verify Deployment (1 min)

1. **Check Logs**
   - In Render Dashboard → Your Service → **Logs**
   - Look for: `You can now view your Streamlit app`

2. **Test Application**
   - Visit your URL: `https://chatp1-ui.onrender.com`
   - First load takes ~30 seconds (cold start)
   - Try: "Who won the 2023 F1 championship?"

3. **Verify Rate Limiting**
   - Make 4 requests quickly
   - Should see rate limit message on 4th request

---

## Alternative: Blueprint Deployment

Use `render.yaml` for infrastructure-as-code deployment.

### 1. Create render.yaml

```yaml
services:
  - type: web
    name: chatp1-ui
    runtime: python
    buildCommand: pip install poetry && poetry install --no-dev
    startCommand: poetry run streamlit run src/ui/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
    plan: free
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: PINECONE_API_KEY
        sync: false
      - key: TAVILY_API_KEY
        sync: false
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
```

### 2. Deploy via Blueprint

```bash
# Commit render.yaml
git add render.yaml
git commit -m "Add Render blueprint"
git push

# In Render Dashboard:
# New + → Blueprint → Connect repository → Deploy
```

---

## Post-Deployment

### Monitor Usage

Set up monitoring to stay within free tiers:

1. **OpenAI Usage**
   - Dashboard: https://platform.openai.com/usage
   - Set alert at 80% of $5 limit
   - Set hard limit: $5/month

2. **Pinecone Usage**
   - Dashboard: https://app.pinecone.io/
   - Monitor vector count (max 100K)
   - Monitor query count

3. **Tavily Usage**
   - Dashboard: https://app.tavily.com/
   - Track daily searches
   - Limit: 30 searches/day recommended

4. **Render Usage**
   - Dashboard: https://dashboard.render.com/
   - Track hours used (750/month free)
   - Monitor auto-sleep behavior

### Share Your App

**Professional Template:**

```
Hi [Name],

I've built an AI-powered F1 chatbot using modern AI/ML technologies.

🚀 Live Demo: https://chatp1-ui.onrender.com
📂 GitHub: https://github.com/YOUR_USERNAME/chatp1

Tech Stack:
- Python, LangChain, LangGraph
- OpenAI GPT, Pinecone Vector DB
- RAG Architecture, Streamlit UI

Features:
- Real-time F1 information
- Historical data queries
- Race predictions
- Conversational AI with citations

Note: First load takes 30s (free tier wakes up).

Best regards,
[Your Name]
```

---

## Cost Protection

### Free Tier Limits

| Service | Free Tier | Strategy |
|---------|-----------|----------|
| **Render** | 750 hrs/month | Auto-sleep after 15min |
| **OpenAI** | $5 credit | Rate limit: 3 RPM, 200 RPD |
| **Pinecone** | 100K vectors | Efficient chunking |
| **Tavily** | 1000/month | Limit: 30 searches/day |

### Built-in Protection

1. **Rate Limiting**
   - User level: 3 requests/min, 100/day
   - Service level: Automatic throttling
   - Friendly error messages

2. **Caching**
   - LLM responses: 1 hour
   - Vector searches: 30 minutes
   - Tavily results: 24 hours

3. **Auto-Sleep**
   - Render sleeps after 15min inactivity
   - Zero cost when not in use
   - ~30 second wake-up time

4. **Usage Alerts**
   - Email at 80% of limits
   - Automatic shutdown at 95%
   - Daily usage reports

---

## Troubleshooting

### App Won't Start

**Check Render Logs:**
```
Dashboard → Your Service → Logs
```

**Common Issues:**
- Missing environment variables
- Invalid API keys
- Build command failed
- Port configuration wrong

**Solutions:**
1. Verify all env vars are set
2. Check API keys are valid
3. Ensure Poetry is installed in build
4. Verify start command uses `$PORT`

### Slow First Load

**This is normal!**
- Free tier sleeps after 15min inactivity
- First request wakes it up (~30 seconds)
- Subsequent requests are fast

**Solutions:**
- Add note to users about cold start
- Use uptime monitoring to keep warm (optional)
- Upgrade to paid tier for always-on

### Rate Limit Errors

**This is working as intended!**
- Protects your free tier limits
- Users see friendly message
- Prevents cost overruns

**Adjust if needed:**
```bash
# In Render environment variables
MAX_REQUESTS_PER_MINUTE=5  # Increase if needed
MAX_REQUESTS_PER_DAY=200   # Increase if needed
```

### Out of OpenAI Credits

**Solutions:**
1. Add payment method to OpenAI
2. Set $5/month hard limit
3. Monitor usage more closely
4. Increase caching TTL

### Pinecone Index Full

**Solutions:**
1. Delete old vectors
2. Optimize chunking strategy
3. Upgrade to paid plan
4. Use multiple indexes

---

## Optional Enhancements

### Custom Domain

1. Go to Service Settings → **Custom Domain**
2. Add your domain (e.g., `f1.yourdomain.com`)
3. Configure DNS with provided values
4. Free on Render!

### Uptime Monitoring

Use **UptimeRobot** (free):
1. Sign up: https://uptimerobot.com/
2. Add monitor for your Render URL
3. Get alerts if app goes down
4. Optional: Keep app warm with pings

### Analytics

Add **Google Analytics**:
1. Create GA4 property
2. Add tracking code to Streamlit app
3. Monitor user interactions
4. Track popular queries

---

## Deployment Checklist

- [ ] GitHub repository created and pushed
- [ ] Pinecone index created
- [ ] Render account created
- [ ] Web service configured
- [ ] Environment variables set
- [ ] Deployment successful
- [ ] Application accessible
- [ ] Rate limiting working
- [ ] Usage monitoring set up
- [ ] OpenAI hard limit set
- [ ] Shareable link ready

---

## Success Criteria

✅ Application is live and accessible  
✅ Rate limiting is working  
✅ All API integrations working  
✅ Monitoring is set up  
✅ Usage alerts configured  
✅ Shareable link ready  

---

## Next Steps

1. ✅ Deploy your app
2. 📊 Monitor usage for first week
3. 🎯 Share with recruiters/portfolio
4. 📈 Ingest more F1 data (optional)
5. 🚀 Add new features

---

## Support

- **Setup Issues**: See [Setup Guide](SETUP.md)
- **Render Docs**: https://render.com/docs
- **Check Logs**: Render Dashboard → Logs
- **GitHub Issues**: Open an issue for bugs

---

**Ready to deploy? Let's go! 🏎️**
