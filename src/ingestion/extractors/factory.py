"""Extractor factory – instantiate based on config."""
from pathlib import Path
from typing import Dict, Any
from .base import BaseExtractor
from .pdf_to_text_extractor import PdfToTextExtractor
# Import concrete VLM extractors once implemented
# from .qwen2vl_extractor import Qwen2VLExtractor
# from .cloud_vlm_extractor import CloudVlmExtractor


def create_extractor(config: Dict[str, Any]) -> BaseExtractor:
    """Create an extractor from a configuration dictionary.

    Example config:
        {
            "type": "tesseract",
            "lang": "ara+fra",
            "dpi": 300
        }
        or
        {
            "type": "vlm",
            "model_id": "Qwen/Qwen2-VL-2B-Instruct",
            "dpi": 200
        }
        or
        {
            "type": "cloud_vlm",
            "endpoint_url": "https://...",
            "api_key": "..."
        }
    """
    extractor_type = config.get("type", "pdf_to_text").lower()
    if extractor_type == "pdf_to_text":
        return PdfToTextExtractor(
            use_ocr=config.get("use_ocr", False),
            ocr_dpi=config.get("ocr_dpi", 200),
            ocr_lang=config.get("ocr_lang", "ara"),
        )
    else:
        raise ValueError(f"Unknown extractor type: {extractor_type}")
