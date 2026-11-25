"""Ask endpoint - legal question answering with RAG.

Each request is independent (no multi-turn context).
A unique session_id is generated per request for history storage.
"""

import time
import asyncio
import uuid
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List

from ..dependencies import get_retrieval_strategy
from ...generation.factory import get_llm
from ...db.conversations import save_exchange

router = APIRouter()

DISCLAIMER = (
    "هذه الاجابة مولدة اليا بناء على النصوص القانونية المسترجعة. "
    "يرجى مراجعة النصوص الاصلية والاستعانة بمختص قانوني عند الحاجة."
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    query: str = Field(..., description="Arabic legal question")
    domain: Optional[str] = Field(None, description="Legal domain filter")
    top_k: int = Field(
        5, ge=1, le=10, description="Number of articles to retrieve")
    strategy: Optional[str] = Field(None, description="Retrieval strategy")


class SourceArticle(BaseModel):
    article_number: str
    law_name: str
    domain: str
    chapter_title: Optional[str]
    section_title: Optional[str]
    text_preview: str
    text_full: str
    relevance_score: float


class AskResponse(BaseModel):
    query: str
    short_answer: str
    long_answer: str
    example: Optional[str]
    disclaimer: str
    sources: List[SourceArticle]
    knowledge_base: List[str]
    session_id: str
    search_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    model_name: str


# ---------------------------------------------------------------------------
# Prompt builder (no history — each question is independent)
# ---------------------------------------------------------------------------
def build_legal_prompt(query: str, sources: list) -> str:
    """Build a grounded legal prompt with retrieved articles."""
    articles_text = []
    for i, src in enumerate(sources, 1):
        articles_text.append(
            f"[{i}] المادة {src.article_number} من {src.law_name}:\n{src.text_full}\n"
        )

    context = "\n".join(articles_text)

    prompt = f"""النصوص القانونية المسترجعة:

{context}

بناء على النصوص القانونية أعلاه فقط، أجب على السؤال التالي.
إذا لم تكن الإجابة موجودة في النصوص، فقل ذلك بوضوح.
لا تخترع معلومات غير موجودة في النصوص.

## 📋 تعليمات التنسيق

قدم إجابتك بتنسيق Markdown منظم وفق الهيكل التالي:

### 1. ملخص الإجابة
- إجابة مختصرة مباشرة (جملة أو جملتين)

### 2. التحليل القانوني
- شرح كيف تجيب كل مادة قانونية مسترجعة على السؤال
- اربط بين السؤال والنصوص القانونية بشكل واضح
- استشهد بأرقام المواد أثناء الشرح

### 3. الخلاصة
- استنتاج نهائي مبني على التحليل أعلاه

### 4. المواد القانونية المستند إليها
- **المادة [الرقم]** من **[اسم القانون]** – [سبب الاستناد إليها]

> ⚖️ *هذا تحليل آلي بناء على النصوص المسترجعة، يرجى مراجعة النصوص الأصلية والاستعانة بمختص قانوني عند الحاجة.*

السؤال: {query}
"""
    return prompt


def parse_llm_response(raw_response: str) -> dict:
    """Parse the LLM response into short_answer, long_answer, example."""
    lines = raw_response.strip().split("\n")

    short_answer = ""
    long_answer = ""
    example = None

    current_section = None
    sections = {"1.": "short", "2.": "long", "3.": "example", "4.": "sources"}

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for section markers
        for marker, section in sections.items():
            if stripped.startswith(marker):
                current_section = section
                stripped = stripped[len(marker):].strip()
                break

        if current_section == "short":
            short_answer += stripped + " "
        elif current_section == "long":
            long_answer += stripped + " "
        elif current_section == "example":
            if example is None:
                example = ""
            example += stripped + " "

    # Fallback: if no structured output, use the whole response
    if not short_answer:
        short_answer = raw_response[:300]
    if not long_answer:
        long_answer = raw_response

    return {
        "short": short_answer.strip(),
        "long": long_answer.strip(),
        "example": example.strip() if example else None,
    }


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@router.post("/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest):
    """Ask a legal question and get a grounded answer with citations."""
    total_start = time.time()

    # Generate a unique session ID for this single Q&A exchange
    session_id = str(uuid.uuid4())

    # 1. Retrieve relevant articles (run in thread to avoid blocking the event loop)
    search_start = time.time()
    strategy = get_retrieval_strategy(request.strategy or "rrf")
    search_response = await asyncio.to_thread(
        strategy.search,
        query=request.query,
        domain=request.domain,
        top_k=request.top_k,
    )
    search_time = (time.time() - search_start) * 1000

    # 2. Build sources list
    sources = []
    knowledge_base = set()
    max_rrf = 1.0 / (60 + 1) + 1.0 / (60 + 1)

    for result in search_response.results:
        sources.append(SourceArticle(
            article_number=result.article_number,
            law_name=result.law_name,
            domain=result.domain,
            chapter_title=result.chapter_title,
            section_title=result.section_title,
            text_preview=result.text[:300] +
            "..." if len(result.text) > 300 else result.text,
            text_full=result.text,
            relevance_score=round(result.similarity /
                                  max_rrf * 100, 1) if max_rrf > 0 else 0.0,
        ))
        knowledge_base.add(result.law_name)

    # 3. Build prompt (no history injection)
    prompt = build_legal_prompt(request.query, sources)

    # 4. Call LLM (run in thread to avoid blocking)
    gen_start = time.time()
    try:
        llm = get_llm()
        gen_result = await asyncio.to_thread(llm.generate, prompt=prompt)
        answer = parse_llm_response(gen_result.response)
        model_name = gen_result.model_name
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.error(f"LLM generation failed: {e}")
        answer = {
            "short": "خدمة الذكاء الاصطناعي غير متوفرة حاليا. يرجى الاطلاع على المواد القانونية المسترجعة.",
            "long": "",
            "example": None,
        }
        model_name = "unavailable"
        gen_result = type("obj", (object,), {
                          "tokens_generated": 0, "generation_time_ms": 0, "response": ""})()

    gen_time = (time.time() - gen_start) * 1000
    total_time = (time.time() - total_start) * 1000
    kb_sorted = sorted(knowledge_base)

    # 5. Save exchange to DB — store full structured response in metadata
    #    so it can be reconstructed when viewing history.
    try:
        sources_payload = [
            {
                "article_number": s.article_number,
                "law_name": s.law_name,
                "domain": s.domain,
                "chapter_title": s.chapter_title,
                "section_title": s.section_title,
                "text_preview": s.text_preview,
                "text_full": s.text_full,
                "relevance_score": s.relevance_score,
            }
            for s in sources
        ]
        save_exchange(
            session_id=session_id,
            user_query=request.query,
            assistant_response=gen_result.response,
            sources=sources_payload,
            metadata={
                "model": model_name,
                "search_time_ms": round(search_time, 2),
                "gen_time_ms": round(gen_time, 2),
                "total_time_ms": round(total_time, 2),
                "short_answer": answer["short"],
                "long_answer": answer["long"],
                "example": answer.get("example"),
                "disclaimer": DISCLAIMER,
                "knowledge_base": kb_sorted,
            },
        )
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"Failed to save conversation history: {e}")

    return AskResponse(
        query=request.query,
        short_answer=answer["short"],
        long_answer=answer["long"],
        example=answer.get("example"),
        disclaimer=DISCLAIMER,
        sources=sources,
        knowledge_base=kb_sorted,
        session_id=session_id,
        search_time_ms=round(search_time, 2),
        generation_time_ms=round(gen_time, 2),
        total_time_ms=round(total_time, 2),
        model_name=model_name,
    )
