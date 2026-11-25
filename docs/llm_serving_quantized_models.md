# Serving Quantized LLMs with llama.cpp

> How we serve **Gemma 4 (2B)** on limited hardware using **GGUF quantization** and **llama.cpp** for memory-efficient inference.

---

## 1. Why Quantization?

Full-precision LLMs (FP16/FP32) require massive VRAM. A 2B-parameter model at FP16 needs ~4 GB just for weights, plus context & KV cache overhead — pushing it beyond most consumer GPUs.

**GGUF quantization** (e.g., `Q4_K_XL`) compresses weights to 4-bit integers, cutting model memory **~4×** while retaining >95% of the original quality for OCR correction tasks.

| Format | Weight size (2B params) | Quality loss |
|--------|------------------------|--------------|
| FP16   | ~4.0 GB                | None         |
| Q8_0   | ~2.0 GB                | Negligible   |
| Q4_K_M | ~1.2 GB                | <2%          |
| **Q4_K_XL** | **~1.1 GB**        | **<3%**      |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER WORKSTATION                             │
│                                                                     │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────────────────┐ │
│  │  Python  │────▶│ llama-cpp    │────▶│     NVIDIA GPU (CUDA)    │ │
│  │  Script  │     │ -python      │     │                          │ │
│  │          │◀────│  (binding)   │◀────│  ┌────────────────────┐  │ │
│  │ OCR text │     │              │     │  │  Gemma 4 (Q4_K_XL) │  │ │
│  │ correction│    └──────────────┘     │  │  n_gpu_layers = -1 │  │ │
│  └──────────┘                          │  └────────────────────┘  │ │
│                                        │                          │ │
│                                        │  GPU Memory Budget:      │ │
│                                        │  ┌─────────────────┐     │ │
│                                        │  │ Weights  ~1.1 GB │     │ │
│                                        │  │ KV Cache ~0.5 GB │     │ │
│                                        │  │ Overhead  ~0.2 GB│     │ │
│                                        │  │─────────────────│     │ │
│                                        │  │ TOTAL    ~1.8 GB │     │ │
│                                        │  └─────────────────┘     │ │
│                                        └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Inference Flow

```
                   ┌──────────────┐
                   │ Hugging Face │
                   │   Hub        │
                   │ (GGUF repo)  │
                   └──────┬───────┘
                          │ hf_hub_download()
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Local Disk: gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf (~1.1 GB)  │
└─────────────────────────────────────────────────────────────┘
                          │ Llama(model_path, ...)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 llama.cpp C++ Runtime                        │
│                                                             │
│   ┌──────────┐    ┌───────────┐    ┌──────────────────┐     │
│   │  GGML    │    │  CUDA     │    │  Metal / Vulkan  │     │
│   │ (CPU)    │    │ (NVIDIA)  │    │  (Apple/AMD)     │     │
│   └──────────┘    └───────────┘    └──────────────────┘     │
│        ▲               ▲                                     │
│        │               │                                     │
│   n_gpu_layers=0   n_gpu_layers=-1                          │
│   (pure CPU)       (all layers → GPU)                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  llama-cpp-python (Python bindings)                          │
│                                                             │
│  llm.create_chat_completion(                                 │
│      messages=[{"role":"user","content":prompt}],            │
│      temperature=0.0,    ← deterministic for OCR correction  │
│      max_tokens=2048     ← enough for a legal article        │
│  )                                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Corrected Arabic Text                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Key Configuration Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `model_path` | `gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf` | 4-bit quantized GGUF — smallest memory footprint with acceptable quality |
| `n_ctx` | `16384` | Context window large enough for a full legal article + OCR correction prompt |
| `n_gpu_layers` | `-1` | Offload **all** transformer layers to GPU for maximum throughput |
| `n_batch` | `1024` | Batch size for prompt processing; larger = faster ingestion, balanced against VRAM |
| `temperature` | `0.0` | Deterministic output — critical for legal OCR correction (no hallucination) |
| `max_tokens` | `2048` | Each Moroccan legal article fits within ~1000 tokens, 2048 provides safety margin |
| `verbose` | `False` | Suppress llama.cpp debug logs in production |

---

## 4. Memory Breakdown (Gemma 4 – 2B, Q4_K_XL)

```
Total GPU Memory Budget: ~1.8 GB
═══════════════════════════════════════════════════════
║                                                   ║
║  ████████████████████████████  Weights    1.10 GB  ║
║  ██████████████                KV Cache   0.46 GB  ║
║  ████                          Overhead   0.18 GB  ║
║  ██                            Free       0.26 GB  ║
║                                                   ║
═══════════════════════════════════════════════════════
         (fits in a 4 GB GPU such as RTX 3050)
