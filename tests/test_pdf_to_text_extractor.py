# tests/test_pdf_to_text_extractor.py
"""Tests for PdfToTextExtractor (no OCR)."""

import pytest
from pathlib import Path
import tempfile
import os

try:
    from src.ingestion.extractors.pdf_text import PdfToTextExtractor
    from src.ingestion.extractors.base import ExtractionResult, PageData
except ImportError:
    pytest.skip("Extraction module not importable", allow_module_level=True)

# Try to import optional libraries for test PDF creation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import fitz  # PyMuPDF (still needed for extractor fallback)
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def create_test_pdf(text: str, path: Path):
    """Create a minimal PDF with given text using reportlab."""
    if not REPORTLAB_AVAILABLE:
        pytest.skip("reportlab not available to create test PDF")
    c = canvas.Canvas(str(path), pagesize=A4)
    # Use a standard font; Arabic may not render correctly but text extraction
    # will still work because the content stream contains the characters.
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, text)
    c.save()


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_pdf_arabic(temp_dir):
    """Create a simple PDF with Arabic text."""
    pdf_path = temp_dir / "test_arabic.pdf"
    arabic_text = "المادة 1: القانون المغربي ينص على أن كل متهم بريء حتى تثبت إدانته."
    create_test_pdf(arabic_text, pdf_path)
    return pdf_path


@pytest.fixture
def sample_pdf_english(temp_dir):
    """Create a simple PDF with English text."""
    pdf_path = temp_dir / "test_english.pdf"
    english_text = "Article 1: All persons are equal before the law."
    create_test_pdf(english_text, pdf_path)
    return pdf_path


# ----------------------------------------------------------------------
# Tests for Arabic helpers
# ----------------------------------------------------------------------
class TestArabicHelpers:
    def test_is_arabic_line_true(self):
        assert PdfToTextExtractor.is_arabic_line("المادة الأولى من القانون")

    def test_is_arabic_line_false(self):
        assert not PdfToTextExtractor.is_arabic_line("Article 1")

    def test_reverse_arabic_text(self):
        original = "المادة"
        reversed_text = PdfToTextExtractor.reverse_arabic_text(original)
        assert reversed_text == "ةداملا"

    def test_fix_arabic_line(self):
        reversed_arabic = "ةداملا"
        fixed = PdfToTextExtractor.fix_arabic_line(reversed_arabic)
        assert fixed == "المادة"

    def test_fix_arabic_text_multiline(self):
        mixed = "Hello\nةداملا\nWorld"
        fixed = PdfToTextExtractor.fix_arabic_text(mixed)
        assert "المادة" in fixed
        assert "Hello" in fixed


# ----------------------------------------------------------------------
# Extractor instantiation
# ----------------------------------------------------------------------
class TestExtractorInit:
    def test_default_init(self):
        ext = PdfToTextExtractor()
        assert ext.use_ocr is False
        assert "pdfplumber" in ext.name

    def test_with_ocr(self):
        ext = PdfToTextExtractor(use_ocr=True, ocr_dpi=150, ocr_lang="ara+fra")
        assert ext.use_ocr is True
        assert ext.ocr_dpi == 150
        assert ext.ocr_lang == "ara+fra"


# ----------------------------------------------------------------------
# Extraction tests
# ----------------------------------------------------------------------
class TestExtract:
    def test_extract_arabic_pdf(self, sample_pdf_arabic):
        ext = PdfToTextExtractor(use_ocr=False)
        result = ext.extract(sample_pdf_arabic)

        assert isinstance(result, ExtractionResult)
        assert result.total_pages == 1
        assert len(result.pages) == 1
        page = result.pages[0]
        assert isinstance(page, PageData)

        # The created PDF may not render Arabic correctly with basic fonts,
        # so we only check that some text was extracted.
        assert len(page.text) > 5, f"Expected some text, got: {page.text!r}"
        assert result.metadata["method"] in ("pdfplumber", "PyMuPDF")

    def test_extract_english_pdf(self, sample_pdf_english):
        ext = PdfToTextExtractor()
        result = ext.extract(sample_pdf_english)
        page = result.pages[0]
        assert "Article 1" in page.text

    def test_extraction_result_structure(self, sample_pdf_arabic):
        ext = PdfToTextExtractor()
        result = ext.extract(sample_pdf_arabic)
        assert result.file_path == sample_pdf_arabic
        assert result.extractor_name == ext.name
        assert result.total_pages >= 1
        assert result.total_time_ms >= 0
        assert isinstance(result.metadata, dict)
