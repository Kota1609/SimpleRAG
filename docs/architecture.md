# Architecture & Design Decisions

## System Overview

The Aurora Q&A system is built on a **Retrieval-Augmented Generation (RAG)** architecture, combining semantic search with large language models for accurate question answering.

## Core Components

### 1. Data Ingestion Layer

- **Fetcher Service:** Async HTTP client with caching
- **Cache Strategy:** TTL-based (1 hour default) to reduce API calls
- **Transformation:** Raw messages → Structured documents with metadata

### 2. Embedding & Indexing

- **Model:** `all-MiniLM-L6-v2` (384 dimensions, 100MB, fast)
- **Why this model:**
  - Good balance of size vs quality
  - Fast inference (~5ms per embedding)
  - Multilingual support if needed
  - Well-tested in production

### 3. Vector Store

- **Choice:** ChromaDB
- **Why ChromaDB:**
  - Embedded database (no separate server)
  - Excellent for dev + small prod deployments
  - Built-in similarity search
  - Easy persistence
- **Alternatives considered:**
  - FAISS: Faster but requires more manual management
  - Pinecone: Better for massive scale, but overkill + costs money
  - Weaviate: Excellent but complex setup

### 4. Retrieval Strategy

- **Search Type:** Cosine similarity on embeddings
- **Top-K:** 10 most relevant messages (configurable)
- **Reranking:** Optional (not implemented for simplicity)

### 5. LLM Generation

- **Provider:** Groq (fastest LLM API)
- **Model:** Llama 3.3 70B Versatile
- **Why Groq:**
  - 10x faster than OpenAI (real-time inference)
  - Competitive pricing
  - Open-source models
- **Prompt Engineering:**
  - System role: Data analyst
  - JSON output format for structured responses
  - Low temperature (0.1) for factual consistency
  - Explicit instruction to only use provided context

## Data Flow

```
1. User Question
   ↓
2. Generate question embedding (50ms)
   ↓
3. Search vector store for top-K similar messages (50ms)
   ↓
4. Build context from retrieved messages
   ↓
5. Send to LLM with structured prompt (800ms)
   ↓
6. Parse & validate JSON response
   ↓
7. Return answer with confidence + sources
```

## Alternative Approaches & Trade-offs

### Approach 1: Keyword/Regex Matching

```python
# Simple pattern matching
if "how many" in question and "car" in question:
    # Extract member name, count cars in messages
```

**Pros:** Fast, no dependencies, deterministic

**Cons:** Brittle, no semantic understanding, high maintenance

**Decision:** ❌ Too limited

### Approach 2: Traditional NER + Rule-Based

```python
# Use spaCy for entity extraction
entities = nlp(question).ents
# Then apply rules based on entities
```

**Pros:** Explainable, good for structured queries

**Cons:** Requires extensive rule writing, poor generalization

**Decision:** ❌ Too much manual work

### Approach 3: RAG (Chosen) ✅

**Pros:** 

- Handles semantic questions
- Scales to dataset growth
- Good accuracy
- Relatively simple

**Cons:**

- Requires LLM API
- Slight latency (~1s)

**Decision:** ✅ Best overall

### Approach 4: Fine-tuned T5/BART

**Pros:** No API costs after training, customized

**Cons:** Requires labeled Q&A pairs, training time, hosting costs

**Decision:** ❌ Overkill for this scale

### Approach 5: Knowledge Graph + LLM

```
Members → Relations → Entities (trips, cars, etc.)
Then query graph + LLM
```

**Pros:** Excellent for complex relational queries

**Cons:** Requires entity extraction, graph construction, maintenance

**Decision:** ❌ Over-engineered for current needs (could be Phase 2)

## Scalability Considerations

### Current System (< 10K messages)

- ChromaDB embedded
- In-memory caching
- Single instance deployment

### Future Scaling (10K - 1M messages)

- Move to Pinecone/Weaviate
- Redis for distributed caching
- Horizontal scaling with load balancer
- Batch indexing jobs

### Enterprise Scale (1M+ messages)

- Hybrid search (dense + sparse)
- Reranking models
- Multi-index strategy (by date, member, topic)
- Real-time streaming ingestion

## Performance Optimization

1. **Embedding Cache:** Store embeddings to avoid recomputation
2. **Batch Processing:** Index messages in batches
3. **Async I/O:** Non-blocking API calls
4. **Connection Pooling:** Reuse HTTP connections
5. **LLM Response Streaming:** (Optional) Stream tokens for UX

## Monitoring & Observability

### Metrics to Track

- Response latency (p50, p95, p99)
- Retrieval accuracy
- LLM token usage
- Cache hit rate
- Error rates

### Logging Strategy

```python
logger.info("question_answered", {
    "question": question,
    "answer_length": len(answer),
    "retrieved_docs": num_docs,
    "llm_latency": latency,
    "confidence": confidence
})
```

## Cost Analysis

**Per 1000 Questions:**

- Groq API: ~$0.06 (70B model)
- Embedding computation: $0 (local)
- Infrastructure: ~$5/month (Railway/Render)

**Total:** ~$5/month + $0.06 per 1K questions

Compare to OpenAI GPT-4: ~$0.30 per 1K questions

## Security & Privacy

- No PII stored in vector database
- API key management via env variables
- Rate limiting to prevent abuse
- Input sanitization
- Audit logging for compliance

