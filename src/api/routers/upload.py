"""
Upload & process user PDFs — extract, clean, normalize, parse to JSON.

Files are saved immediately, then processed in the background so the
upload response doesn't block on potentially slow PDF extraction.
"""

import json
import threading
import asyncio
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from src.ingestion.extractors.pdf_text import PdfToTextExtractor
from src.core.cleaning import LegalTextCleaner
from src.core.normalizing import ArabicNormalizer
from src.core.structure import parse_normalized_text_to_json, _extract_heading_number
from src.ingestion.pipeline import ingest_articles

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Paths ────────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path("data/uploaded")
UPLOAD_JSON_DIR = Path("data/processed/uploads")
STATUS_DIR = Path("data/uploaded/.status")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_JSON_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}


# ── Schemas ──────────────────────────────────────────────────────────────────

class UploadedFileInfo(BaseModel):
    """Summary info for a single uploaded file."""
    file_id: str
    original_filename: str
    size_bytes: int
    uploaded_at: str
    processed: bool
    processing: bool
    article_count: int
    json_path: Optional[str] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    """Response returned immediately after saving the uploaded file."""
    file_id: str
    original_filename: str
    size_bytes: int
    status: str  # "uploaded" | "processing" | "done"
    message: str


class UploadListResponse(BaseModel):
    """List of all uploaded files."""
    total: int
    files: list[UploadedFileInfo]


class EmbedResponse(BaseModel):
    """Response after embedding an uploaded file into the vector DB."""
    file_id: str
    source_file: str
    domain: str
    ingested: int
    clear_existing: bool
    message: str


# ── Processing status helpers ────────────────────────────────────────────────
# Status marker files: data/uploaded/.status/{file_id}.status
# Content: JSON with {status, article_count, error, processing_time_ms}

def _status_path(file_id: str) -> Path:
    return STATUS_DIR / f"{file_id}.status"


