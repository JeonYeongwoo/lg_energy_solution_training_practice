# LG 에너지솔루션 연계 교육 과정 — AI 융합모듈 실습 프로젝트

**본 저장소는 「LG 에너지솔루션 연계 - 배터리 AI 융합 인력 양성 과정」의 「AI 융합모듈」에서 사용한 프로젝트를 모아 놓은 실습 저장소입니다.**

일상적인 문제를 해결하는 네 가지 애플리케이션을 통해 웹·데스크톱 UI, 데이터 관리, 외부 API 연동과 AI 서비스 구현을 살펴볼 수 있습니다. 각 프로젝트는 독립적으로 실행하며, 세부 기능과 사용법은 해당 폴더의 README에서 확인할 수 있습니다.

- 저장소: [lg_energy_solution_training_practice](https://github.com/JeonYeongwoo/lg_energy_solution_training_practice)
- 교육 과정: LG 에너지솔루션 연계 - 배터리 AI 융합 인력 양성 과정
- 사용 모듈: AI 융합모듈

## 프로젝트 한눈에 보기

| 프로젝트 | 주요 내용 | 사용 기술 | 실행 형태 |
| --- | --- | --- | --- |
| [냉장고 미니홈피](./cuision_recommendation/README.md) | 보유 재료 기반 메뉴 추천, 단계별 조리 안내, 재고 관리 | HTML, CSS, JavaScript, localStorage, PWA | 정적 웹앱 |
| [아나바다 — 물건의 다음 이야기](./flea_market/README.md) | 회원 관리, 물품 등록·검색·수정·삭제, 무료 나눔 및 거래 상태 관리 | Python, Flask, Flask-SQLAlchemy, Flask-Login, SQLite, Pillow | 웹앱 |
| [PDF 번역기](./pdf_translator/README.md) | PDF 텍스트 추출, 영어·한국어 양방향 번역, TXT 다운로드 | Python, Flask, pypdf, OpenAI API | 웹앱 |
| [냥튜브 — 유튜브 다운로더](./youtube_downloader/README.md) | 영상 정보 분석, 포맷 선택, 영상·음원 다운로드 | Python, PyQt5, yt-dlp, FFmpeg | 데스크톱 GUI |

## 프로젝트별 소개

### 1. 냉장고 미니홈피 (`cuision_recommendation`)

냉장고의 재료를 관리하고 조리 시간이 짧고 설거지가 적은 메뉴를 추천하는 모바일 중심 웹앱 프로토타입입니다.

- 사진 촬영·선택 및 샘플 재료 인식 흐름 제공
- 재료명, 수량, 유통기한 편집과 알레르기·기피 재료·조리도구 설정
- 보유 재료와 조리도구에 맞는 메뉴를 최대 3개 추천
- 단계별 조리법, 타이머, 요리 완료 후 재고 반영 및 만족도 평가
- 브라우저 로컬 저장과 서비스 워커 기반 정적 자산 캐싱

현재 사진 분석은 실제 이미지 인식 API 대신 고정된 샘플 재료를 반환합니다. 추천은 내장된 4개 레시피와 규칙 기반 정렬을 사용하며, 별도 백엔드나 사용자 계정은 없습니다. 제품 요구사항은 [PRD.md](./cuision_recommendation/PRD.md)에 정리되어 있습니다.

### 2. 아나바다 (`flea_market`)

사용자가 물품을 등록하고 무료 나눔 또는 거래 물품을 찾아볼 수 있는 반응형 Flask 웹앱입니다.

- 회원가입·로그인·로그아웃과 비밀번호 해시 저장
- 물품 등록·상세 조회·수정·삭제 및 작성자 권한 검사
- 제목·설명 검색, 무료 나눔 필터와 페이지 이동
- 거래 가능·거래 완료 상태 전환
- 사진 업로드·검증·크기 조정과 CSRF 보호

사용자와 물품 정보는 SQLite에 저장합니다. 채팅, 결제, 거래 연락 기능은 포함되어 있지 않습니다.

### 3. PDF 번역기 (`pdf_translator`)

텍스트가 포함된 PDF에서 원문을 추출하고 OpenAI API로 번역하는 로컬 웹앱입니다.

- 영어 → 한국어 및 한국어 → 영어 번역
- 페이지별 원문 확인과 약 3,000자 단위 분할 처리
- 번역 진행률과 결과 실시간 표시
- UTF-8 TXT 파일 다운로드

`OPENAI_API_KEY` 환경변수가 필요하며, 코드의 기본 모델은 `gpt-4.1-mini`입니다. `OPENAI_MODEL`로 모델을 변경할 수 있습니다. 스캔 PDF의 OCR과 원본 PDF 레이아웃 보존은 지원하지 않습니다.

### 4. 냥튜브 (`youtube_downloader`)

YouTube 영상 링크를 입력하고 원하는 포맷을 선택해 저장하는 한국어 데스크톱 프로그램입니다.

- 영상 제목·길이·포맷·해상도·비트레이트·파일 크기 조회
- 저장 폴더 선택과 다운로드 진행률·속도·남은 시간 표시
- 영상 전용 포맷과 음원을 받아 FFmpeg로 MKV 병합
- 링크·네트워크·접근·저장 오류 안내

한 번에 영상 하나를 처리합니다. 재생목록 일괄 다운로드, MP3 변환, 로그인·쿠키 입력은 지원하지 않습니다.

## 저장소 구조

```text
lg_energy_solution_training_practice/
├── README.md
├── cuision_recommendation/
│   ├── README.md
│   ├── PRD.md
│   └── app/
│       ├── dist/                     # 실행 가능한 HTML·CSS·JavaScript
│       └── site-bundle.tar.gz         # 정적 사이트 번들
├── flea_market/
│   ├── README.md
│   ├── app.py
│   ├── models.py
│   ├── requirements-anabada.txt       # 앱 실행용 의존성
│   ├── templates/
│   ├── static/
│   ├── instance/                     # SQLite DB 및 로컬 설정
│   └── tests/
├── pdf_translator/
│   ├── README.md
│   ├── app.py
│   ├── requirements.txt
│   ├── smoke_test.py
│   ├── templates/
│   └── static/
└── youtube_downloader/
    ├── README.md
    ├── main.py
    └── requirements.txt
```

> `cuision_recommendation`은 저장소에 등록된 실제 폴더명입니다. 위 구조는 주요 파일만 표시합니다.

## 시작하기

아래 명령은 Windows PowerShell 기준입니다. Git과 Python을 준비하고, Python 앱은 프로젝트별 가상환경에 의존성을 설치합니다. Python 3.10 이상 사용을 권장합니다.

### 저장소 복제

```powershell
git clone https://github.com/JeonYeongwoo/lg_energy_solution_training_practice.git
cd lg_energy_solution_training_practice
```

다음 실행 예시는 각각 **저장소 루트에서 시작**합니다.

### 냉장고 미니홈피

```powershell
cd cuision_recommendation/app/dist
python -m http.server 8000
```

브라우저에서 [http://localhost:8000](http://localhost:8000)에 접속합니다. 별도 패키지 설치나 빌드는 필요하지 않습니다.

### 아나바다

```powershell
cd flea_market
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-anabada.txt
.\.venv\Scripts\python.exe app.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)에 접속합니다.

### PDF 번역기

```powershell
cd pdf_translator
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:OPENAI_API_KEY = '본인의_API_키'
.\.venv\Scripts\python.exe app.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)에 접속합니다. API 사용에 따른 비용이 발생할 수 있으며, 번역할 텍스트는 OpenAI API로 전송됩니다. API 키는 저장소에 커밋하지 마세요.

아나바다와 PDF 번역기는 기본적으로 같은 5000번 포트를 사용하므로 하나씩 실행하거나 코드에서 포트를 변경해야 합니다.

### 냥튜브

```powershell
cd youtube_downloader
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

영상·음원 병합에는 [FFmpeg](https://ffmpeg.org/download.html)가 필요합니다. 설치 후 실행 파일이 있는 폴더를 `PATH`에 등록하고 `ffmpeg -version`으로 확인하세요.

## 실습에서 살펴볼 내용

- **서비스 기획과 UI 구성:** 사용자 흐름, 반응형 화면, 입력과 진행 상태 표현
- **웹 애플리케이션 개발:** Flask 라우팅, 템플릿, 사용자 인증, 파일 업로드
- **데이터 관리:** SQLite 모델링, CRUD, 브라우저 로컬 저장
- **AI API 활용:** PDF 텍스트 전처리, 분할 번역, 실시간 결과 전달
- **데스크톱 개발:** PyQt5 화면, 백그라운드 작업, 다운로드 진행 상태 처리
- **기본 검증:** 웹앱 기능 테스트와 외부 API를 모의 처리하는 스모크 테스트

## 포함된 테스트

각 프로젝트 폴더에서 의존성을 설치한 뒤 실행합니다.

```powershell
# flea_market 폴더에서 실행
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# pdf_translator 폴더에서 실행
.\.venv\Scripts\python.exe smoke_test.py
```

아나바다 테스트는 인증·물품 관리·검색·이미지·권한·CSRF를 검사합니다. PDF 번역기 스모크 테스트는 실제 API 호출 없이 업로드 검증, 텍스트 분할, 실시간 이벤트와 다운로드를 확인합니다. 자세한 지원 범위와 제한은 각 프로젝트 README를 참고하세요.
