# Architecture Microservices Colab + Fallback Local

> Utilisation de **Google Colab** comme backend GPU distant pour les tâches lourdes
> (embedding et génération LLM), avec **fallback automatique** sur CPU local via
> une **classe abstraite** et un **pattern Factory**.

---

## 1. Problématique

### 1.1 Contrainte Matérielle

Le projet doit exécuter deux modèles d'IA lourds :

| Service | Modèle | Taille | VRAM nécessaire | CPU alternatif |
|---------|--------|--------|-----------------|----------------|
| **Embedding** | `intfloat/multilingual-e5-large` (1024d) | ~560M params | ~2 GB GPU | ~10 textes/s sur CPU |
| **Génération LLM** | `Qwen2.5-7B-Instruct` (via Colab) | ~7B params | ~14 GB GPU | Impossible (trop lent) |

La machine locale n'a **pas de GPU** — ou un GPU trop modeste. La solution :
utiliser **Google Colab** (Tesla T4 / V100 gratuit) comme serveur GPU distant.

### 1.2 Défis

| Défi | Solution |
|------|----------|
| Colab n'a pas d'IP publique | Tunnel Cloudflare (trycloudflare.com) |
| Le notebook Colab peut s'arrêter | Détection de connexion + fallback auto |
| Pas de GPU disponible | Mode CPU local dégradé mais fonctionnel |
| Deux services (embedding + LLM) | Pattern abstrait unifié + Factory |

---

## 2. Architecture Globale

```
┌──────────────────────────────────────────────────────────────────────┐
│                   ARCHITECTURE COLAS MICROSERVICES                     │
│                                                                      │
│                        ┌──────────────────────┐                      │
│                        │   Google Colab (T4)   │                      │
│                        │                      │                      │
│                        │  ┌────────────────┐  │                      │
│                        │  │ Embedding       │  │                      │
│                        │  │ Service         │  │  FastAPI :8000       │
│                        │  │ BGE-M3 / E5     │  │                      │
│                        │  └────────┬───────┘  │                      │
│                        │           │           │                      │
│                        │  ┌────────▼───────┐  │                      │
│                        │  │ LLM Service     │  │  FastAPI :8001       │
│                        │  │ Qwen 2.5 7B     │  │                      │
│                        │  └────────────────┘  │                      │
│                        │                      │                      │
│                        │  ┌────────────────┐  │                      │
│                        │  │ Cloudflared     │  │  Tunnel trycloudflare│
│                        │  │ Tunnel Agent    │──┼── http://xxx.try... │
│                        │  └────────────────┘  │                      │
│                        └──────────┬───────────┘                      │
│                                   │ HTTPS                            │
│                                   ▼                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    Machine Locale                                │  │
│  │                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐    │  │
│  │  │              Factory (create_embedder / create_llm)       │    │  │
│  │  │                                                         │    │  │
│  │  │  EMBEDDING_SERVICE_URL défini ? ───► OUI ──► Remote      │    │  │
│  │  │                        │                               │    │   │
│  │  │                       NON                              │    │  │
│  │  │                        ▼                               │    │  │
│  │  │                   LocalEmbedder (CPU)                   │    │  │
│  │  │                   avec modèle de fallback               │    │  │
│  │  └─────────────────────────────────────────────────────────┘    │  │
│  │                                                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐    │  │
│  │  │  API Locale (FastAPI)       ┌──────────────────────┐    │    │  │
│  │  │  POST /ask                  │  PostgreSQL 16       │    │    │  │
│  │  │  POST /search               │  + pgvector          │    │    │  │
│  │  │  POST /embed                │  (Docker)            │    │    │  │
│  │  │                             └──────────────────────┘    │    │  │
│  │  └─────────────────────────────────────────────────────────┘    │  │
│  │                                                                  │  │
│  │  Interfaces utilisateur :                                        │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐                    │  │
│  │    │  Web     │  │   TUI    │  │   CLI    │                    │  │
│  │    │  Svelte  │  │  Textual  │  │  Python  │                    │  │
│  │    └──────────┘  └──────────┘  └──────────┘                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.1 Flux d'une Requête

```
Question Utilisateur
      │
      ▼