def _write_status(file_id: str, status: str, **kwargs):
    data = {"status": status, **kwargs}
    path = _status_path(file_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _read_status(file_id: str) -> Optional[dict]:
    path = _status_path(file_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _file_id_from_stem(stem: str) -> str:
    """Create a URL-safe file ID from a filename stem."""
    return stem.replace(" ", "_").replace("/", "_").replace("..", "")


def _infer_domain_from_name(filename: str) -> str:
    """Try to infer a legal domain from the filename."""
    name = filename.lower()
    if any(kw in name for kw in ("trade", "تجارة", "commercial")):
        return "commercial"
    if any(kw in name for kw in ("civil", "مدني")):
        return "civil"
    if any(kw in name for kw in ("penal", "جنائي", "criminal", "عقوبات")):
        return "criminal"
    if any(kw in name for kw in ("route", "سير", "traffic")):
        return "traffic"
    if any(kw in name for kw in ("قضائي", "judicial")):
        return "judicial"
    if any(kw in name for kw in ("ضري", "tax")):
        return "tax"
    if any(kw in name for kw in ("violation", "مخالفة")):
        return "violations"
    return "civil"


# ── Hierarchy builder ────────────────────────────────────────────────────────

HIERARCHY_LEVELS = ['book', 'section', 'subsection', 'chapter', 'branch']


def _build_hierarchy_tree(articles: list[dict]) -> list[dict]:
    """
    Build a hierarchical tree from flat articles with context.

    Each article's ``context`` dict contains hierarchy breadcrumbs
    (book → section → subsection → chapter → branch).  This function
    walks the breadcrumbs to assemble parent nodes, then places the
    article as a leaf under its deepest heading.

    Returns a list of root-level nodes (usually books or sections).
    """
    roots: list[dict] = []

    # Helper: find or create a child node at the current parent level
    def _ensure_child(parents: list[dict], level: str, title: str) -> dict:
        for child in parents:
            if child.get('title') == title:
                return child
        node = {
            'level': level,
            'title': title,
            'article_number': None,
            'children': [],
        }
        parents.append(node)
        return node

    for article in articles:
        ctx = article.get('context', {})
        art_num = article.get('article_number', '')
        text = article.get('text', '')

        # Walk hierarchy levels from top to bottom
        current_level_nodes = roots
        for level in HIERARCHY_LEVELS:
            title = ctx.get(level)
            if title:
                node = _ensure_child(current_level_nodes, level, title)
                current_level_nodes = node['children']
            else:
                # If this level is None but a deeper level exists, skip
                # (e.g. no book but has section)
                deeper = any(ctx.get(l) for l in HIERARCHY_LEVELS[
                    HIERARCHY_LEVELS.index(level) + 1:])
                if not deeper:
                    break

        # Place the article as a leaf under the deepest container
        leaf = {
            'level': 'article',
            'title': None,
            'article_number': art_num,
            'text_preview': text[:300] + '...' if len(text) > 300 else text,
            'children': [],
        }
        current_level_nodes.append(leaf)

    return roots


def _count_hierarchy_nodes(nodes: list[dict]) -> int:
    """Recursively count all nodes (including root-level ones)."""
    count = 0
    for node in nodes:
        count += 1
        count += _count_hierarchy_nodes(node.get('children', []))
    return count


def _process_pdf_background(file_id: str, pdf_path: Path):
    """
    Run the full pipeline in a background thread.
    Updates the status file on completion.
    """
    logger.info(f"Background processing started: {file_id}")
    start = time.time()

    try:
        # Step 1: Extract text
        extractor = PdfToTextExtractor(use_ocr=False)
        extraction_result = extractor.extract(pdf_path)

        # Step 2: Clean
        cleaner = LegalTextCleaner()
        cleaned = cleaner.clean_extraction_result(extraction_result)

        # Step 3: Normalize
        normalizer = ArabicNormalizer({
            "unify_alef": True,
            "remove_tatweel": True,
            "remove_diacritics": True,
            "preserve_shadda": False,
            "unify_digits": True,
        })
        normalized_text = normalizer.normalize(cleaned.full_text)

        # Step 4: Parse structure -> JSON
        domain = _infer_domain_from_name(pdf_path.stem)
        law_name = pdf_path.stem.replace("-", " ").replace("_", " ").strip()
        json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"

        articles = parse_normalized_text_to_json(
            normalized_text,
            domain=domain,
            law_name=law_name,
            output_path=str(json_path),
        )

        elapsed = (time.time() - start) * 1000
        _write_status(file_id, "done",
                      article_count=len(articles),
                      processing_time_ms=round(elapsed, 2))
        logger.info(f"Background processing done: {file_id} - "
                    f"{len(articles)} articles in {elapsed:.0f}ms")

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f"Background processing failed for {file_id}: {e}",
                     exc_info=True)
        _write_status(file_id, "error",
                      error=str(e),
                      processing_time_ms=round(elapsed, 2))


def _list_uploaded_files() -> list[UploadedFileInfo]:
    """Scan the upload directory and build a list of all uploaded files."""
    files: list[UploadedFileInfo] = []

    for pdf_path in sorted(UPLOAD_DIR.glob("*.pdf"), reverse=True):
        file_id = _file_id_from_stem(pdf_path.stem)
        json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
        status = _read_status(file_id)

        article_count = 0
        processed = False
        processing = False
        error = None

        if status:
            if status["status"] == "done":
                processed = True
                article_count = status.get("article_count", 0)
            elif status["status"] == "error":
                error = status.get("error", "Unknown error")
                if json_path.exists():
                    processed = True
                    try:
                        with open(json_path, encoding="utf-8") as f:
                            article_count = len(json.load(f))
                    except Exception:
                        pass
            elif status["status"] == "processing":
                processing = True
        else:
            if json_path.exists():
                processed = True
                try:
                    with open(json_path, encoding="utf-8") as f:
                        article_count = len(json.load(f))
                except Exception:
                    pass
            else:
                processing = True
                _write_status(file_id, "processing")

        stat = pdf_path.stat()
        files.append(UploadedFileInfo(
            file_id=file_id,
            original_filename=pdf_path.name,
            size_bytes=stat.st_size,
            uploaded_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            processed=processed,
            processing=processing,
            article_count=article_count,
            json_path=str(json_path) if json_path.exists() else None,
            error=error,
        ))

    return files


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF file. The file is saved immediately and processing starts
    in the background. Poll GET /uploads/{file_id}/status for completion.
    """
    ext = Path(file.filename or "file.pdf").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only PDF files are allowed.",
        )

    file_id = _file_id_from_stem(Path(file.filename).stem)

    save_path = UPLOAD_DIR / f"{file_id}.pdf"
    if save_path.exists():
        ts = int(time.time())
        save_path = UPLOAD_DIR / f"{file_id}_{ts}.pdf"
        file_id = f"{file_id}_{ts}"

    content = await file.read()
    save_path.write_bytes(content)
    file_size = len(content)

    _write_status(file_id, "processing")

    thread = threading.Thread(
        target=_process_pdf_background,
        args=(file_id, save_path),
        daemon=True,
    )
    thread.start()

    logger.info(f"File saved + background processing started: "
                f"{save_path.name} ({file_size} bytes) - file_id={file_id}")

    return UploadResponse(
        file_id=file_id,
        original_filename=file.filename or save_path.name,
        size_bytes=file_size,
        status="processing",
        message=f"File uploaded. Processing in background (file_id={file_id}).",
    )


@router.get("/uploads/{file_id}/status")
async def get_upload_status(file_id: str):
    """Check the processing status of an uploaded file."""
    status = _read_status(file_id)
    if status is None:
        pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
        if not pdf_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No upload found for file_id '{file_id}'.",
            )
        json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
        processed = json_path.exists()
        status = {"status": "done" if processed else "unknown"}

    return {
        "file_id": file_id,
        "status": status.get("status", "unknown"),
        "article_count": status.get("article_count", 0),
        "error": status.get("error"),
        "processing_time_ms": status.get("processing_time_ms"),
    }


@router.get("/uploads/{file_id}/hierarchy")
async def get_upload_hierarchy(file_id: str):
    """
    Get the hierarchical document tree for an uploaded file.

    Builds a tree from the flat articles and their context breadcrumbs.
    Structure: book -> section -> subsection -> chapter -> branch -> article.
    Heading-only documents (no individual articles) show each heading
    as a container node so the frontend can render the full outline.
    """
    json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
    if not json_path.exists():
        matches = list(UPLOAD_JSON_DIR.glob(f"{file_id}*.articles.json"))
        if matches:
            json_path = matches[0]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No processed JSON found for file_id '{file_id}'. "
                f"Upload a file first and wait for processing.",
            )

    try:
        with open(json_path, encoding="utf-8") as f:
            articles = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse articles JSON: {e}",
        )

    tree = _build_hierarchy_tree(articles)
    node_count = _count_hierarchy_nodes(tree)

    return {
        "file_id": file_id,
        "article_count": len(articles),
        "node_count": node_count,
        "hierarchy": tree,
    }


@router.post("/uploads/{file_id}/embed", response_model=EmbedResponse)
async def embed_uploaded_file(
    file_id: str,
    domain: str = "uploaded",
    clear_existing: bool = True,
):
    """
    Embed a processed uploaded file into the vector database.

    Loads the processed articles JSON and runs them through the
    embedding pipeline (embed → store in ``legal_chunks`` table).

    Args:
        file_id: The uploaded file identifier (stem).
        domain: Legal domain to assign (default: 'uploaded').
        clear_existing: Whether to delete existing chunks for this
            source before inserting (default: True).

    Returns:
        Number of articles ingested.
    """
    json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
    if not json_path.exists():
        # Try partial match
        matches = list(UPLOAD_JSON_DIR.glob(f"{file_id}*.articles.json"))
        if matches:
            json_path = matches[0]
            file_id = json_path.stem.replace(".articles", "")
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No processed JSON found for file_id '{file_id}'. "
                f"Upload and process a file first.",
            )

    # Derive source_file from the PDF in the upload dir
    pdf_candidates = list(UPLOAD_DIR.glob(f"{file_id}.pdf"))
    source_file = pdf_candidates[0].name if pdf_candidates else f"{file_id}.pdf"

    try:
        ingested = await asyncio.to_thread(
            ingest_articles,
            json_path=json_path,
            domain=domain,
            source_file=source_file,
            extraction_method="pipeline",
            clear_existing=clear_existing,
        )
    except Exception as e:
        logger.error(f"Embedding failed for {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Embedding failed: {e}",
        )

    return EmbedResponse(
        file_id=file_id,
        source_file=source_file,
        domain=domain,
        ingested=ingested,
        clear_existing=clear_existing,
        message=f"Successfully ingested {ingested} articles into the vector database."
        if ingested > 0
        else "No articles were ingested (the JSON may be empty).",
    )


@router.get("/uploads", response_model=UploadListResponse)
async def list_uploads():
    """List all uploaded PDF files with their processing status."""
    files = _list_uploaded_files()
    return UploadListResponse(total=len(files), files=files)


@router.get("/uploads/{file_id}/articles")
async def get_upload_articles(file_id: str):
    """
    Get the parsed articles JSON for a specific uploaded file.
    The `file_id` is the filename without extension (e.g. 'my_document').
    """
    json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
    if not json_path.exists():
        matches = list(UPLOAD_JSON_DIR.glob(f"{file_id}*.articles.json"))
        if matches:
            json_path = matches[0]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No processed JSON found for file_id '{file_id}'. "
                f"Upload a file first and wait for processing.",
            )

    try:
        with open(json_path, encoding="utf-8") as f:
            articles = json.load(f)
        return {
            "file_id": file_id,
            "article_count": len(articles),
            "articles": articles,
        }
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse articles JSON: {e}",
        )


@router.delete("/uploads/{file_id}", status_code=204)
async def delete_upload(file_id: str):
    """Delete an uploaded PDF, its processed JSON, and status marker."""
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
    json_path = UPLOAD_JSON_DIR / f"{file_id}.articles.json"
    status_path = _status_path(file_id)

    deleted_any = False
    for p in [pdf_path, json_path, status_path]:
        if p.exists():
            p.unlink()
            deleted_any = True

    if not deleted_any:
        raise HTTPException(
            status_code=404,
            detail=f"No upload found for file_id '{file_id}'.",
        )

    logger.info(f"Deleted upload: {file_id}")
