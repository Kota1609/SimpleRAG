# Deployment Guide

## ✅ Local Testing Complete

The Aurora Q&A system has been tested locally and is fully functional:

- ✅ Server starts successfully
- ✅ All 3,349 messages indexed
- ✅ Embedding model loaded (sentence-transformers/all-MiniLM-L6-v2)
- ✅ ChromaDB initialized
- ✅ Groq LLM integrated
- ✅ API endpoints working (`/`, `/health`, `/ask`)
- ✅ Average response time: ~500-1700ms

## 🚀 Deployment Options

### Option 1: Railway (Recommended)

**Steps:**

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Initialize project:
   ```bash
   cd /Users/Kota/Desktop/aurora
   railway init
   ```

4. Set environment variable:
   ```bash
   railway variables set GROQ_API_KEY=your_groq_api_key_here
   ```

5. Deploy:
   ```bash
   railway up
   ```

6. Get deployment URL:
   ```bash
   railway status
   ```

**Configuration:**
- Railway will automatically detect the `Dockerfile`
- The `railway.toml` file contains build and deployment config
- Health check is configured at `/health`

### Option 2: Render

**Steps:**

1. Create account at https://render.com

2. Create new "Web Service"

3. Connect GitHub repository (after pushing code)

4. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment Variables:
     - `GROQ_API_KEY`: `your_groq_api_key_here`

5. Deploy

**Alternative:** Use the included `render.yaml` file for automatic configuration.

### Option 3: Docker Deployment

**Build:**
```bash
docker build -t aurora-qa .
```

**Run locally:**
```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_groq_api_key_here \
  aurora-qa
```

**Deploy to any cloud:**
- AWS ECS
- Google Cloud Run
- Azure Container Instances
- DigitalOcean App Platform

### Option 4: Fly.io

**Steps:**

1. Install flyctl:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Login:
   ```bash
   fly auth login
   ```

3. Launch app:
   ```bash
   fly launch
   ```

4. Set secret:
   ```bash
   fly secrets set GROQ_API_KEY=your_groq_api_key_here
   ```

5. Deploy:
   ```bash
   fly deploy
   ```

## 📋 Pre-Deployment Checklist

- [x] Code tested locally
- [x] All dependencies in requirements.txt
- [x] .env.example created (template)
- [x] .gitignore configured (don't commit .env)
- [x] Dockerfile created and tested
- [x] Health check endpoint working
- [x] Logging configured
- [ ] GitHub repository created
- [ ] Code pushed to GitHub
- [ ] Deployment platform chosen
- [ ] Environment variables configured on platform
- [ ] Deployed and tested
- [ ] README updated with live URL

## 🧪 Post-Deployment Testing

Once deployed, test with:

```bash
# Replace with your deployment URL
DEPLOY_URL="https://your-app.railway.app"

# Test health
curl $DEPLOY_URL/health

# Test question
curl -X POST $DEPLOY_URL/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "When is Layla planning her trip to London?"}'
```

## 🐛 Troubleshooting

### Issue: Application won't start

**Check:**
- Logs for error messages
- GROQ_API_KEY is set correctly
- Port is correctly configured ($PORT on most platforms)

### Issue: Slow first request

**Reason:** Models and data load on startup (takes ~10-15 seconds)

**Solution:** Configure health check with appropriate timeout (60-100s)

### Issue: Memory errors

**Solution:** Increase memory allocation to at least 1GB (2GB recommended)

### Issue: ChromaDB persistence

**Solution:** Ensure volume/persistent storage is mounted at `/app/data/chromadb`

## 📊 Performance Tuning

**For production:**

1. Enable response caching
2. Add rate limiting
3. Use gunicorn with multiple workers:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```
4. Monitor response times and adjust `top_k_results` in config
5. Consider moving to Pinecone/Weaviate for larger datasets

## 🔒 Security

**Before going live:**

1. Remove or rotate API keys shown in documentation
2. Enable HTTPS (most platforms do this automatically)
3. Add authentication if needed
4. Set up CORS restrictions (currently allows all origins)
5. Implement rate limiting
6. Add request logging and monitoring

## 💰 Cost Estimates

**Monthly costs (estimated):**

- Groq API: ~$0.06 per 1K questions (very cheap)
- Railway: $5-10 (hobby plan, includes 500 hours)
- Render: $0 (free tier) or $7/month (starter)
- Fly.io: ~$5/month (256MB RAM)

**For 10K questions/month:** ~$5-10 total

## 📈 Monitoring

**Metrics to track:**

- Response latency (p50, p95, p99)
- Error rates
- API usage (Groq tokens)
- Memory usage
- Disk usage (ChromaDB size)

**Tools:**
- Built-in structured logging (JSON format)
- Platform-provided metrics (Railway/Render/Fly.io)
- Optional: Sentry for error tracking
- Optional: Prometheus + Grafana for advanced monitoring