┌─────────────────┐
│  API Locale      │
│  POST /ask       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Hybrid Search   │────▶│  pgvector (local) │────▶│  Top-K Articles │
│  (local)         │     │  + BM25           │     │                │
└─────────────────┘     └──────────────────┘     └────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│  create_llm() → Factory                                      │
│                                                              │
│  ┌─────────────┐          ┌─────────────────────────────┐   │
│  │ LLM_URL set │──OUI──▶  │ RemoteLLM                    │   │
│  │             │          │  POST https://xxx.trycloud… │   │
│  │             │          │  /generate                   │   │
│  │             │          │  → Qwen 2.5 7B sur T4 GPU   │   │
│  ├─────────────┤          └─────────────────────────────┘   │
│  │ LLM_URL set │──NON──▶  │ ⚠️ Erreur (pas de LLM local)   │
│  │             │          │ (Gemma 4 local à implémenter)  │
│  └─────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Réponse        │
│  Juridique      │
└─────────────────┘
```

---

## 3. Pattern : Classe Abstraite (BaseEmbedder / BaseLLM)

### 3.1 Principe

Une classe abstraite définit **l'interface commune** que toutes les
implémentations (locale et distante) doivent respecter. Le code client
(API, ingestion, TUI) **ne sait pas** s'il parle à un backend local ou distant.

### 3.2 Interface Embedding

```python
# src/core/embedding.py

from abc import ABC, abstractmethod
from typing import Union, List

class BaseEmbedder(ABC):
    """Interface commune pour tous les embedders (local & remote)."""

    @abstractmethod
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Génère les embeddings pour un ou plusieurs textes."""
        pass

    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Génère l'embedding pour un seul texte."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension des vecteurs (ex: 1024)."""
        pass

    @property
    @abstractmethod
    def mode(self) -> str:
        """'local' ou 'remote'."""
        pass
```

### 3.3 Interface LLM

```python
# src/generation/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class GenerationResult:
    response: str
    tokens_generated: int
    generation_time_ms: float
    model_name: str

class BaseLLM(ABC):
    """Interface commune pour tous les générateurs LLM."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> GenerationResult:
        """Génère une réponse."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom lisible du modèle."""
        pass
```

---

## 4. Pattern : Factory

### 4.1 Factory pour l'Embedding

```python
# src/core/embedding.py (create_embedder)

def create_embedder(
    service_url: str = None,
    model_name: str = None,
) -> BaseEmbedder:
    """
    Crée l'embedder approprié selon la configuration.

    Stratégie :
    1. Si EMBEDDING_SERVICE_URL est défini → tente RemoteEmbedder
    2. Si la connexion distante échoue → log warning + fallback local
    3. Sinon → LocalEmbedder avec modèle de secours
    """
    service_url = (
        service_url
        or os.getenv("EMBEDDING_SERVICE_URL")
        or embed_config.get("service_url")
    )

    if service_url and service_url.strip():
        try:
            return RemoteEmbedder(service_url=service_url)
        except ConnectionError:
            logger.warning("→ Fallback vers embedder local")

    return LocalEmbedder(model_name=model_name or "intfloat/multilingual-e5-large")
```

### 4.2 Factory pour le LLM

```python
# src/generation/factory.py

def create_llm(service_url: str = None) -> BaseLLM:
    """
    Crée le LLM approprié selon la configuration.

    Stratégie :
    1. Si LLM_SERVICE_URL est défini → RemoteLLM
    2. Sinon → erreur (pas de LLM local pour l'instant)
    """
    service_url = service_url or os.getenv("LLM_SERVICE_URL")

    if not service_url:
        raise ValueError(
            "LLM_SERVICE_URL non défini. "
            "Exemple : LLM_SERVICE_URL=https://xxx.trycloudflare.com"
        )

    return RemoteLLM(service_url=service_url)
```

### 4.3 Arbre de Décision

```
create_embedder()
    │
    ├── EMBEDDING_SERVICE_URL défini ?
    │       │
    │       ├── OUI → RemoteEmbedder (Colab GPU)
    │       │         └── Échec connexion ?
    │       │               └── OUI → LocalEmbedder (CPU)
    │       │
    │       └── NON → LocalEmbedder (CPU)
    │
    └── Retourne BaseEmbedder (le client ne voit pas la différence)


create_llm()
    │
    ├── LLM_SERVICE_URL défini ?
    │       │
    │       ├── OUI → RemoteLLM (Colab GPU, Qwen 2.5 7B)
    │       │
    │       └── NON → ValueError
    │                 (Gemma 4 local à brancher ici)
    │
    └── Retourne BaseLLM (interface unifiée)
```

---

## 5. Implémentations Concrètes

### 5.1 LocalEmbedder

```python
class LocalEmbedder(BaseEmbedder):
    """Embedding sur CPU local — lent mais toujours disponible."""

    def __init__(self, model_name="intfloat/multilingual-e5-large"):
        self._model_name = model_name
        self._model = None   # Chargement paresseux (lazy)

    def _load_model(self):
        """Charge le modèle SentenceTransformer au premier appel."""
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_name)

    def embed(self, texts):
        self._load_model()
        return self._model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

    @property
    def mode(self): return "local"

    @property
    def dimension(self): return 1024
