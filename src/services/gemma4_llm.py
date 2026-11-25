import subprocess
import requests
import socket
import time

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Moroccan Legal RAG - Gemma4-E2B-QAT",
    version="1.0.0",
)

LLAMA_PORT = 8081

MODEL_REPO = "unsloth/gemma-4-E2B-it-GGUF:UD-Q4_K_XL"

llama_process = None

SYSTEM_PROMPT = (
    "انت مساعد قانوني مغربي متخصص. تجيب على الاسئلة القانونية بناء على "
    "النصوص القانونية المقدمة فقط. لا تخترع معلومات غير موجودة في النصوص. "
    "تذكر ارقام المواد التي استندت اليها في اجابتك. "
    "اذا لم تكن الاجابة موجودة في النصوص المقدمة فقل ذلك بوضوح.\n\n"
    "قدم اجابتك بهذا التنسيق:\n"
    "1. اجابة مختصرة\n"
    "2. شرح مفصل\n"
    "3. مثال عملي\n"
    "4. المواد القانونية المستند اليها"
)


class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 4096
    temperature: float = 0.3
    top_p: float = 0.9


class LLMResponse(BaseModel):
    response: str
    tokens_generated: int
    time_ms: float


def wait_for_server():

    while True:

        try:

            requests.get(
                f"http://127.0.0.1:{LLAMA_PORT}/health",
                timeout=1
            )

            break

        except Exception:

            time.sleep(1)


def start_llama():

    global llama_process

    llama_process = subprocess.Popen(
        [
            "llama-server",
            "-hf",
            MODEL_REPO,
            "-ngl",
            "0",
            "--host",
            "127.0.0.1",
            "--port",
            str(LLAMA_PORT)
        ]
    )

    wait_for_server()


@app.on_event("startup")
def startup():

    start_llama()


@app.get("/")
def root():

    return {
        "service": "Moroccan Legal RAG - Gemma4-E2B-QAT",
        "model": MODEL_REPO,
        "backend": "llama.cpp"
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "model": MODEL_REPO
    }


@app.post("/generate", response_model=LLMResponse)
def generate(request: LLMRequest):

    start = time.time()

    response = requests.post(
        f"http://127.0.0.1:{LLAMA_PORT}/v1/chat/completions",
        json={
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
        },
    )

    elapsed = time.time() - start
    data = response.json()

    generated_text = data["choices"][0]["message"]["content"]
    tokens_generated = (
        data["usage"]["completion_tokens"]
        if "usage" in data
        else len(generated_text.split())
    )

    return LLMResponse(
        response=generated_text.strip(),
        tokens_generated=tokens_generated,
        time_ms=round(elapsed * 1000, 2),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001
    )
