"""
EasyOCR client for Moroccan Legal RAG.

Calls the Colab GPU EasyOCR service via Cloudflare Tunnel.
"""

import os
import time
import base64
import logging
from io import BytesIO
from typing import Union, List
from pathlib import Path

import requests
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class EasyOCRClient:
    """Client for remote EasyOCR service running on Colab GPU."""

    def __init__(self, service_url: str = None):
        self.service_url = (service_url or os.getenv(
            "EASYOCR_SERVICE_URL", "")).rstrip("/")
        if not self.service_url:
            raise ValueError("EASYOCR_SERVICE_URL not set")

        self._health_check()

    def _health_check(self):
        try:
            resp = requests.get(f"{self.service_url}/health", timeout=10)
            resp.raise_for_status()
            health = resp.json()
            logger.info(f"EasyOCR service: {health.get('gpu_name', 'unknown')} | "
                        f"Languages: {health.get('languages', [])}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"EasyOCR service unreachable: {e}")

    def _image_to_base64(self, image: Image.Image) -> str:
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def ocr(self, image: Image.Image, correct_text: bool = True) -> dict:
        """Run OCR on a PIL image."""
        img_b64 = self._image_to_base64(image)

        start = time.time()
        resp = requests.post(
            f"{self.service_url}/ocr",
            json={"image_base64": img_b64, "correct_text": correct_text},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        elapsed = time.time() - start
        logger.debug(f"OCR: {data['total_chars']} chars in {elapsed:.1f}s "
                     f"(server: {data['time_ms']:.0f}ms)")

        return data

    def ocr_pdf_page(self, pdf_path: Path, page_num: int = 0, dpi: int = 300) -> dict:
        """OCR a specific page from a PDF file."""
        from pdf2image import convert_from_path

        images = convert_from_path(
            pdf_path, dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
        if not images:
            raise ValueError(
                f"No images extracted from {pdf_path} page {page_num}")

        return self.ocr(images[0])
