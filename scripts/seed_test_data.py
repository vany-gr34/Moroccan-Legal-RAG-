"""
Seed the database with Arabic legal embeddings for testing.

Usage:
    python scripts/seed_test_data.py
"""

from src.core.embedding import create_embedder
from src.db.session import get_connection
from pathlib import Path
import logging
import time
import sys
import numpy as np
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================
# Sample Arabic legal articles
# ============================================

ARTICLES = [
    # Criminal Law
    {
        "chunk_text": "المادة 147 من القانون الجنائي: كل من ارتكب جريمة السرقة يعاقب بالحبس من سنة إلى خمس سنوات وغرامة مالية.",
        "domain": "criminal",
        "law_name": "القانون الجنائي",
        "article_number": "147",
    },
    {
        "chunk_text": "المادة 400 من القانون الجنائي: الضرب والجرح العمدي يعاقب عليه بالحبس من شهر إلى ثلاث سنوات.",
        "domain": "criminal",
        "law_name": "القانون الجنائي",
        "article_number": "400",
    },
    {
        "chunk_text": "المادة 241 من القانون الجنائي: الاحتيال للحصول على مال الغير يعاقب بالحبس والغرامة.",
        "domain": "criminal",
        "law_name": "القانون الجنائي",
        "article_number": "241",
    },
    # Traffic Law
    {
        "chunk_text": "المادة 172 من مدونة السير: تجاوز السرعة القصوى المسموح بها في المدار الحضري يعرض المخالف لعقوبة مالية.",
        "domain": "traffic",
        "law_name": "مدونة السير",
        "article_number": "172",
    },
    {
        "chunk_text": "المادة 175 من مدونة السير: السياقة تحت تأثير الكحول تعرض المخالف لعقوبة حبسية وغرامة مالية.",
        "domain": "traffic",
        "law_name": "مدونة السير",
        "article_number": "175",
    },
    {
        "chunk_text": "المادة 180 من مدونة السير: عدم احترام إشارات المرور يعاقب بغرامة مالية وسحب رخصة السياقة.",
        "domain": "traffic",
        "law_name": "مدونة السير",
        "article_number": "180",
    },
    # Family Law
    {
        "chunk_text": "المادة 48 من مدونة الأسرة: النفقة واجبة على الزوج لزوجته بمجرد الدخول بها وتشمل الطعام والكسوة والسكن.",
        "domain": "family",
        "law_name": "مدونة الأسرة",
        "article_number": "48",
    },
    {
        "chunk_text": "المادة 78 من مدونة الأسرة: الطلاق هو حل ميثاق الزوجية ويمارسه الزوج والزوجة حسب شروط قانونية.",
        "domain": "family",
        "law_name": "مدونة الأسرة",
        "article_number": "78",
    },
    {
        "chunk_text": "المادة 54 من مدونة الأسرة: حضانة الأطفال حق للأبوين معا ولا تسقط إلا بمقتضى حكم قضائي.",
        "domain": "family",
        "law_name": "مدونة الأسرة",
        "article_number": "54",
    },
    # Civil Law
    {
        "chunk_text": "المادة 1 من قانون الالتزامات والعقود: الالتزامات تنشأ عن الاتفاقات والتصرفات القانونية وعن الأفعال الضارة.",
        "domain": "civil",
        "law_name": "قانون الالتزامات والعقود",
        "article_number": "1",
    },
    {
        "chunk_text": "المادة 77 من قانون الالتزامات والعقود: العقد شريعة المتعاقدين ويجب تنفيذه بحسن نية.",
        "domain": "civil",
        "law_name": "قانون الالتزامات والعقود",
        "article_number": "77",
    },
    # Commercial Law
    {
        "chunk_text": "المادة 54 من مدونة التجارة: السجل التجاري يمسك لدى المحكمة التجارية المختصة ويقيد فيه كل تاجر.",
        "domain": "commercial",
        "law_name": "مدونة التجارة",
        "article_number": "54",
    },
    {
        "chunk_text": "المادة 1 من مدونة التجارة: يعد تاجرا كل من يباشر الأعمال التجارية ويتخذها مهنة معتادة له.",
        "domain": "commercial",
        "law_name": "مدونة التجارة",
        "article_number": "1",
    },
    # Judicial Procedures
    {
        "chunk_text": "المادة 134 من قانون المسطرة المدنية: الاستئناف يرفع أمام المحكمة الأعلى درجة خلال ثلاثين يوما من تاريخ الحكم.",
        "domain": "judicial",
        "law_name": "قانون المسطرة المدنية",
        "article_number": "134",
    },
    {
        "chunk_text": "المادة 1 من قانون المسطرة المدنية: تطبق قواعد المسطرة المدنية أمام جميع المحاكم ما لم ينص القانون على خلاف ذلك.",
        "domain": "judicial",
        "law_name": "قانون المسطرة المدنية",
        "article_number": "1",
    },
    # Violations
    {
        "chunk_text": "المادة 1 من قانون المخالفات: المخالفات تصنف إلى مخالفات من الدرجة الأولى والثانية والثالثة حسب خطورتها.",
        "domain": "violations",
        "law_name": "قانون المخالفات والعقوبات",
        "article_number": "1",
    },
    {
        "chunk_text": "المادة 5 من قانون المخالفات: الغرامات المالية تحدد حسب درجة المخالفة ونوعها بقرار من السلطة المختصة.",
        "domain": "violations",
        "law_name": "قانون المخالفات والعقوبات",
        "article_number": "5",
    },
]


