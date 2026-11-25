"""
Generate fixture PDFs for the test suite.
Run once from the project root:  python create_fixtures.py
"""
from pathlib import Path
import fitz
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURE_DIR = Path("tests/fixtures")
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def create_text_image(image_path: Path, text: str):
    img = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 100), text, fill="black")
    img.save(image_path)


def create_digital_pdf():
    path = FIXTURE_DIR / "sample_digital.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    text = "This is a digital PDF page with extractable text. " * 20
    for i in range(3):
        c.drawString(72, 720, f"Page {i + 1}")
        text_object = c.beginText(72, 680)
        text_object.textLines(text)
        c.drawText(text_object)
        c.showPage()
    c.save()
    print(f"Created {path}")


def create_scanned_pdf():
    pdf_path = FIXTURE_DIR / "sample_scanned.pdf"
    doc = fitz.open()
    for i in range(3):
        image_path = FIXTURE_DIR / f"scan_{i}.png"
        create_text_image(image_path, "This text is embedded inside an image only. " * 20)
        img_doc = fitz.open(str(image_path))
        rect = img_doc[0].rect
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, filename=str(image_path))
        img_doc.close()
    doc.save(pdf_path)
    doc.close()
    print(f"Created {pdf_path}")


def create_hybrid_pdf():
    pdf_path = FIXTURE_DIR / "sample_hybrid.pdf"
    doc = fitz.open()
    # 3 text pages
    for _ in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), "This is a digital text page. " * 30, fontsize=12)
    # 3 image-only pages
    for i in range(3):
        image_path = FIXTURE_DIR / f"hybrid_scan_{i}.png"
        create_text_image(image_path, "Hybrid scanned page " * 20)
        img_doc = fitz.open(str(image_path))
        rect = img_doc[0].rect
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(rect, filename=str(image_path))
        img_doc.close()
    doc.save(pdf_path)
    doc.close()
    print(f"Created {pdf_path}")


def create_corrupted_pdf():
    path = FIXTURE_DIR / "sample_corrupted.pdf"
    path.write_bytes(b"%PDF-1.4 corrupted content")
    print(f"Created {path}")


def create_empty_pdf():
    """Valid PDF structure with 0 pages (fitz refuses to save 0-page docs)."""
    path = FIXTURE_DIR / "sample_empty.pdf"
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type /Pages /Kids [] /Count 0>>endobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer<</Size 3 /Root 1 0 R>>\n"
        b"startxref\n110\n%%EOF"
    )
    print(f"Created {path}")


if __name__ == "__main__":
    create_digital_pdf()
    create_scanned_pdf()
    create_hybrid_pdf()
    create_corrupted_pdf()
    create_empty_pdf()
    print("\nAll fixtures generated.")