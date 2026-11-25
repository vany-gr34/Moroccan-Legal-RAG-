.PHONY: test test-all test-classifier test-extractor test-pdf-extractor \
        test-database test-embedder test-config test-short help \
        install lint format clean tui tui-help \
        embed embed-all embed-dry-run embed-clear \
        embed-domain embed-domain-clear

# ─── Default target ──────────────────────────────────────────────────────────

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Testing targets:"
	@echo "  make test              Run all tests (aliases: test-all)"
	@echo "  make test-short        Run tests excluding slow embedder/model loading"
	@echo "  make test-classifier   Test PDF classifier"
	@echo "  make test-extractor    Test PDF block parser / article extractor"
	@echo "  make test-pdf-extractor  Test PdfToTextExtractor"
	@echo "  make test-database     Test database connection and operations"
	@echo "  make test-embedder     Test embedding (local + mocked remote)"
	@echo "  make test-config       Test configuration loading"
	@echo ""
	@echo "TUI (Knowledge Base Manager):"
	@echo "  make tui               Launch the Knowledge Base Manager TUI"
	@echo "  make tui-help          Show keyboard shortcuts for the TUI"
	@echo ""
	@echo "Embedding pipeline:"
	@echo "  make embed-all              Embed all articles into the vector database"
	@echo "  make embed-dry-run          Show what would be processed (no insertion)"
	@echo "  make embed-clear            Re-embed all articles (clears existing data first)"
	@echo "  make embed-domain DOMAIN=x  Embed articles for a single domain"
	@echo "  make embed-domain-clear D=  Re-embed a domain (clears existing data first)"
	@echo ""
	@echo "  (add MAX_CHARS=4000 to any embed target to raise the 2000-char truncation"
	@echo "   limit, or MAX_CHARS=0 to disable truncation entirely)"
	@echo ""
	@echo "Other targets:"
	@echo "  make install           Install dependencies"
	@echo "  make lint              Run flake8 linting"
	@echo "  make format            Check formatting with black"
	@echo "  make clean             Remove __pycache__ and .pytest_cache"

# ─── Embedding pipeline ───────────────────────────────────────────────────────

# Auto-detect venv python, fall back to system python
PYTHON := $(or $(wildcard venv/bin/python), $(wildcard .venv/bin/python), python)
EMBED_SCRIPT = $(PYTHON) scripts/embed_all_articles.py

# Optional max_chars override (default: 2000). Set MAX_CHARS=0 to disable.
ifdef MAX_CHARS
EMBED_FLAGS := --max-chars $(MAX_CHARS)
else
EMBED_FLAGS :=
endif

embed: embed-all

embed-all:
	@echo "Embedding all articles into the vector database..."
	$(EMBED_SCRIPT) $(EMBED_FLAGS)

embed-dry-run:
	@echo "Dry run — showing what would be processed..."
	$(EMBED_SCRIPT) --dry-run --skip-empty $(EMBED_FLAGS)

embed-clear:
	@echo "Re-embedding all articles (clearing existing data)..."
	$(EMBED_SCRIPT) --clear-existing --skip-empty $(EMBED_FLAGS)

embed-domain:
	@if [ -z "$(DOMAIN)" ]; then \
		echo "Usage: make embed-domain DOMAIN=civil"; \
		echo "Valid domains: civil commercial criminal judicial traffic violations companies family"; \
		exit 1; \
	fi
	@echo "Embedding articles for domain: $(DOMAIN)..."
	$(EMBED_SCRIPT) --domains $(DOMAIN) --skip-empty $(EMBED_FLAGS)

embed-domain-clear:
	@if [ -z "$(DOMAIN)" ]; then \
		echo "Usage: make embed-domain-clear DOMAIN=civil"; \
		echo "Valid domains: civil commercial criminal judicial traffic violations companies family"; \
		exit 1; \
	fi
	@echo "Re-embedding domain $(DOMAIN) (clearing existing data)..."
	$(EMBED_SCRIPT) --domains $(DOMAIN) --clear-existing --skip-empty $(EMBED_FLAGS)

# ─── Test runner ─────────────────────────────────────────────────────────────

PYTEST = python -m pytest
TEST_DIR = tests
FLAGS = -v --tb=short

# Run all tests
test: test-all

test-all:
	$(PYTEST) $(TEST_DIR) $(FLAGS)

# Run tests excluding slow embedder model downloads
test-short:
	$(PYTEST) $(TEST_DIR) $(FLAGS) \
		-k "not local_embedder" \
		--ignore=$(TEST_DIR)/test_embedder.py

# Individual test suites
test-classifier:
	$(PYTEST) $(TEST_DIR)/test_pdf_classifier.py $(FLAGS)

test-extractor:
	$(PYTEST) $(TEST_DIR)/test_extractor.py $(FLAGS)

test-pdf-extractor:
	$(PYTEST) $(TEST_DIR)/test_pdf_to_text_extractor.py $(FLAGS)

test-database:
	$(PYTEST) $(TEST_DIR)/test_database.py $(FLAGS)

test-embedder:
	$(PYTEST) $(TEST_DIR)/test_embedder.py $(FLAGS) \
		-k "not real"

test-config:
	$(PYTEST) $(TEST_DIR)/test_config.py $(FLAGS)

# ─── TUI (Knowledge Base Manager) ────────────────────────────────────────────

TUI_APP = python -m tui.app

tui:
	$(TUI_APP)

tui-help:
	@echo "Keyboard shortcuts for the Knowledge Base Manager TUI:"
	@echo ""
	@echo "  q      Quit"
	@echo "  a      Toggle select all / deselect all PDFs"
	@echo "  r      Refresh the PDF file list"
	@echo "  p      Process selected PDFs"
	@echo "  Tab    Move focus between widgets"
	@echo "  Enter  Click a button or select a list item"
	@echo "  ↑/↓    Navigate the PDF list"
	@echo ""
	@echo "Select PDFs by clicking on them in the list."
	@echo "Then press 'Process Selected' or hit 'p'."
	@echo "Use 'Process All' to process all PDFs at once."

# ─── Utility targets ─────────────────────────────────────────────────────────

install:
	pip install -r requirements.txt
	pip install -e .

lint:
	@command -v flake8 >/dev/null 2>&1 || { echo "flake8 not installed. Run: pip install flake8"; exit 1; }
	flake8 src/ tests/ --max-line-length=100

format:
	@command -v black >/dev/null 2>&1 || { echo "black not installed. Run: pip install black"; exit 1; }
	black --check src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf *.egg-info