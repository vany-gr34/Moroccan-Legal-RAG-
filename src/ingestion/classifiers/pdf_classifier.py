import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
import argparse
import logging
import sys

# ----------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------


def setup_logging(level=logging.INFO):
    """Configure root logger with console output and clear formatting."""
    logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# ----------------------------------------------------------------------
# Core classification logic
# ----------------------------------------------------------------------


def classify_pdf(pdf_path, text_threshold: int = 100) -> dict:
    """
    Classify a PDF as 'digital', 'scanned', 'hybrid', or 'error'.

    Args:
        pdf_path: Path (str or Path object) to the PDF file.
        text_threshold: Minimum number of characters per page to consider
                        it text-heavy.

    Returns:
        Dictionary with classification details and metadata.
    """
    logger = logging.getLogger(__name__)
    # Accept both str and Path
    pdf_path = Path(pdf_path)

    result = {
        "file": str(pdf_path),
        "classification": "unknown",
        "total_pages": 0,
        "avg_text_length": 0.0,
        "text_page_ratio": 0.0,
        "image_page_ratio": 0.0,
        "processing_status": "success",
        "error_reason": "",
    }

    if not pdf_path.is_file():
        result["classification"] = "error"
        result["processing_status"] = "error"
        result["error_reason"] = "File not found"
        logger.error(f"File not found: {pdf_path}")
        return result

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        result["classification"] = "error"
        result["processing_status"] = "error"
        result["error_reason"] = f"Failed to open PDF: {e}"
        logger.error(f"Cannot open {pdf_path.name}: {e}")
        return result

    total_pages = len(doc)
    if total_pages == 0:
        result["classification"] = "empty"
        result["processing_status"] = "warning"
        result["error_reason"] = "PDF has no pages"
        logger.warning(f"{pdf_path.name} is empty (0 pages)")
        doc.close()
        return result

    text_per_page = []
    image_per_page = []

    for page_num, page in enumerate(doc, start=1):
        try:
            text = page.get_text()
        except Exception as e:
            logger.debug(
                f"Page {page_num} text extraction error in {pdf_path.name}: {e}"
            )
            text = ""
        text_per_page.append(len(text.strip()))

        try:
            image_count = len(page.get_images(full=True))
        except Exception as e:
            logger.debug(f"Page {page_num} image enumeration error: {e}")
            image_count = 0
        image_per_page.append(image_count)

    doc.close()

    avg_text = sum(text_per_page) / total_pages
    text_heavy_pages = sum(1 for t in text_per_page if t > text_threshold)
    image_heavy_pages = sum(1 for i in image_per_page if i > 0)
    text_page_ratio = text_heavy_pages / total_pages
    image_page_ratio = image_heavy_pages / total_pages

    if text_page_ratio > 0.9:
        classification = "digital"
    elif image_page_ratio > 0.9 and text_page_ratio < 0.1:
        classification = "scanned"
    else:
        classification = "hybrid"

    logger.info(
        f"{pdf_path.name}: {classification} "
        f"(text_ratio={text_page_ratio:.2f}, img_ratio={image_page_ratio:.2f}, "
        f"avg_text={avg_text:.1f} chars/page)"
    )

    result.update({
        "classification": classification,
        "total_pages": total_pages,
        "avg_text_length": round(avg_text, 2),
        "text_page_ratio": round(text_page_ratio, 4),
        "image_page_ratio": round(image_page_ratio, 4),
    })
    return result

# ----------------------------------------------------------------------
# Batch processing
# ----------------------------------------------------------------------


def classify_directory(raw_dir, output_dir=None) -> pd.DataFrame:
    """
    Classify all PDFs in raw_dir.

    Args:
        raw_dir:    Directory containing PDF files (str or Path).
        output_dir: Directory to write pdf_classification.csv into.
                    If None, no CSV is written.

    Returns:
        DataFrame of classification results (empty if no PDFs found).
    """
    logger = logging.getLogger(__name__)
    raw_dir = Path(raw_dir)

    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {raw_dir}")
        return pd.DataFrame()

    logger.info(f"Starting classification of {len(pdf_files)} PDFs")
    results = [classify_pdf(pdf) for pdf in pdf_files]
    df = pd.DataFrame(results)

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / "pdf_classification.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"Saved to {out_path}")

    counts = df["classification"].value_counts().to_dict()
    logger.info(f"Classification complete. Results: {counts} (total {len(df)})")
    return df


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Classify PDFs as digital, scanned, or hybrid.")
    parser.add_argument("--raw-dir", type=str, default="data/raw")
    parser.add_argument("--output-dir", type=str, default="data/interim")
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    args = parser.parse_args()

    setup_logging(getattr(logging, args.log_level.upper()))
    classify_directory(args.raw_dir, args.output_dir)