# Moroccan Legal RAG — Embedding Service

GPU-powered embedding generation for Arabic legal texts using Google Colab and Cloudflare Tunnel.

---

## Overview

The embedding service converts Arabic legal text into 1024-dimensional vector representations using `intfloat/multilingual-e5-large`. Embeddings are generated on a **Tesla T4 GPU via Google Colab** and returned to your local machine through a **Cloudflare Tunnel**.

```
┌──────────────────────┐          ┌──────────────────┐          ┌─────────────────────┐
│   Your Local Machine │          │  Cloudflare       │          │  Google Colab       │
│                      │          │  Tunnel           │          │  (T4 GPU)           │
│  Python scripts ─────┼────HTTP──▶┼──────────────────┼──HTTP───▶│                     │
│  (embedder client)   │          │  trycloudflare    │          │  FastAPI server     │
│                      │◀─────────┼──────────────────┼──────────│  multilingual-e5    │
│  PostgreSQL          │          │  .com             │          │  Port 8000          │
│  + pgvector          │          │                   │          │                     │
└──────────────────────┘          └──────────────────┘          └─────────────────────┘
```

### Components

| Component | Where | Purpose |
|-----------|-------|---------|
| **Colab Notebook** | Google Colab | Loads model on GPU, runs FastAPI server |
| **Cloudflare Tunnel** | Between Colab and your machine | Creates a public URL for the Colab server |
| **Embedder Client** | Local `src/retrieval/embedder.py` | Calls the embedding API or falls back to local CPU |
| **PostgreSQL + pgvector** | Local Docker | Stores embeddings and metadata |

### Modes

| Mode | When | Speed | Memory | Setup |
|------|------|-------|--------|-------|
| **Remote (Colab GPU)** | `EMBEDDING_SERVICE_URL` set | ~500 texts/s | 0 MB local | Colab notebook running |
| **Local (CPU)** | `EMBEDDING_SERVICE_URL` empty | ~10 texts/s | ~2 GB RAM | None (automatic) |

---

## Prerequisites

| Requirement | Purpose | Cost |
|-------------|---------|------|
| Google account | Colab access | Free |
| Cloudflare account | Tunnel (quick tunnels need no setup) | Free |
| Docker | PostgreSQL + pgvector | Free |
| Python 3.10+ | Local scripts | Free |
| Git | Clone repository | Free |

---

## Quick Start (5 minutes)

### Step 1: Start PostgreSQL

```bash
cd moroccan-legal-rag
docker-compose up -d

# Verify
docker-compose ps
# Expected: State = "healthy"
```

### Step 2: Open Colab Notebook

1. Open `notebooks/embedding_service_colab.ipynb` in Google Colab
2. **Runtime → Change runtime type → T4 GPU → Save**
3. Run all cells (Runtime → Run all or Ctrl+F9)

### Step 3: Get Tunnel URL

After the last cell runs, look for:

```
============================================================
✅ PUBLIC TUNNEL URL:
   https://grand-otters-smooth.trycloudflare.com
============================================================
```

Copy this URL.

### Step 4: Configure Local Environment

```bash
# Edit .env file
EMBEDDING_SERVICE_URL=https://grand-otters-smooth.trycloudflare.com
```

### Step 5: Verify Connection

```bash
# Test health endpoint
curl $EMBEDDING_SERVICE_URL/health
```

Expected response:

```json
{
  "status": "ok",
  "model": "intfloat/multilingual-e5-large",
  "device": "cuda",
  "dimension": 1024,
  "gpu_name": "Tesla T4"
}
```

### Step 6: Run Pipeline

```bash
# Install project in dev mode (first time only)
pip install -e .

# Seed test data
python scripts/seed_test_data.py

# Test retrieval
python scripts/debug_vector_search.py
```

---

## Colab Notebook Usage

### Starting the Service