```

**Caractéristiques :**
- Chargement *lazy* — le modèle n'occupe la RAM que si utilisé
- ~10 textes/seconde sur CPU
- 2 GB de RAM
- Fonctionne sans internet (hors-ligne)

### 5.2 RemoteEmbedder

```python
class RemoteEmbedder(BaseEmbedder):
    """Embedding via Colab GPU — rapide mais nécessite une connexion."""

    def __init__(self, service_url: str, timeout: int = 300):
        self._service_url = service_url.rstrip("/")
        self._health_check()  # Vérifie la connexion à l'initialisation

    def embed(self, texts, batch_size=32):
        resp = requests.post(
            f"{self._service_url}/embed",
            json={"texts": texts, "batch_size": batch_size},
            timeout=300,
        )
        return np.array(resp.json()["embeddings"])

    @property
    def mode(self): return "remote"

    @property
    def dimension(self): return 1024
```

**Caractéristiques :**
- ~500 textes/seconde sur T4 GPU
- 0 VRAM utilisée localement
- Nécessite le notebook Colab allumé

### 5.3 RemoteLLM

```python
class RemoteLLM(BaseLLM):
    """Génération LLM via Colab GPU — Qwen2.5-7B-Instruct."""

    def __init__(self, service_url: str, timeout: int = 120):
        self._service_url = service_url.rstrip("/")
        self._health_check()

    def generate(self, prompt, max_tokens=1024, temperature=0.3):
        resp = requests.post(
            f"{self._service_url}/generate",
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=120,
        )
        data = resp.json()
        return GenerationResult(
            response=data["response"],
            tokens_generated=data.get("tokens_generated", 0),
            generation_time_ms=data.get("time_ms", 0),
            model_name="Qwen2.5-7B-Instruct",
        )

    @property
    def name(self): return f"Remote LLM ({self._service_url})"
```

---

## 6. Côté Colab : Microservices GPU

### 6.1 Notebook Embedding (`notebooks/02_embedding_colab_api.ipynb`)

```
┌────────────────────────────────────────────────────────────────┐
│                COLAB — EMBEDDING SERVICE                         │
│                                                                │
│  1. pip install fastapi uvicorn sentence-transformers           │
│  2. wget cloudflared (tunnel client)                           │
│  3. Load model: BAAI/bge-m3 sur T4 GPU                        │
│  4. Start FastAPI :8000                                        │
│  5. Start cloudflared → tunnel → public URL                    │
│  6. Affiche: ✅ PUBLIC TUNNEL URL: https://xxx.trycloudflare.. │
│                                                                │
│  Endpoints exposés :                                           │
│    GET  /health   → {"status": "ok", "model": "bge-m3"}        │
│    POST /embed    → {"embeddings": [...], "dimension": 1024}   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Notebook LLM (`notebooks/07_llm_api_colab_qwen2_5.ipynb`)

```
┌────────────────────────────────────────────────────────────────┐
│                COLAB — LLM SERVICE                               │
│                                                                │
│  1. pip install transformers torch accelerate                  │
│  2. wget cloudflared                                           │
│  3. Load model: Qwen2.5-7B-Instruct (quantisé en 4-bit)       │
│  4. Start FastAPI :8001                                        │
│  5. Start cloudflared → tunnel → public URL                    │
│  6. Affiche: ✅ PUBLIC TUNNEL URL: https://yyy.trycloudflare.. │
│                                                                │
│  Endpoints exposés :                                           │
│    GET  /health    → {"status": "ok", "model": "Qwen2.5-7B"}  │
│    POST /generate  → {"response": "...", "tokens_generated": N}│
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 6.3 Cloudflare Tunnel

```bash
# Côté Colab — une seule commande
./cloudflared tunnel --url http://localhost:8000

# Sortie :
# 2025/01/15 10:30:00 +00:00 INF
#   https://grand-otters-smooth.trycloudflare.com
#   -> http://localhost:8000
```

**Avantages du tunnel :**
- Pas de configuration DNS
- Pas de port forwarding
- Chiffrement HTTPS automatique
- Fonctionne même derrière un NAT / proxy Colab
- Nouvelle URL aléatoire à chaque démarrage

---

## 7. Configuration et Déploiement

### 7.1 Fichier `.env`

```bash
# --- Service d'Embedding (Colab GPU) ---
EMBEDDING_SERVICE_URL=https://grand-otters-smooth.trycloudflare.com

# --- Service LLM (Colab GPU) ---
LLM_SERVICE_URL=https://cool-wombats-eager.trycloudflare.com

# --- Base de données locale ---
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=legal_rag
POSTGRES_USER=legal_rag_user
POSTGRES_PASSWORD=legal_rag_pass
```

### 7.2 Config YAML

```yaml
# config/config.yaml
embedding:
  model_name: BAAI/bge-m3        # Modèle de fallback local
  service_url: ""                 # Priorité à EMBEDDING_SERVICE_URL
