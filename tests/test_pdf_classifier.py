"""
Unit tests for src/ingestion/classifiers/pdf_classifier.py

Run with:
    pytest tests/test_pdf_classifier.py -v \
        --cov=src.ingestion.classifiers.pdf_classifier --cov-report=term-missing
"""
import logging
import subprocess
import sys
import pytest
import pandas as pd
from pathlib import Path

from src.ingestion.classifiers.pdf_classifier import (
    classify_pdf,
    classify_directory,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Keys that every result dict must contain
# ---------------------------------------------------------------------------
REQUIRED_KEYS = {
    "file",
    "classification",
    "total_pages",
    "avg_text_length",
    "text_page_ratio",
    "image_page_ratio",
    "processing_status",
    "error_reason",
}

# ---------------------------------------------------------------------------
# classify_pdf — happy paths
# ---------------------------------------------------------------------------


def test_classify_digital_pdf(fixtures_path):
    """A text-only PDF must be classified as 'digital'."""
    result = classify_pdf(fixtures_path / "sample_digital.pdf")
    assert result["classification"] == "digital"
    assert result["processing_status"] == "success"


def test_classify_scanned_pdf(fixtures_path):
    """An image-only PDF must be classified as 'scanned'."""
    result = classify_pdf(fixtures_path / "sample_scanned.pdf")
    assert result["classification"] == "scanned"
    assert result["processing_status"] == "success"


def test_classify_hybrid_pdf(fixtures_path):
    """A mixed PDF must be classified as 'hybrid'."""
    result = classify_pdf(fixtures_path / "sample_hybrid.pdf")
    assert result["classification"] == "hybrid"
    assert result["processing_status"] == "success"


# ---------------------------------------------------------------------------
# classify_pdf — error / edge cases
# ---------------------------------------------------------------------------

def test_classify_corrupted_pdf(fixtures_path):
    """A corrupted PDF must yield classification='error' with a reason."""
    result = classify_pdf(fixtures_path / "sample_corrupted.pdf")
    assert result["classification"] == "error"
    assert result["processing_status"] == "error"
    assert result["error_reason"] != ""


def test_classify_nonexistent_file():
    """Passing a non-existent path (str or Path) must return an error dict."""
    # str input
    result_str = classify_pdf("not_a_real_file.pdf")
    assert result_str["classification"] == "error"
    assert result_str["processing_status"] == "error"
    assert result_str["error_reason"] != ""

    # Path input
    result_path = classify_pdf(Path("also_missing.pdf"))
    assert result_path["classification"] == "error"
    assert result_path["processing_status"] == "error"


def test_classify_empty_pdf(fixtures_path):
    """A PDF with 0 pages must yield classification='empty', status='warning'."""
    result = classify_pdf(fixtures_path / "sample_empty.pdf")
    assert result["classification"] == "empty"
    assert result["processing_status"] == "warning"


# ---------------------------------------------------------------------------
# classify_pdf — result dict structure & types
# ---------------------------------------------------------------------------

def test_output_dict_has_all_fields(fixtures_path):
    """The result dict must contain every required key."""
    result = classify_pdf(fixtures_path / "sample_digital.pdf")
    assert REQUIRED_KEYS.issubset(result.keys()), (
        f"Missing keys: {REQUIRED_KEYS - result.keys()}"
    )


def test_numeric_fields_are_floats(fixtures_path):
    """avg_text_length, text_page_ratio, and image_page_ratio must be floats."""
    result = classify_pdf(fixtures_path / "sample_hybrid.pdf")
    assert isinstance(result["avg_text_length"], float)
    assert isinstance(result["text_page_ratio"], float)
    assert isinstance(result["image_page_ratio"], float)


def test_ratios_are_between_zero_and_one(fixtures_path):
    """Page-ratio fields must be in [0, 1]."""
    result = classify_pdf(fixtures_path / "sample_digital.pdf")
    assert 0.0 <= result["text_page_ratio"] <= 1.0
    assert 0.0 <= result["image_page_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# classify_directory
# ---------------------------------------------------------------------------

def test_classify_directory_creates_csv(tmp_path, fixtures_path):
    """
    classify_directory should write pdf_classification.csv to output_dir
    and return a non-empty DataFrame with one row per PDF.
    """
    pdf_count = len(list(fixtures_path.glob("*.pdf")))
    df = classify_directory(fixtures_path, output_dir=tmp_path)

    csv_path = tmp_path / "pdf_classification.csv"
    assert csv_path.exists(), "CSV file was not created"

    loaded = pd.read_csv(csv_path)
    assert len(loaded) == pdf_count, (
        f"Expected {pdf_count} rows, got {len(loaded)}"
    )
    assert len(df) == pdf_count


def test_classify_directory_no_output_dir(fixtures_path):
    """
    classify_directory without output_dir must still return a DataFrame
    and must NOT create any CSV files.
    """
    df = classify_directory(fixtures_path)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    # No CSV should appear next to the fixtures
    assert not (fixtures_path / "pdf_classification.csv").exists()


def test_classify_directory_empty_dir(tmp_path, caplog):
    """
    classify_directory on a folder with no PDFs must return an empty
    DataFrame and log a warning.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with caplog.at_level("WARNING"):
        df = classify_directory(empty_dir)

    assert df.empty
    assert any(
        "no pdf" in record.message.lower() or "not found" in record.message.lower()
        for record in caplog.records
    ), "Expected a warning about missing PDFs"


def test_classify_directory_str_inputs(tmp_path, fixtures_path):
    """classify_directory must accept plain strings for both arguments."""
    df = classify_directory(str(fixtures_path), output_dir=str(tmp_path))
    assert not df.empty
    assert (tmp_path / "pdf_classification.csv").exists()


def test_classify_directory_dataframe_columns(fixtures_path):
    """The returned DataFrame must include all required columns."""
    df = classify_directory(fixtures_path)
    for col in REQUIRED_KEYS:
        assert col in df.columns, f"Missing column: {col}"


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

def test_setup_logging_returns_root_logger():
    """setup_logging must return the root logger and attach a handler."""
    logger = setup_logging(logging.DEBUG)
    assert logger is logging.getLogger()
    assert len(logger.handlers) >= 1


def test_setup_logging_idempotent():
    """Calling setup_logging twice must not duplicate handlers."""
    setup_logging(logging.INFO)
    handler_count_first = len(logging.getLogger().handlers)
    setup_logging(logging.INFO)
    assert len(logging.getLogger().handlers) == handler_count_first


# ---------------------------------------------------------------------------
# CLI __main__ smoke test
# ---------------------------------------------------------------------------

def test_cli_empty_dir(tmp_path):
    """
    Running the module as a script against an empty directory must exit
    cleanly (returncode 0) even when there are no PDFs.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "src.ingestion.classifiers.pdf_classifier",
            "--raw-dir", str(tmp_path),
            "--output-dir", str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
