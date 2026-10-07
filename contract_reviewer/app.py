"""Flask 기반 계약서 검토 RAG 웹 애플리케이션.

환경 변수 OPENAI_API_KEY를 사용하며, 업로드된 원본 PDF는 처리 후 즉시 삭제합니다.
Chroma 벡터 데이터는 data/chroma 아래에 로컬로 영구 저장됩니다.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Iterator

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from tqdm import tqdm
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_UPLOAD_MB = 50

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["JSON_AS_ASCII"] = False

# 데모용 메모리 저장소입니다. 계약서 원문 자체는 디스크에 보관하지 않습니다.
contract_store: dict[str, list[str]] = {}
store_lock = threading.Lock()


class ReviewResult(BaseModel):
    """LLM이 반환해야 하는 계약 조항 검토 결과."""

    needs_revision: bool = Field(description="오류 또는 보완이 필요하면 true")
    revised_text: str = Field(description="수정이 필요할 때의 완전한 수정 문구")
    reason: str = Field(description="수정 근거를 한 문장으로 설명")


def require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다.")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def embeddings() -> OpenAIEmbeddings:
    require_api_key()
    return OpenAIEmbeddings(model="text-embedding-3-small")


def vector_store() -> Chroma:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name="contract_guidelines",
        embedding_function=embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def load_pdf(file_storage) -> list:
    """PyPDFLoader는 경로를 받으므로 임시 파일에서 읽은 후 바로 삭제합니다."""
    safe_name = secure_filename(file_storage.filename) or f"document-{uuid.uuid4()}.pdf"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f"-{safe_name}", delete=False) as temp_file:
            file_storage.save(temp_file.name)
            temp_path = Path(temp_file.name)
        documents = PyPDFLoader(str(temp_path)).load()
        for document in documents:
            document.metadata["source"] = safe_name
        return documents
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def clean_chunks(documents: list, *, overlap: int) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=30,
        chunk_overlap=overlap,
        separators=["\n", "\n\n"],
        length_function=len,
    )
    return [chunk for chunk in splitter.split_documents(documents) if chunk.page_content.strip()]


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    count = 0
    if CHROMA_DIR.exists():
        try:
            count = vector_store()._collection.count()
        except Exception:
            count = 0
    return jsonify({"rag_chunks": count, "api_key_ready": bool(os.getenv("OPENAI_API_KEY"))})


@app.post("/api/rag/upload")
def upload_rag():
    files = request.files.getlist("files")
    if not files or all(not file.filename for file in files):
        return jsonify({"error": "PDF 파일을 한 개 이상 선택해 주세요."}), 400
    if any(not allowed_file(file.filename) for file in files):
        return jsonify({"error": "PDF 파일만 업로드할 수 있습니다."}), 400

    try:
        all_documents = []
        for file in tqdm(files, desc="RAG PDF 읽기", unit="file"):
            all_documents.extend(load_pdf(file))
        chunks = clean_chunks(all_documents, overlap=5)
        if not chunks:
            return jsonify({"error": "PDF에서 텍스트를 찾지 못했습니다. 스캔 PDF라면 OCR이 필요합니다."}), 400

        # 큰 업로드에서도 API 요청 크기를 관리하기 위해 묶음 단위로 저장합니다.
        store = vector_store()
        batch_size = 100
        for start in tqdm(range(0, len(chunks), batch_size), desc="RAG 임베딩", unit="batch"):
            store.add_documents(chunks[start : start + batch_size])
        return jsonify({
            "message": f"가이드라인 {len(files)}개 파일을 학습 자료에 추가했습니다.",
            "file_count": len(files),
            "chunk_count": len(chunks),
            "total_chunks": store._collection.count(),
        })
    except Exception as exc:
        app.logger.exception("RAG 업로드 실패")
        return jsonify({"error": str(exc)}), 500


@app.post("/api/contract/upload")
def upload_contract():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "검토할 계약서 PDF를 선택해 주세요."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "PDF 파일만 업로드할 수 있습니다."}), 400

    try:
        documents = load_pdf(file)
        chunks = clean_chunks(documents, overlap=0)
        texts = [re.sub(r"\s+", " ", chunk.page_content).strip() for chunk in chunks]
        texts = [text for text in texts if text]
        if not texts:
            return jsonify({"error": "계약서에서 텍스트를 찾지 못했습니다. 스캔 PDF라면 OCR이 필요합니다."}), 400
        contract_id = uuid.uuid4().hex
        with store_lock:
            contract_store[contract_id] = texts
        return jsonify({
            "message": "계약서 업로드가 완료되었습니다. 이제 검토를 시작할 수 있습니다.",
            "contract_id": contract_id,
            "filename": secure_filename(file.filename),
            "sentence_count": len(texts),
        })
    except Exception as exc:
        app.logger.exception("계약서 업로드 실패")
        return jsonify({"error": str(exc)}), 500


def review_stream(contract_id: str) -> Iterator[str]:
    with store_lock:
        clauses = contract_store.get(contract_id)
    if not clauses:
        yield sse("error", {"message": "계약서를 다시 업로드해 주세요."})
        return

    try:
        store = vector_store()
        if store._collection.count() == 0:
            yield sse("error", {"message": "먼저 RAG 가이드라인 PDF를 업로드해 주세요."})
            return

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        reviewer = llm.with_structured_output(ReviewResult)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 한국어 계약서 검토 전문가입니다. 제공된 가이드라인만 근거로 조항을 검토하세요.
가이드라인과 충돌하거나 중요한 내용이 누락된 경우에만 수정하십시오.
표현 취향만으로 수정하지 말고, 수정 문구는 원문의 번호와 의미를 최대한 보존한 완전한 문장으로 작성하세요."""),
            ("human", """[검색된 가이드라인]\n{context}\n\n[검토할 원문]\n{clause}"""),
        ])

        total = len(clauses)
        yield sse("start", {"total": total})
        for index, clause in enumerate(tqdm(clauses, desc="계약서 검토", unit="clause"), start=1):
            related = store.similarity_search(clause, k=4)
            context = "\n---\n".join(doc.page_content for doc in related)
            result = reviewer.invoke(prompt.format_messages(context=context, clause=clause))
            yield sse("clause", {
                "index": index,
                "total": total,
                "original": clause,
                "needs_revision": result.needs_revision,
                "revised": result.revised_text.strip() if result.needs_revision else "",
                "reason": result.reason.strip() if result.needs_revision else "",
                "progress": round(index / total * 100),
            })
        yield sse("complete", {"message": "계약서 검토가 완료되었습니다.", "total": total})
    except GeneratorExit:
        return
    except Exception as exc:
        app.logger.exception("계약서 검토 실패")
        yield sse("error", {"message": str(exc)})


@app.get("/api/contract/review/<contract_id>")
def review_contract(contract_id: str):
    return Response(
        stream_with_context(review_stream(contract_id)),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question", "")).strip()
    if not question:
        return jsonify({"error": "질문을 입력해 주세요."}), 400
    try:
        require_api_key()
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        answer = llm.invoke([
            ("system", "당신은 명확하고 친절한 한국어 도우미입니다. 이 질문에는 RAG 문서를 사용하지 마세요."),
            ("human", question),
        ])
        return jsonify({"answer": answer.content})
    except Exception as exc:
        app.logger.exception("일반 질문 실패")
        return jsonify({"error": str(exc)}), 500


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": f"파일 크기는 전체 {MAX_UPLOAD_MB}MB 이하여야 합니다."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