```

### 7.3 Workflow Typique

```
┌──────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW QUOTIDIEN                                 │
│                                                                      │
│  1. docker compose up -d          # PostgreSQL local                  │
│  2. Ouvrir Colab → Embedding      # Démarrer le service embedding    │
│  3. Copier l'URL du tunnel        # Dans .env                        │
│  4. Ouvrir Colab → LLM            # Démarrer le service LLM          │
│  5. Copier l'URL du tunnel        # Dans .env                        │
│  6. python scripts/embed_all.py   # Indexation (utilise Colab)       │
│  7. uvicorn src.main:app          # API locale                       │
│                                                                      │
│  Résultat : GPU T4 gratuit pour l'embedding et le LLM               │
│             sans consommer de ressources locales.                    │
│                                                                      │
│  En cas d'arrêt de Colab :                                           │
│    → L'embedding tombe en mode CPU (lent mais fonctionnel)           │
│    → Le LLM remonte une erreur — relancer le notebook                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.4 Gestion des Erreurs et Fallback

```
 RemoteEmbedder.embed()
      │
      ├── Succès → Retourne les embeddings
      │
      └── Échec (Timeout / ConnectionError)
            │
            ├── Log: "Remote embedding failed: {reason}"
            │
            └── Exception remontée à l'appelant
                  │
                  └── IngestionEmbedder peut :
                        ├── Réessayer (batch suivant)
                        └── Arrêter l'indexation (mode dégradé)

─────────────────────────────────────────────────────────────

 create_embedder()
      │
      ├── Remote impossible → Automatiquement LocalEmbedder
      │                        (transparent pour l'appelant)
      │
      └── Toujours un fallback fonctionnel
```

---

## 8. Comparaison Local vs Remote

| Critère | Local (CPU) | Remote (Colab T4) |
|---------|-------------|-------------------|
| **Vitesse embedding** | ~10 textes/s | ~500 textes/s |
| **VRAM utilisée** | 0 GB | 0 GB (côté local) |
| **RAM utilisée** | ~2 GB | ~50 MB |
| **Dépendance internet** | Non | Oui |
| **Coût** | Gratuit | Gratuit |
| **Disponibilité** | 100% | Dépend de Colab (limite de 12h) |
| **Modèle LLM possible** | Aucun (trop lent) | Qwen 2.5 7B / Gemma 4 |
| **Mise en place** | Aucune | Notebook + tunnel |

---

## 9. Arbre des Fichiers

```
src/
├── core/
│   └── embedding.py          ← Interface BaseEmbedder
│                                + LocalEmbedder
│                                + RemoteEmbedder
│                                + create_embedder() (Factory)
│
├── generation/
│   ├── base.py               ← Interface BaseLLM
│   ├── factory.py            ← create_llm() (Factory)
│   └── remote_llm.py         ← RemoteLLM (Colab)
│
└── ingestion/
    └── embedder.py           ← IngestionEmbedder (wrapper batch)

notebooks/
├── 02_embedding_colab_api.ipynb   ← Service embedding sur Colab
├── 04_ocr_service_colab.ipynb     ← Service OCR sur Colab
└── 07_llm_api_colab_qwen2_5.ipynb ← Service LLM sur Colab

config/
└── config.yaml                    ← Configuration embedding

docs/Services/
└── Embedding-Service.md           ← Documentation dédiée
```

---

## 10. Résumé

```
┌─────────────────────────────────────────────────────────────────┐
│                      POINTS CLÉS                                 │
│                                                                 │
│  1. Colab comme microservice GPU                                 │
│     Un notebook = un service FastAPI + Cloudflare Tunnel         │
│     Pas de déploiement Kubernetes, pas de VM cloud payante       │
│                                                                 │
│  2. Classe abstraite (BaseEmbedder / BaseLLM)                    │
│     Interface commune → le code client ne change jamais         │
│     Que ce soit local ou distant, l'appel est le même           │
│                                                                 │
│  3. Factory (create_embedder / create_llm)                       │
│     Décision automatique basée sur :                             │
│       • Variable d'environnement (EMBEDDING_SERVICE_URL)         │
│       • Disponibilité du service distant                         │
│       • Fallback automatique vers le CPU local                   │
│                                                                 │
│  4. Fallback transparent                                         │
│     Si Colab est injoignable → embedding CPU automatique         │
│     L'utilisateur ne voit pas la différence                      │
│                                                                 │
│  5. Zéro infrastructure cloud payante                            │
│     Tout le calcul GPU = notebooks Colab gratuits                │
│     Tunnel Cloudflare = gratuit (quick tunnels)                  │
│     Stockage = PostgreSQL dans Docker local                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