```

**Formula (approximate):**

$$M_{\text{total}} \approx \frac{P \times B}{8} \;+\; 2 \times L \times H \times \frac{C}{G} \times 2 \;+\; M_{\text{overhead}}$$

Where:
- $P$ = number of parameters (2B)
- $B$ = bits per weight (4 for Q4)
- $L$ = number of layers
- $H$ = hidden size
- $C$ = context length (16384)
- $G$ = number of KV heads
- $M_{\text{overhead}}$ = CUDA runtime overhead (~200 MB)

---

## 5. Why llama.cpp for This Use Case?

| Requirement | llama.cpp Solution |
|-------------|-------------------|
| **Limited GPU memory** | GGUF quantization reduces model size 4× |
| **Arabic text quality** | Gemma 4 supports Arabic natively; Q4_K_XL preserves token-level accuracy |
| **Deterministic output** | `temperature=0.0` ensures reproducible corrections |
| **No server overhead** | Direct Python bindings — no REST API, no container |
| **Cross-platform** | Same GGUF file runs on CUDA, Metal, Vulkan, or CPU |
| **Batch processing** | Loop over articles with checkpoint/resume |

---

## 6. Checkpoint/Resume Strategy

Since processing hundreds of legal articles is time-consuming, we use a simple JSON-based checkpoint:

```
┌─────────────────┐
│ article_objects │  (OCR extracted, unsorted)
│   [{num, text}] │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           Processing Loop               │
│                                         │
│  for article in article_objects:        │
│    if num in processed:  ◀── skip       │
│      continue                           │
│    corrected = llm(article.text)        │
│    clean_articles.append(corrected)     │
│    save("clean_articles.json")  ◀── save│
│                                         │
└─────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ clean_articles   │
│   .json          │  (persisted after each article)
└──────────────────┘
```

This ensures no work is lost if the process is interrupted mid-batch.

---

## 7. Quick Start

```bash
# Install CUDA-accelerated llama-cpp-python
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124

# Download model
python -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download('unsloth/gemma-4-E2B-it-qat-GGUF',
                        'gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf')
print(path)
"
```

```python
from llama_cpp import Llama

llm = Llama(
    model_path="gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
    n_ctx=16384,        # 16K context window
    n_gpu_layers=-1,    # All layers on GPU
    n_batch=1024,       # Batch processing size
    verbose=False
)

response = llm.create_chat_completion(
    messages=[{"role": "user", "content": "Correct this OCR text: ..."}],
    temperature=0.0,
    max_tokens=2048
)

print(response["choices"][0]["message"]["content"])
```

---

## 8. Trade-offs

| ✅ Advantages | ❌ Limitations |
|--------------|---------------|
| Fits in 4 GB VRAM | Q4 quality slightly below FP16 |
| Single-file GGUF — no sharding | Max context limited by KV cache size |
| No API server needed | ~2–3× slower than vLLM/TGI |
| Checkpoint/resume built-in | Not suitable for streaming/chat use |
| Runs on CPU as fallback | Requires llama-cpp-python build with CUDA |