def seed(clear_first: bool = False):
    """Generate embeddings and insert into database."""

    # Connect
    conn = get_connection()
    cur = conn.cursor()

    # Clear existing test data if requested
    if clear_first:
        cur.execute(
            "DELETE FROM legal_chunks WHERE source_file = 'seed_test_data'")
        conn.commit()
        logger.info("Cleared existing test data")

    # Check for duplicates
    cur.execute(
        "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'")
    existing = cur.fetchone()[0]
    if existing > 0:
        logger.info(
            f"Found {existing} existing test chunks. Use --clear to reset.")
        logger.info("Skipping insert (data already exists).")
        cur.close()
        conn.close()
        return

    # Initialize embedder
    logger.info("Initializing embedder...")
    embedder = create_embedder()
    logger.info(
        f"Embedder mode: {embedder.mode} | Dimension: {embedder.dimension}")

    # Generate embeddings
    texts = [a["chunk_text"] for a in ARTICLES]
    logger.info(f"Generating embeddings for {len(texts)} articles...")
    start = time.time()
    embeddings = embedder.embed(texts)
    elapsed = time.time() - start
    logger.info(
        f"Embeddings generated in {elapsed:.1f}s ({len(texts)/elapsed:.0f} texts/s)")
    logger.info(f"Embedding shape: {embeddings.shape}")

    # Insert into database
    logger.info("Inserting into PostgreSQL...")
    insert_start = time.time()

    for i, article in enumerate(ARTICLES):
        # Normalize text (simple: strip extra whitespace)
        normalized = " ".join(article["chunk_text"].split())

        cur.execute(
            """
            INSERT INTO legal_chunks 
                (chunk_text, chunk_text_normalized, embedding, domain, 
                 law_name, article_number, source_file, extraction_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                article["chunk_text"],
                normalized,
                embeddings[i].tolist(),
                article["domain"],
                article["law_name"],
                article["article_number"],
                "seed_test_data",
                "manual",
            ),
        )

    conn.commit()
    insert_elapsed = time.time() - insert_start
    logger.info(f"Inserted {len(ARTICLES)} chunks in {insert_elapsed:.1f}s")

    # Verify
    cur.execute(
        "SELECT COUNT(*) FROM legal_chunks WHERE source_file = 'seed_test_data'")
    count = cur.fetchone()[0]
    logger.info(f"Verified: {count} chunks in database")

    # Show per-domain counts
    cur.execute("""
        SELECT domain, COUNT(*) 
        FROM legal_chunks 
        WHERE source_file = 'seed_test_data' 
        GROUP BY domain 
        ORDER BY domain
    """)
    logger.info("Per-domain counts:")
    for row in cur.fetchall():
        logger.info(f"  {row[0]}: {row[1]}")

    cur.close()
    conn.close()
    logger.info("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing test data first")
    args = parser.parse_args()
    seed(clear_first=args.clear)
