# Clause — LLM 기반 계약서 검토 웹

가이드라인/약관 PDF를 Chroma DB에 저장하고, 계약서를 30자 단위로 나눠 관련 기준을 검색한 뒤 GPT-4o mini가 문장별로 검토하는 Flask 웹입니다.

## 실행

```powershell
# OPENAI_API_KEY는 이미 시스템 환경 변수에 있다고 가정합니다.
python app.py
```

브라우저에서 `http://127.0.0.1:5000`을 엽니다.

별도 환경에서 설치할 때는 다음 최소 목록을 사용할 수 있습니다.

```powershell
pip install -r requirements-app.txt
```

현재 `requirements.txt`에는 실제 시스템의 전체 패키지 목록이 들어 있으며, 확인된 LangChain은 요청서의 0.3.x가 아니라 **1.3.11**입니다. 구현은 설치된 1.3.11 계열의 최신 분리 패키지 API(`langchain-openai`, `langchain-chroma`, `langchain-text-splitters`)에 맞췄습니다. 추가 설치가 필요한 패키지는 없습니다.

## 처리 방식

- RAG PDF: `PyPDFLoader` → 30자 청크 / 5자 오버랩 → `text-embedding-3-small` → 로컬 Chroma
- 계약서 PDF: `PyPDFLoader` → 30자 청크 / 오버랩 없음 → 유사 기준 4개 검색 → `gpt-4o-mini` 구조화 검토
- 검토 결과: SSE로 문장 하나씩 브라우저에 표시
- 일반 질문: RAG 검색 없이 `gpt-4o-mini`에 직접 요청
- 업로드/처리 진행: 웹 진행 막대 + 서버 콘솔 `tqdm`

## 주의

- 원본 업로드 PDF는 임시 파일로 읽고 즉시 삭제합니다. RAG 임베딩은 `data/chroma`에 남습니다.
- 이미지로만 된 스캔 PDF는 텍스트를 추출할 수 없습니다. 이 경우 OCR 전처리가 필요합니다.
- 메모리 기반 계약서 세션이므로 서버를 재시작하면 업로드한 계약서의 검토 버튼 상태는 초기화됩니다.
