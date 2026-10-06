# PDF 번역기

PDF에서 텍스트를 추출해 OpenAI API로 번역하는 로컬 웹 앱입니다. 영어 → 한국어와 한국어 → 영어 번역을 지원하며, 번역 결과를 실시간으로 표시하고 TXT 파일로 내려받을 수 있습니다.

## 주요 기능

- PDF 원문 추출 및 페이지별 미리보기
- 영어 → 한국어, 한국어 → 영어 번역
- 긴 문서를 약 3,000자 단위로 나누어 순차 처리
- 진행률과 번역 결과 실시간 표시
- 번역 결과를 UTF-8 TXT 파일로 다운로드

## 준비 사항

- Python 3.10 이상 권장
- OpenAI API 키와 API 사용 가능 잔액
- 인터넷 연결
- 텍스트가 포함된 PDF

| 라이브러리 | 용도 |
|---|---|
| Flask | 로컬 웹 서버와 화면 제공 |
| pypdf | PDF 텍스트 추출 |
| openai | OpenAI Responses API를 이용한 번역 |

## 설치

Windows PowerShell에서 실행합니다.

```powershell
cd 'C:\Users\USER\Desktop\pdf_translator'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

이미 `.venv`가 있다면 가상환경 생성은 생략할 수 있습니다.

## OpenAI API 설정

프로그램을 실행할 PowerShell 창에 API 키를 설정합니다.

```powershell
$env:OPENAI_API_KEY = '본인의_API_키'
```

기본 모델은 `gpt-4.1-mini`입니다. 다른 모델을 쓰려면 다음 환경 변수를 추가합니다.

```powershell
$env:OPENAI_MODEL = '사용할_모델_이름'
```

API 키는 코드나 README에 직접 저장하지 마세요. 위 설정은 현재 PowerShell 창에만 적용됩니다.

## 실행

```powershell
cd 'C:\Users\USER\Desktop\pdf_translator'
.\.venv\Scripts\python.exe app.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)을 엽니다. 종료할 때는 PowerShell에서 `Ctrl+C`를 누릅니다.

## 사용 방법

1. **PDF 파일**에서 번역할 문서를 선택합니다.
2. **번역 방향**을 선택합니다.
3. **번역 시작**을 누릅니다.
4. 추출 원문과 실시간 번역 결과를 확인합니다.
5. 완료되면 **텍스트 다운로드**를 눌러 결과를 저장합니다.

번역 시 PDF에서 추출된 텍스트가 OpenAI API로 전송됩니다. 기밀 문서는 조직의 보안 정책과 데이터 처리 조건을 확인한 뒤 사용하세요.

## 지원 범위와 제한

| 항목 | 제한 |
|---|---|
| 파일 크기 | 최대 20MB |
| 페이지 수 | 최대 300페이지 |
| 추출 텍스트 | 최대 500,000자 |
| 메모리에 보관하는 작업 | 최대 20개 |
| 번역 방향 | 영어 ↔ 한국어 |

- 이미지로만 된 스캔 PDF는 OCR 처리가 먼저 필요합니다.
- 암호화된 PDF는 지원하지 않습니다.
- 표, 열 구성, 글꼴과 그림 등 원본 레이아웃은 보존하지 않습니다.
- 결과물은 번역문만 포함한 TXT 파일입니다.
- 작업 정보는 메모리에 있으므로 서버를 종료하면 사라집니다.
- 완료 후 1시간이 지난 작업은 새 작업 생성 시 정리됩니다.
- 로컬 실습용 단일 프로세스 앱이며 인터넷에 직접 공개하는 운영 서버 용도로 설계되지 않았습니다.

## 테스트

실제 API 호출 없이 업로드 검증, 텍스트 분할, 실시간 이벤트와 다운로드를 확인합니다.

```powershell
cd 'C:\Users\USER\Desktop\pdf_translator'
.\.venv\Scripts\python.exe smoke_test.py
```

성공하면 `PASS:`로 시작하는 메시지가 출력됩니다.

## 문제 해결

| 증상 | 확인할 내용 |
|---|---|
| `OPENAI_API_KEY` 안내 | 앱을 실행한 PowerShell에 API 키를 설정하고 서버를 다시 시작하세요. |
| 번역 실패 | API 키, 모델 접근 권한, API 사용 한도와 네트워크를 확인하세요. |
| 추출할 텍스트가 없음 | 스캔 PDF라면 OCR 처리 후 다시 시도하세요. |
| PDF를 읽을 수 없음 | 파일 손상 또는 암호화 여부를 확인하세요. |
| 연결이 끊김 | 서버가 계속 실행 중인지 확인하세요. 서버를 재시작했다면 번역도 다시 시작해야 합니다. |
| 5000번 포트 충돌 | 다른 프로그램이 포트를 쓰는지 확인하거나 `app.py` 마지막의 포트 값을 변경하세요. |

## 파일 구성

| 경로 | 설명 |
|---|---|
| `app.py` | PDF 검사, 텍스트 추출, 번역, 실시간 이벤트와 다운로드 처리 |
| `templates/index.html` | 업로드 화면과 진행률 표시 |
| `static/animal-farm-translation.png` | 화면의 농장 동물 이미지 |
| `requirements.txt` | 실행에 필요한 최소 라이브러리 |
| `requirements.original.txt` | 개발 환경의 전체 패키지 목록 기록 |
| `smoke_test.py` | 외부 API를 모의 처리하는 기본 동작 테스트 |

## 처리 흐름

```text
PDF 업로드
  → 파일·페이지 검사
  → 페이지별 텍스트 추출
  → 약 3,000자 단위 분할
  → OpenAI API로 순차 번역
  → 브라우저에 진행 상황 전송
  → UTF-8 TXT 파일 생성
```

이 문서는 `app.py`, 화면 템플릿, 의존성 파일과 테스트 코드를 기준으로 작성했습니다.
