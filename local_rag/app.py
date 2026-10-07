from __future__ import annotations

import os
import json
import shutil
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, session, stream_with_context
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
NO_ANSWER = "정보가 없어서 답변할 수 없습니다"
TOP_K = 4
MAX_HISTORY_MESSAGES = 12


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "local-rag-development-key"),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    histories: dict[str, list[dict[str, str]]] = {}
    services: dict[str, RagService] = {}

    def session_id() -> str:
        if "rag_session_id" not in session:
            session["rag_session_id"] = uuid.uuid4().hex
        return session["rag_session_id"]

    def service() -> "RagService":
        sid = session_id()
        if sid not in services:
            services[sid] = RagService(sid)
        return services[sid]

    @app.get("/")
    def index():
        sid = session_id()
        return render_template("index.html", history=histories.get(sid, []))

    @app.post("/api/upload")
    def upload():
        files = request.files.getlist("files")
        if not files or all(not item.filename for item in files):
            return jsonify(error="업로드할 PDF 파일을 선택해 주세요."), 400
        invalid = [item.filename for item in files if not _is_pdf(item.filename)]
        if invalid:
            return jsonify(error="PDF 파일만 업로드할 수 있습니다.", invalid_files=invalid), 400

        saved_files: list[tuple[Path, str]] = []
        target_dir = UPLOAD_DIR / session_id()
        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            for item in files:
                original_name = Path(item.filename).name
                safe_stem = secure_filename(Path(original_name).stem) or "document"
                filename = f"{safe_stem}.pdf"
                path = _unique_path(target_dir, filename)
                saved_files.append((path, original_name))
                item.save(path)
                with path.open("rb") as pdf_file:
                    header = pdf_file.read(5)
                if header != b"%PDF-":
                    raise ValueError(f"{item.filename}은(는) 올바른 PDF 파일이 아닙니다.")
            result = service().add_pdfs(saved_files)
        except Exception as exc:
            for path, _ in saved_files:
                path.unlink(missing_ok=True)
            return jsonify(error=f"PDF 처리 중 오류가 발생했습니다: {exc}"), 400

        return jsonify(
            message=f"PDF {len(saved_files)}개를 저장했습니다.",
            files=[original_name for _, original_name in saved_files],
            chunks=result,
        )

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="질문을 JSON 객체로 보내 주세요."), 400
        message = payload.get("message", "")
        if not isinstance(message, str):
            return jsonify(error="질문은 문자열로 입력해 주세요."), 400
        question = message.strip()
        if not question:
            return jsonify(error="질문을 입력해 주세요."), 400

        sid = session_id()
        history = histories.setdefault(sid, [])
        try:
            answer_chunks, sources = service().stream_answer(question, history)
        except Exception as exc:
            return jsonify(error=f"답변 생성 중 오류가 발생했습니다: {exc}"), 500

        @stream_with_context
        def generate():
            parts: list[str] = []
            try:
                for chunk in answer_chunks:
                    if not chunk:
                        continue
                    parts.append(chunk)
                    yield _stream_event("token", text=chunk)

                answer = "".join(parts).strip()
                if not answer:
                    answer = NO_ANSWER
                    yield _stream_event("token", text=answer)
                final_sources = [] if NO_ANSWER in answer else sources
                history.extend(
                    [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ]
                )
                del history[:-MAX_HISTORY_MESSAGES]
                yield _stream_event("done", sources=final_sources)
            except Exception as exc:
                yield _stream_event("error", message=f"답변 생성 중 오류가 발생했습니다: {exc}")

        return Response(
            generate(),
            content_type="application/x-ndjson; charset=utf-8",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/reset")
    def reset():
        sid = session_id()
        histories.pop(sid, None)
        instance = services.pop(sid, None)
        if instance:
            instance.delete_collection()
        shutil.rmtree(UPLOAD_DIR / sid, ignore_errors=True)
        return jsonify(message="문서와 대화 기록을 초기화했습니다.")

    @app.errorhandler(413)
    def upload_too_large(error):
        return jsonify(error="업로드 요청이 허용 용량을 초과했습니다. PDF 크기를 줄여 주세요."), 413

    return app


class RagService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.store = Chroma(
            collection_name=f"rag_{session_id}",
            embedding_function=self.embeddings,
            persist_directory=str(CHROMA_DIR),
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

    def add_pdfs(self, files: list[tuple[Path, str]]) -> int:
        documents = []
        for path, original_name in files:
            pages = PyPDFLoader(str(path)).load()
            for page in pages:
                page.metadata["source"] = original_name
                page.metadata["session_id"] = self.session_id
            documents.extend(pages)
        chunks = [chunk for chunk in self.splitter.split_documents(documents) if chunk.page_content.strip()]
        if not chunks:
            raise ValueError("PDF에서 읽을 수 있는 텍스트를 찾지 못했습니다.")
        ids = [uuid.uuid4().hex for _ in chunks]
        self.store.add_documents(chunks, ids=ids)
        return len(chunks)

    def stream_answer(self, question: str, history: list[dict[str, str]]):
        if not self.store.get(limit=1).get("ids"):
            return iter((NO_ANSWER,)), []

        query = self._standalone_query(question, history)
        candidates = self.store.similarity_search_with_score(query, k=TOP_K)
        if not candidates:
            return iter((NO_ANSWER,)), []

        context_parts = []
        sources = []
        for index, (doc, distance) in enumerate(candidates, start=1):
            page = int(doc.metadata.get("page", 0)) + 1
            filename = doc.metadata.get("source", "알 수 없는 문서")
            content = " ".join(doc.page_content.split())
            context_parts.append(f"[근거 {index} | {filename} | {page}페이지]\n{content}")
            sources.append(
                {
                    "file": filename,
                    "page": page,
                    "summary": self._summarize_chunk(content),
                    "distance": round(float(distance), 3),
                }
            )

        history_text = "\n".join(
            f"{('사용자' if item['role'] == 'user' else '도우미')}: {item['content']}"
            for item in history[-8:]
        )
        prompt = f"""이전 대화:
{history_text or '(없음)'}

문서 근거:
{chr(10).join(context_parts)}

질문: {question}

문서 근거만 사용해 한국어로 답하세요. 먼저 근거가 질문과 직접 관련 있는지 판단하세요. 관련이 없거나 답하기에 부족하면 정확히 '{NO_ANSWER}'라고만 답하세요. 문서의 전체 내용·주제·요약을 묻는 질문에는 제공된 근거에서 핵심 내용을 종합하세요. 출처 목록은 별도로 표시되므로 답변 본문에는 만들지 마세요."""
        messages = [
            SystemMessage(content="당신은 업로드된 문서에만 근거하는 정확한 RAG 도우미입니다."),
            HumanMessage(content=prompt),
        ]

        def chunks():
            for chunk in self.llm.stream(messages):
                content = chunk.content
                if isinstance(content, str):
                    yield content

        return chunks(), sources

    def answer(self, question: str, history: list[dict[str, str]]) -> dict:
        """Non-streaming compatibility helper for callers outside the web UI."""
        chunks, sources = self.stream_answer(question, history)
        answer = "".join(chunks).strip() or NO_ANSWER
        if NO_ANSWER in answer:
            sources = []
        return {"answer": answer, "sources": sources}

    def _standalone_query(self, question: str, history: list[dict[str, str]]) -> str:
        history_text = "\n".join(
            f"{item['role']}: {item['content']}" for item in history[-8:]
        )
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "대화 맥락을 반영해 벡터 검색용 독립 질문 하나만 작성하세요. "
                        "문서가 무슨 내용인지, 주제가 무엇인지 묻는 포괄적인 질문은 "
                        "'문서의 주제, 목적, 핵심 내용과 결론'을 찾는 검색문으로 바꾸세요."
                    )
                ),
                HumanMessage(content=f"대화:\n{history_text or '(없음)'}\n\n새 질문: {question}"),
            ]
        )
        return response.content.strip() or question

    def _summarize_chunk(self, content: str) -> str:
        response = self.llm.invoke(
            [
                SystemMessage(content="주어진 문서 조각을 한국어 한 문장으로만 간결하게 요약하세요."),
                HumanMessage(content=content),
            ]
        )
        return response.content.strip()

    def delete_collection(self) -> None:
        self.store.delete_collection()


def _is_pdf(filename: str | None) -> bool:
    return bool(filename and Path(filename).suffix.lower() == ".pdf")


def _unique_path(directory: Path, filename: str) -> Path:
    path = directory / filename
    if not path.exists():
        return path
    return directory / f"{path.stem}-{uuid.uuid4().hex[:8]}{path.suffix}"


def _stream_event(event: str, **payload) -> str:
    return json.dumps({"event": event, **payload}, ensure_ascii=False) + "\n"


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
