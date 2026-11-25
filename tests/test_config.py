from src.utils.config import (
    load_config,
    get_pdf_classifier_config,
)


def test_load_config():
    config = load_config()

    assert isinstance(config, dict)


def test_pdf_classifier_section():
    config = get_pdf_classifier_config()

    assert "text_threshold" in config
    assert "text_page_ratio" in config
    assert "image_page_ratio" in config