# PDF RAG Chat

PDF 문서를 업로드하고, 문서 내용을 근거로 질문과 답변을 주고받을 수 있는 Flask 기반 웹 애플리케이션입니다.

## 주요 기능

- 여러 PDF 파일 동시 업로드
- PDF 텍스트 추출 및 검색 데이터 저장
- 이전 대화 맥락을 반영한 질문 처리
- 문서 내용에 근거한 한국어 답변
- 채팅 형태의 부드러운 실시간 답변 출력과 자동 스크롤
- 참고한 파일명, 페이지 및 문서 조각 표시
- 세션별 업로드 문서와 대화 기록 분리
- 문서와 대화 기록 초기화

## 프로젝트 구조

```text
local_rag/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── app.js
│   └── styles.css
└── tests/
    └── test_app.py
```

## 설치 및 실행

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:OPENAI_API_KEY="your-api-key"
python app.py
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python app.py
```

서버 실행 후 [http://127.0.0.1:5000](http://127.0.0.1:5000)에 접속합니다.

## 사용 방법

1. **PDF 업로드** 버튼으로 문서를 선택합니다.
2. 문서 처리가 끝나면 입력창에 질문을 작성합니다.
3. 실시간으로 출력되는 답변과 참고 문서를 확인합니다.
4. **새 대화 시작** 버튼으로 문서와 대화 기록을 초기화합니다.

한 번의 업로드 요청은 최대 50MB입니다. 이미지로만 구성된 스캔 PDF는 별도의 OCR 처리가 없으면 텍스트를 읽지 못할 수 있습니다.

## 환경 변수

| 변수 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | API 인증 키 |
| `FLASK_SECRET_KEY` | 운영 환경에서 사용할 세션 서명 키 |
| `FLASK_DEBUG` | `1`로 설정하면 디버그 모드 활성화 |

API 키와 비밀값은 GitHub에 커밋하지 않습니다.

## 테스트

```powershell
python -m unittest discover -s tests -v
```

## 커밋 제외 대상

가상환경, 캐시, 업로드 문서, 검색 데이터, 모델 파일과 환경 변수 파일은 `.gitignore`를 통해 커밋에서 제외됩니다.
