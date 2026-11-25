"""
Tests for LegalEmbedder (LocalEmbedder + RemoteEmbedder).

Run remote tests (requires Colab service running):
    pytest tests/test_embedder.py -v

Run local tests (requires model download, ~560MB):
    pytest tests/test_embedder.py -v -m "local"

Run mocked tests only (no dependencies):
    pytest tests/test_embedder.py -v -m "not local and not remote"
"""

from src.core.embedding import (
    BaseEmbedder,
    LocalEmbedder,
    RemoteEmbedder,
    create_embedder,
)
import os
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_texts():
    """Sample Arabic legal texts."""
    return [
        "المادة 147 من القانون الجنائي المغربي: كل من ارتكب جريمة السرقة يعاقب بالحبس من سنة إلى خمس سنوات",
        "المادة 172 من مدونة السير: تجاوز السرعة القصوى المسموح بها في المدار الحضري",
        "المادة 48 من مدونة الأسرة: النفقة واجبة على الزوج لزوجته بمجرد الدخول بها",
        "المادة 54 من مدونة التجارة: السجل التجاري يمسك لدى المحكمة التجارية المختصة",
        "المادة 1 من قانون الالتزامات والعقود: الالتزامات تنشأ عن الاتفاقات والتصرفات القانونية",
    ]


@pytest.fixture
def single_text():
    """Single Arabic legal text."""
    return "عقوبة تجاوز السرعة القصوى في المدار الحضري"

# ============================================
# RemoteEmbedder Tests — MOCKED (always run)
# ============================================


class TestRemoteEmbedderMocked:
    """Tests for RemoteEmbedder using mocked HTTP responses.

    These run without any external service.
    """

    @pytest.fixture
    def health_response(self):
        return {
            "status": "ok",
            "model": "intfloat/multilingual-e5-large",
            "device": "cuda",
            "dimension": 1024,
            "gpu_name": "Tesla T4",
        }

    @pytest.fixture
    def embed_response(self):
        return {
            "embeddings": [
                [0.01] * 1024,
                [0.02] * 1024,
                [0.03] * 1024,
            ],
            "dimension": 1024,
            "count": 3,
            "time_ms": 45.3,
        }

    @patch("src.core.embedding.requests.get")
    def test_initialization_success(self, mock_get, health_response):
        """RemoteEmbedder initializes when health check passes."""
        mock_resp = Mock()
        mock_resp.json.return_value = health_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        embedder = RemoteEmbedder(service_url="http://fake-url.local")

        assert embedder.mode == "remote"
        assert embedder.dimension == 1024

    @patch("src.core.embedding.requests.get")
    def test_initialization_failure_raises(self, mock_get):
        """RemoteEmbedder raises ConnectionError when service unreachable."""
        mock_get.side_effect = Exception("Connection refused")

        with pytest.raises(ConnectionError, match="unreachable"):
            RemoteEmbedder(service_url="http://fake-url.local")

    @patch("src.core.embedding.requests.get")
    @patch("src.core.embedding.requests.post")
    def test_embed_returns_correct_shape(
        self, mock_post, mock_get, health_response, embed_response
    ):
        """Remote embed returns correctly shaped numpy array."""
        mock_health = Mock()
        mock_health.json.return_value = health_response
        mock_get.return_value = mock_health

        mock_embed = Mock()
        mock_embed.json.return_value = embed_response
        mock_post.return_value = mock_embed

        embedder = RemoteEmbedder(service_url="http://fake-url.local")
        result = embedder.embed(["text1", "text2", "text3"])

        assert result.shape == (3, 1024)
        assert result.dtype == np.float32

    @patch("src.core.embedding.requests.get")
    @patch("src.core.embedding.requests.post")
    def test_embed_single_string(self, mock_post, mock_get, health_response):
        """Remote embed handles a single string (not list)."""
        mock_health = Mock()
        mock_health.json.return_value = health_response
        mock_get.return_value = mock_health

        single_response = {
            "embeddings": [[0.01] * 1024],
            "dimension": 1024,
            "count": 1,
            "time_ms": 12.5,
        }
        mock_embed = Mock()
        mock_embed.json.return_value = single_response
        mock_post.return_value = mock_embed

        embedder = RemoteEmbedder(service_url="http://fake-url.local")
        result = embedder.embed("single text")

        assert result.shape == (1, 1024)

    @patch("src.core.embedding.requests.get")
    def test_embed_empty_list(self, mock_get, health_response):
        """Remote embed returns empty array for empty list."""
        mock_health = Mock()
        mock_health.json.return_value = health_response
        mock_get.return_value = mock_health

        embedder = RemoteEmbedder(service_url="http://fake-url.local")
        result = embedder.embed([])

        assert result.size == 0

    @patch("src.core.embedding.requests.get")
    @patch("src.core.embedding.requests.post")
    def test_embed_single_returns_1d(self, mock_post, mock_get, health_response):
        """embed_single returns 1D array."""
        mock_health = Mock()
        mock_health.json.return_value = health_response
        mock_get.return_value = mock_health

        single_response = {
            "embeddings": [[0.01] * 1024],
            "dimension": 1024,
            "count": 1,
            "time_ms": 12.5,
        }
        mock_embed = Mock()
        mock_embed.json.return_value = single_response
        mock_post.return_value = mock_embed

        embedder = RemoteEmbedder(service_url="http://fake-url.local")
        result = embedder.embed_single("text")

        assert result.shape == (1024,)
        assert result.ndim == 1

    @patch("src.core.embedding.requests.get")
    def test_initialization_failure_raises(self, mock_get):
        """RemoteEmbedder raises ConnectionError when service unreachable."""
        import requests as req_module
        mock_get.side_effect = req_module.exceptions.ConnectionError(
            "Connection refused")

        with pytest.raises(ConnectionError, match="unreachable"):
            RemoteEmbedder(service_url="http://fake-url.local")


