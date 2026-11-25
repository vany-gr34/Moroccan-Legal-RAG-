from src.core.block_parser import PDFBlockParser


def test_normalize_text_improves_arabic_readability():
    raw = "القسم األول : الخطبة والزواج"
    normalized = PDFBlockParser.normalize_text(raw)
    assert normalized == "القسم الأول: الخطبة والزواج"


def test_normalize_text_adds_space_between_marker_and_number():
    assert PDFBlockParser.normalize_text("المادة1") == "المادة 1"


def test_is_article_start_handles_quotes_and_blocks_numbered_list_items():
    assert PDFBlockParser.is_article_start(
        "«الفصل 490 - إذا تبين من المناقشات")
    assert not PDFBlockParser.is_article_start("7- المادة733 من القانون")


def test_build_articles_groups_body_until_next_article():
    pages = [
        {
            "page_number": 9,
            "blocks": [
                {"index": 6, "text": "المادة1",
                    "type": "text", "bbox": [0, 0, 0, 0]},
                {"index": 7, "text": "يطلق على هذا القانون اسم مدونة الأسرة",
                    "type": "text", "bbox": [0, 0, 0, 0]},
                {"index": 8, "text": "المادة2",
                    "type": "text", "bbox": [0, 0, 0, 0]},
                {"index": 9, "text": "تسري أحكام هذه المدونة على",
                    "type": "text", "bbox": [0, 0, 0, 0]},
            ],
        }
    ]

    articles = PDFBlockParser.build_articles(pages)

    assert len(articles) == 2
    assert articles[0]["id"] == "المادة 1"
    assert articles[0]["text"] == "المادة 1 يطلق على هذا القانون اسم مدونة الأسرة"
    assert articles[1]["id"] == "المادة 2"
    assert articles[1]["text"] == "المادة 2 تسري أحكام هذه المدونة على"
