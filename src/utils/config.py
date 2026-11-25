from pathlib import Path
from typing import Optional
import yaml


# ─── Config file paths ────────────────────────────────────────────────────────

CONFIG_DIR = Path("config")
CONFIG_PATH = CONFIG_DIR / "config.yaml"
CLEANING_CONFIG_PATH = CONFIG_DIR / "cleaning.yaml"
NORMALIZATION_CONFIG_PATH = CONFIG_DIR / "normalization.yaml"
OCR_CONFIG_PATH = CONFIG_DIR / "ocr_config.yml"
RETRIEVAL_CONFIG_PATH = CONFIG_DIR / "retrieval_config.yml"


# ─── Generic loader ───────────────────────────────────────────────────────────

def load_config(config_path: str | Path = CONFIG_PATH) -> dict:
    """Load a YAML config file and return its contents as a dict.

    Args:
        config_path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dict (empty dict if file missing or empty).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return config


def load_config_optional(config_path: str | Path) -> dict:
    """Load a YAML config file, returning an empty dict if it doesn't exist.

    Args:
        config_path: Path to the YAML file.

    Returns:
        Parsed YAML content or empty dict.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    return load_config(config_path)


# ─── Main config sections ─────────────────────────────────────────────────────

def get_pdf_classifier_config(
    config_path: str | Path = CONFIG_PATH,
) -> dict:
    """Get the PDF classifier configuration section."""
    config = load_config(config_path)

    if "pdf_classifier" not in config:
        raise KeyError("Missing 'pdf_classifier' section in config")

    return config["pdf_classifier"]


def get_embedding_config(
    config_path: str | Path = CONFIG_PATH,
) -> dict:
    """Get the embedding configuration section."""
    config = load_config(config_path)
    return config.get("embedding", {})


# ─── Specialized config loaders ───────────────────────────────────────────────

def get_cleaning_config(config_path: Optional[Path] = None) -> dict:
    """Get the text cleaning configuration from cleaning.yaml."""
    return load_config_optional(config_path or CLEANING_CONFIG_PATH)


def get_normalization_config(config_path: Optional[Path] = None) -> dict:
    """Get the Arabic normalization configuration from normalization.yaml."""
    return load_config_optional(config_path or NORMALIZATION_CONFIG_PATH)


def get_ocr_config(config_path: Optional[Path] = None) -> dict:
    """Get the OCR configuration from ocr_config.yml."""
    return load_config_optional(config_path or OCR_CONFIG_PATH)


def get_retrieval_config(config_path: Optional[Path] = None) -> dict:
    """Get the retrieval configuration from retrieval_config.yml."""
    return load_config_optional(config_path or RETRIEVAL_CONFIG_PATH)