# ============================================
# RemoteEmbedder Tests — REAL (always run if URL set)
# ============================================

class TestRemoteEmbedderReal:
    """Tests against the real Colab embedding service.

    Requires:
        - Colab notebook running
        - EMBEDDING_SERVICE_URL set in .env
    """

    @pytest.fixture
    def service_url(self):
        """Get service URL from environment."""
        url = os.getenv("EMBEDDING_SERVICE_URL")
        if not url:
            pytest.skip("EMBEDDING_SERVICE_URL not set in .env")
        return url

    @pytest.fixture
    def remote(self, service_url):
        """Create real remote embedder."""
        return RemoteEmbedder(service_url=service_url)

    def test_health_check(self, remote):
        """Service responds to health check with correct info."""
        assert remote.mode == "remote"
        assert remote.dimension == 1024

    def test_embed_single_arabic(self, remote):
        """Embed a single Arabic legal text."""
        result = remote.embed("المادة 147 من القانون الجنائي المغربي")
        assert result.shape == (1, 1024)
        assert not np.allclose(result, 0, atol=1e-6)

    def test_embed_batch_arabic(self, remote, sample_texts):
        """Embed a batch of Arabic legal texts."""
        result = remote.embed(sample_texts)
        assert result.shape == (5, 1024)
        assert not np.allclose(result, 0, atol=1e-6)

    def test_normalized_embeddings(self, remote):
        """Remote embeddings are L2-normalized (unit vectors)."""
        result = remote.embed("اختبار التطبيع للنماذج")
        for i in range(len(result)):
            norm = np.linalg.norm(result[i])
            assert np.isclose(norm, 1.0, atol=0.01), f"Norm = {norm:.6f}"

    def test_semantic_similarity(self, remote):
        """Similar texts have higher cosine similarity."""
        criminal_1 = "السرقة يعاقب عليها القانون بالحبس"
        criminal_2 = "عقوبة السارق تصل إلى خمس سنوات حبسا"
        traffic = "تجاوز السرعة القصوى في الطريق السيار"

        emb_c1 = remote.embed_single(criminal_1)
        emb_c2 = remote.embed_single(criminal_2)
        emb_t = remote.embed_single(traffic)

        sim_criminal = float(np.dot(emb_c1, emb_c2))
        sim_cross = float(np.dot(emb_c1, emb_t))

        assert sim_criminal > sim_cross, (
            f"Criminal similarity ({sim_criminal:.4f}) should exceed "
            f"cross-domain similarity ({sim_cross:.4f})"
        )

    def test_deterministic(self, remote, single_text):
        """Same input produces identical embeddings."""
        e1 = remote.embed_single(single_text)
        e2 = remote.embed_single(single_text)
        assert np.allclose(e1, e2, atol=1e-6)

    def test_string_vs_list_consistency(self, remote, single_text):
        """embed(str) and embed([str]) give same result."""
        from_str = remote.embed(single_text)
        from_list = remote.embed([single_text])
        assert np.allclose(from_str, from_list, atol=1e-6)

    def test_french_text(self, remote):
        """French legal text produces valid embedding."""
        french = "Article 147 du Code pénal marocain : le vol est puni d'emprisonnement"
        result = remote.embed(french)
        assert result.shape == (1, 1024)
        assert not np.allclose(result, 0, atol=1e-6)

    def test_mixed_arabic_french(self, remote):
        """Mixed Arabic-French text produces valid embedding."""
        mixed = "المادة 147 du Code pénal: العقوبة هي l'emprisonnement"
        result = remote.embed(mixed)
        assert result.shape == (1, 1024)
        assert not np.allclose(result, 0, atol=1e-6)

    def test_large_batch(self, remote):
        """Service handles 50 texts in one request."""
        texts = ["نص قانوني للاختبار"] * 50
        result = remote.embed(texts)
        assert result.shape == (50, 1024)

    def test_latency_single(self, remote):
        """Single embedding returns quickly."""
        start = time.time()
        _ = remote.embed("اختبار السرعة")
        elapsed = time.time() - start
        assert elapsed < 5.0, f"Single embedding took {elapsed:.1f}s"

    def test_latency_batch(self, remote):
        """Batch of 20 texts returns in reasonable time."""
        texts = ["اختبار الأداء"] * 20
        start = time.time()
        result = remote.embed(texts)
        elapsed = time.time() - start
        assert result.shape == (20, 1024)
        assert elapsed < 10.0, f"Batch of 20 took {elapsed:.1f}s"


