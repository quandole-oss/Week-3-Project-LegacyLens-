# LegacyLens Cost Analysis

## Development Costs

### Embedding Generation (One-Time Ingestion)
- LAPACK SRC + BLAS/SRC: ~1,500 routines, ~500K tokens total
- OpenAI text-embedding-3-small: $0.02 per 1M tokens
- **Cost: ~$0.01**

### LLM Usage (Development & Testing)
- Claude Sonnet: $3/1M input, $15/1M output tokens
- Estimated 50 test queries during development: ~200K input tokens, ~100K output tokens
- **Cost: ~$2.10**

### Infrastructure
- Pinecone: Free tier (100K vectors, sufficient for ~1,500 LAPACK chunks)
- Railway: Free tier / $5/mo hobby plan
- Vercel: Free tier for frontend
- **Cost: $0-5/month**

### Total Development Cost: **~$5-10**

---

## Production Cost Projections

### Per-Query Cost Breakdown
| Component | Cost per Query |
|-----------|---------------|
| Query embedding (OpenAI) | $0.000004 |
| Pinecone search | $0 (included in plan) |
| Claude Sonnet generation (~1K tokens) | $0.018 |
| **Total per query** | **~$0.018** |

### Scaling Projections

| Scale | Queries/month | LLM Cost | Embedding Cost | Pinecone | Total/month |
|-------|--------------|----------|---------------|----------|-------------|
| 100 users | 1,000 | $18 | $0.004 | $0 (free) | ~$18 |
| 1,000 users | 10,000 | $180 | $0.04 | $0 (free) | ~$180 |
| 10,000 users | 100,000 | $1,800 | $0.40 | $70 (standard) | ~$1,870 |
| 100,000 users | 1,000,000 | $18,000 | $4.00 | $200 (standard) | ~$18,200 |

### Cost Optimization Strategies

1. **Response caching**: Cache frequent queries (e.g., "What does DGESV do?") to avoid repeated LLM calls. Could reduce costs by 30-50% depending on query distribution.

2. **Model tiering**: Use Claude Haiku ($0.25/1M input) for simple queries, Sonnet only for complex explanations. Could reduce LLM cost by 60-70%.

3. **Embedding caching**: Cache query embeddings for repeated/similar queries. Minimal cost impact but reduces latency.

4. **Token optimization**: Reduce context window by only sending top-3 instead of top-10 chunks for simple queries. Reduces input tokens by ~70%.

### Break-Even Analysis
At $20/user/month SaaS pricing:
- 100 users: Revenue $2,000/mo, Cost $18/mo = highly profitable
- 1,000 users: Revenue $20,000/mo, Cost $180/mo = 99% margin
- 10,000 users: Revenue $200,000/mo, Cost $1,870/mo = 99% margin

The LLM cost per query (~$0.018) is low enough that this application scales extremely well economically.
