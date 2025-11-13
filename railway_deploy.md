# 🚀 Railway Deployment Guide

## ✅ Pre-Deployment Checklist

- [x] Dockerfile configured for Railway ($PORT variable)
- [x] TOKENIZERS_PARALLELISM=false set
- [x] Timeouts added to Groq client (30s)
- [x] Messages backup included in Docker image
- [x] ChromaDB will rebuild on startup (5-10 seconds)
- [x] Health check endpoint ready

## 📦 What Happens on Railway:

1. **Build:** Docker image builds (~2-3 minutes)
2. **Startup:** 
   - Loads embedding model (~2 seconds)
   - Fetches messages from API (~1 second)
   - Indexes 3,349 messages (~5 seconds)
   - BM25 indexing (~1 second)
   - **Total startup: ~10 seconds**
3. **Ready:** Health check passes ✅

## 🔧 Railway Configuration:

1. Create new project on Railway
2. Connect this GitHub repo
3. Add environment variable:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```
4. Deploy! 🚀

## ⚡ Notes:

- **Ephemeral storage:** ChromaDB rebuilds on each deployment (fast!)
- **Cold starts:** ~10 seconds (includes full indexing)
- **API fallback:** Uses backup if external API is down
- **Memory:** ~500MB RAM (Sentence-Transformers + ChromaDB)
- **Response time:** 400-1500ms per question

## 🎯 Expected URL:
```
https://your-app.up.railway.app/
```

Test with:
```bash
curl -X POST https://your-app.up.railway.app/ask \
  -H "Content-Type: application/json" \
  --data-binary @- << 'EOFCURL'
{
  "question": "When is Layla planning her trip to London?"
}
EOFCURL
```