1. Go to [Google Colab](https://colab.research.google.com/)
2. Open `notebooks/embedding_service_colab.ipynb`
3. **Runtime → Change runtime type → Hardware accelerator: T4 GPU**
4. Run cells in order or **Runtime → Run all**

### Cell-by-Cell Walkthrough

| Cell | Purpose | Expected Output | Time |
|------|---------|-----------------|------|
| Cell 1 | Install dependencies, download cloudflared | `✓ Environment setup complete` | ~30s |
| Cell 2 | Load model on GPU | `GPU: Tesla T4`, `Model loaded`, `✓ Warm-up` | ~20s |
| Cell 3 | Define FastAPI app | `✓ FastAPI app created` | <1s |
| Cell 4 | Start server + tunnel | `✅ PUBLIC TUNNEL URL: https://...` | ~5s |

### Runtime Limits

| Tier | Max Session | GPU | Idle Timeout |
|------|------------|-----|--------------|
| Free | ~12 hours | T4 | ~90 min |
| Colab Pro | ~24 hours | T4/P100 | ~90 min |
| Colab Pro+ | ~24 hours | T4/P100/V100 | Longer |

**Keep the Colab tab open and active** while running batch embedding jobs.

### When Colab Disconnects

Colab sessions expire or disconnect due to:

- **Idle timeout** (~90 minutes of no interaction)
- **Session limit reached** (~12 hours on free tier)
- **Browser closed or network issue**

What to do:

1. Re-open the notebook
2. Re-run all cells (Runtime → Run all)
3. Copy the **new** tunnel URL
4. Update `.env` with the new URL
5. Resume your work

**Data is safe** — all embeddings are stored in your local PostgreSQL. The Colab service is stateless.

---

## Local Configuration

### `.env` File

```bash
# Required
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=legal_rag
POSTGRES_USER=legal_rag_user
POSTGRES_PASSWORD=legal_rag_pass

# Optional — set to use Colab GPU
EMBEDDING_SERVICE_URL=https://your-tunnel.trycloudflare.com
```

### Switching Modes

| Action | Mode Used |
|--------|-----------|
| `.env` has `EMBEDDING_SERVICE_URL` + Colab running | Remote (GPU) |
| `.env` has `EMBEDDING_SERVICE_URL` but Colab stopped | Falls back to local |
| `.env` has `EMBEDDING_SERVICE_URL=` (empty) | Local (CPU) |

No code changes needed. The embedder auto-detects.

### Testing Connectivity

```bash
# Health check
curl $EMBEDDING_SERVICE_URL/health

# Single embedding
curl -X POST $EMBEDDING_SERVICE_URL/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["اختبار"]}'

# Batch embedding
curl -X POST $EMBEDDING_SERVICE_URL/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["نص 1", "نص 2", "نص 3"], "batch_size": 16}'
```

---

## API Reference

### `GET /health`

Returns service status.

**Response:**
```json
{
  "status": "ok",
  "model": "intfloat/multilingual-e5-large",
  "device": "cuda",
  "dimension": 1024,
  "gpu_name": "Tesla T4"
}
```

### `POST /embed`

Generate embeddings for one or more texts.

**Request:**
```json
{
  "texts": ["المادة 147 من القانون الجنائي", "المادة 172 من مدونة السير"],
  "batch_size": 32
}
```

**Response:**
```json
{
  "embeddings": [
    [0.023, -0.014, ...],  // 1024 values
    [0.018, 0.031, ...]    // 1024 values
  ],
  "dimension": 1024,
  "count": 2,
  "time_ms": 45.3
}
```

### `GET /docs`

Interactive Swagger documentation.

---

## Python Usage

```python
from src.core.embedding import create_embedder

# Auto-detect mode from .env
embedder = create_embedder()

# Single text
embedding = embedder.embed_single("المادة 147 من القانون الجنائي")
print(embedding.shape)  # (1024,)

# Batch
texts = ["نص 1", "نص 2", "نص 3"]
embeddings = embedder.embed(texts)
print(embeddings.shape)  # (3, 1024)

# Check mode
print(embedder.mode)     # "remote" or "local"
print(embedder.dimension)  # 1024
```

---

## Architecture: How It Works

### Embedder Client (`src/retrieval/embedder.py`)

```
create_embedder()
    │
    ├── EMBEDDING_SERVICE_URL set?
    │   ├── YES → RemoteEmbedder()
    │   │         ├── Health check GET /health
    │   │         ├── Success → mode = "remote"
    │   │         └── Failure → fallback to LocalEmbedder()
    │   │
    │   └── NO → LocalEmbedder()
    │             └── Lazy-loads SentenceTransformer on first embed()
```

### Remote Embedding Flow

```
embed(["text1", "text2"])
    │
    ├── POST /embed {"texts": [...], "batch_size": 32}
    │
    ├── Colab GPU processes batch
    │
    ├── Response: {"embeddings": [[...], [...]], "time_ms": 45}
    │
    └── Returns np.ndarray of shape (2, 1024)
```

### Local Embedding Flow

```
embed(["text1", "text2"])
    │
    ├── Load model (first call only, ~20s)
    │
    ├── model.encode(texts, normalize=True)
    │
    └── Returns np.ndarray of shape (2, 1024)
```

---

## Performance Benchmarks

### Hardware

| Configuration | GPU | CPU | RAM |
|---------------|-----|-----|-----|
| Colab Free | Tesla T4 (16 GB VRAM) | 2 vCPU | 13 GB |
| Colab Pro | Tesla P100 (16 GB VRAM) | 4 vCPU | 25 GB |
| Typical Laptop | None | 4-8 cores | 8-16 GB |

### Embedding Speed

| Mode | Texts/Second | 100 Texts | 1,000 Texts | 10,000 Texts |
|------|-------------|-----------|-------------|--------------|
| Colab T4 GPU | ~500 | <1s | ~2s | ~20s |
| Colab P100 GPU | ~700 | <1s | ~1.5s | ~15s |
| MacBook M2 CPU | ~15 | ~7s | ~70s | ~12 min |
| Intel i7 CPU | ~8 | ~13s | ~2 min | ~20 min |
| Intel i5 CPU | ~5 | ~20s | ~3 min | ~33 min |

### Network Overhead

| Latency Component | Time |
|-------------------|------|
| Colab → Cloudflare | 10-50ms |
| Cloudflare → Your machine | 10-100ms |
| HTTP request overhead | 5-20ms |
| **Total per batch** | **50-200ms** |

Network overhead is negligible compared to embedding time on CPU, but noticeable compared to GPU speed. Use large batch sizes (32-64) to minimize round-trips.

---

## Troubleshooting

### "Tunnel URL not appearing in Colab"

**Cause:** `cloudflared` download failed or tunnel couldn't start.

**Fix:**
1. Check Cell 1 output — did `cloudflared` download successfully?
2. Re-run Cell 4
3. If persistent, run in terminal: `!./cloudflared tunnel --url http://localhost:8000`
4. Check Cloudflare status: https://www.cloudflarestatus.com/

### "Connection refused" or "ConnectionError" locally

**Cause:** Colab notebook is not running or tunnel expired.

**Fix:**
1. Open Colab — is the notebook still running? (green checkmark on runtime)
2. If disconnected, re-run all cells
3. Copy the new tunnel URL
4. Update `.env` with the new URL
5. Re-run your script

### "Out of memory" on Colab

**Cause:** Model too large for available VRAM, or batch too large.

**Fix:**
1. **Runtime → Disconnect and delete runtime**
2. **Runtime → Change runtime type → T4 GPU**
3. Re-run all cells
4. Reduce batch size in your requests:
   ```python
   embedder.embed(texts, batch_size=16)  # Try smaller
   ```

### "Slow embedding" — taking minutes instead of seconds

**Cause:** Running on CPU instead of GPU.

**Fix:**
1. Check Colab: **Runtime → Change runtime type → T4 GPU** (not "None" or "CPU")
2. Re-run Cell 2 — verify: `GPU: Tesla T4`
3. If `CUDA available: False`, restart runtime and re-select GPU

### "psycopg2 error" or "could not connect to server"

**Cause:** PostgreSQL Docker container not running.

**Fix:**
```bash
# Check container
docker-compose ps

# Start if stopped
docker-compose up -d

# Check logs
docker-compose logs postgres
```

### "ModuleNotFoundError: No module named 'src'"

**Cause:** Project not installed in development mode.

**Fix:**
```bash
pip install -e .
```

### "CUDA out of memory" during large batches

**Cause:** Single batch exceeds GPU VRAM.

**Fix:**
```python
# Split large batches
for i in range(0, len(texts), 32):
    batch = texts[i:i+32]
    embeddings = embedder.embed(batch)
```

### "Tunnel URL shows 'ERR_CONNECTION_REFUSED' in browser"

**Cause:** FastAPI server not running in Colab, or port mismatch.

**Fix:**
1. Verify Cell 4 output shows: `Uvicorn running on http://0.0.0.0:8000`
2. Check Cell 3 ran without errors: `✓ FastAPI app created`
3. Re-run Cells 3 and 4 in order

---

## Security Notes

### Current State (Development)

- **No authentication** — anyone with the tunnel URL can call the API
- **Temporary URLs** — tunnel URLs expire when Colab disconnects
- **No rate limiting** — single user, batch processing

### Production Hardening (Future)

- [ ] API key authentication on `/embed` endpoint
- [ ] Persistent named Cloudflare tunnels
- [ ] Rate limiting per API key
- [ ] Request logging and monitoring
- [ ] HTTPS certificate validation
- [ ] Input validation and size limits
- [ ] Colab auto-reconnect script

### Recommendations for Now

- Only share tunnel URLs within your team
- Don't expose sensitive legal texts publicly
- Tunnel URLs are ephemeral — they stop working when Colab disconnects
- Use `.env` and never commit `EMBEDDING_SERVICE_URL`

---

## Files Reference

| File | Purpose |
|------|---------|
| `notebooks/embedding_service_colab.ipynb` | Colab notebook (GPU server) |
| `src/retrieval/embedder.py` | Embedder client (local + remote) |
| `scripts/seed_test_data.py` | Seed database with test embeddings |
| `scripts/debug_vector_search.py` | Test vector search queries |
| `tests/test_embedder.py` | Pytest suite (local + remote) |
| `tests/conftest.py` | Auto-loads `.env` for tests |
| `.env` | Local configuration (gitignored) |
| `.env.example` | Template for `.env` |

---

## FAQ

**Q: Do I always need Colab running?**
A: Only for batch embedding. For quick tests (<10 texts), local CPU mode works fine. The embedder auto-falls back to local mode when Colab is unreachable.

**Q: How long does the tunnel URL last?**
A: Until the Colab runtime disconnects (idle timeout ~90 min, max session ~12 hours). Each restart generates a new URL.

**Q: Can I use this without Cloudflare?**
A: Yes. Use ngrok instead. Replace Cell 4's tunnel command with ngrok. The API and client code remain the same.

**Q: Is my data sent to Cloudflare?**
A: Data passes through Cloudflare's tunnel infrastructure but is not stored. For production, consider direct VPN instead.

**Q: Why not just run the model locally?**
A: You can. Set `EMBEDDING_SERVICE_URL=` (empty) in `.env`. It will be ~50x slower on CPU but works with zero setup.

**Q: Can multiple team members use the same Colab instance?**
A: Yes. Share the tunnel URL. All requests go to the same GPU. No concurrency limits in current setup.

**Q: What happens to my embeddings if Colab crashes mid-batch?**
A: Partial results are lost. Re-run the script — use `--clear` flag to start fresh if needed.