# ============================================
# LocalEmbedder Tests — DISABLED by default
# ============================================

@pytest.mark.local
class TestLocalEmbedder:
    """Tests for LocalEmbedder.

    Disabled by default. To run:
        pytest tests/test_embedder.py -v -m "local"

    Requires:
        - sentence-transformers installed
        - ~560MB disk space for multilingual-e5-large
        - ~2GB RAM for model inference
    """

    @pytest.fixture
    def local(self):
        return LocalEmbedder()

    def test_initialization(self, local):
        assert local.mode == "local"
        assert local._model is None  # Lazy loading

    def test_dimension(self, local):
        assert local.dimension == 1024

    def test_embed_single(self, local):
        result = local.embed("عقوبة تجاوز السرعة القصوى في المدار الحضري")
        assert result.shape == (1, 1024)
        assert result.dtype == np.float32

    def test_embed_batch(self, local):
        texts = [
            "المادة 147 من القانون الجنائي",
            "المادة 172 من مدونة السير",
            "المادة 48 من مدونة الأسرة",
            "المادة 54 من مدونة التجارة",
            "المادة 1 من قانون الالتزامات والعقود",
        ]
        result = local.embed(texts)
        assert result.shape == (5, 1024)

    def test_embed_empty_list(self, local):
        result = local.embed([])
        assert result.size == 0

    def test_embed_single_1d(self, local):
        result = local.embed_single("اختبار")
        assert result.shape == (1024,)
        assert result.ndim == 1

    def test_normalized(self, local):
        texts = ["المادة 147", "المادة 172", "المادة 48"]
        result = local.embed(texts)
        for i in range(len(texts)):
            norm = np.linalg.norm(result[i])
            assert np.isclose(norm, 1.0, atol=0.01)

    def test_semantic_similarity(self, local):
        criminal_1 = "السرقة يعاقب عليها القانون بالحبس"
        criminal_2 = "عقوبة السارق تصل إلى خمس سنوات حبسا"
        traffic = "تجاوز السرعة القصوى في الطريق السيار"

        emb_c1 = local.embed_single(criminal_1)
        emb_c2 = local.embed_single(criminal_2)
        emb_t = local.embed_single(traffic)

        sim_criminal = float(np.dot(emb_c1, emb_c2))
        sim_cross = float(np.dot(emb_c1, emb_t))

        assert sim_criminal > sim_cross

    def test_deterministic(self, local):
        text = "عقوبة تجاوز السرعة"
        e1 = local.embed_single(text)
        e2 = local.embed_single(text)
        assert np.allclose(e1, e2, atol=1e-6)

    def test_french_text(self, local):
        french = "Article 147 du Code pénal marocain"
        result = local.embed(french)
        assert result.shape == (1, 1024)

    def test_mixed_arabic_french(self, local):
        mixed = "المادة 147 du Code pénal"
        result = local.embed(mixed)
        assert result.shape == (1, 1024)
# ============================================
# Factory Function Tests (always run)
# ============================================


class TestCreateEmbedder:
    """Tests for create_embedder factory function."""

    def test_creates_local_when_no_url(self, monkeypatch):
        """Returns LocalEmbedder when no URL configured."""
        monkeypatch.delenv("EMBEDDING_SERVICE_URL", raising=False)
        embedder = create_embedder()
        assert embedder.mode == "local"
        assert isinstance(embedder, LocalEmbedder)

    def test_creates_local_when_url_empty(self, monkeypatch):
        """Returns LocalEmbedder when URL is empty string."""
        monkeypatch.setenv("EMBEDDING_SERVICE_URL", "")
        embedder = create_embedder()
        assert embedder.mode == "local"

    @patch("src.core.embedding.RemoteEmbedder.__init__")
    def test_attempts_remote_when_url_set(self, mock_init, monkeypatch):
        """Tries RemoteEmbedder when URL is configured."""
        mock_init.return_value = None
        monkeypatch.setenv("EMBEDDING_SERVICE_URL", "http://fake.local")
        create_embedder()
        mock_init.assert_called_once()

    @patch("src.core.embedding.RemoteEmbedder.__init__")
    def test_falls_back_to_local(self, mock_init, monkeypatch):
        """Falls back to LocalEmbedder when remote is unreachable."""
        mock_init.side_effect = ConnectionError("Unreachable")
        monkeypatch.setenv("EMBEDDING_SERVICE_URL", "http://fake.local")
        embedder = create_embedder()
        assert embedder.mode == "local"
        assert isinstance(embedder, LocalEmbedder)


# ============================================
# Interface Compliance Tests (always run)
# ============================================

class TestInterfaceCompliance:
    """Verify both implementations conform to BaseEmbedder."""

    def test_local_is_base_embedder(self):
        assert issubclass(LocalEmbedder, BaseEmbedder)

    def test_remote_is_base_embedder(self):
        assert issubclass(RemoteEmbedder, BaseEmbedder)

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            BaseEmbedder()
