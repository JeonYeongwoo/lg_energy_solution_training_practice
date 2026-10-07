# 고객사 VOC 분석 Agent

CrewAI, Gradio, Plotly를 활용해 고객사 VOC CSV를 분석하고 Word 보고서를 생성하는 실습 프로젝트입니다.

CSV 파일을 업로드하면 다음 작업을 수행합니다.

- 산업군·제품명·분야별 VOC 통계 분석
- Plotly 비율 막대그래프 생성
- 불만 내용의 핵심 키워드 추출 및 워드클라우드 생성
- 산업군별 주요 이슈와 개선 과제 도출
- 통계·워드클라우드·이슈·대응 방안이 포함된 Word 보고서 생성

모든 기능은 [`voc_analysis_agent.py`](./voc_analysis_agent.py) 파일 하나에 구현되어 있습니다.

## 1. 주요 화면

Gradio 웹 화면은 다음 네 가지 메뉴로 구성됩니다.

1. **파일 업로드**
   - VOC CSV 파일 업로드
   - 필수 열과 데이터 형식 검증
   - 업로드 데이터 미리보기
2. **통계 분석**
   - 산업군, 제품명, 분야 중 분석 항목 선택
   - 항목별 건수와 비율 계산
   - 비율을 소수점 둘째 자리까지 표시한 Plotly 막대그래프 출력
3. **워드클라우드**
   - 불만 내용에서 2자 이상의 한글·영문 키워드 추출
   - 기본 조사와 일반적인 불용어 제거
   - 한글 폰트를 적용한 워드클라우드 및 상위 키워드 출력
4. **보고서 생성**
   - CrewAI Agent 순차 실행
   - 산업군별 주요 이슈와 개선 과제 도출
   - Word 형식의 VOC 분석 보고서 생성 및 다운로드

각 작업의 처리 단계와 오류는 화면 하단의 진행 로그에서 확인할 수 있습니다.

## 2. Agent 구성

보고서 생성 시 세 Agent가 순차적으로 협업합니다.

```text
CSV 데이터
   │
   ▼
voc agent
통계 및 VOC 집중 구간 분석
   │
   ▼
issue agent
산업군별 주요 이슈와 개선 과제 도출
   │
   ▼
report agent
경영진 요약 및 Word 보고서 문안 작성
```

### voc agent

- 산업군·분야별 구성비와 교차 분포 분석
- VOC 표본에서 대표 내용 확인
- 데이터만으로 판단하기 어려운 분석 한계 표시

### issue agent

- 산업군별 주요 VOC 분석
- 주요 이슈와 근거 정리
- 담당 조직이 실행할 수 있는 개선 과제 도출

### report agent

- 한 줄 결론과 핵심 사실 작성
- 우선 실행 과제 정리
- Word 보고서용 경영진 요약 생성

OpenAI API 호출이 실패하거나 API 키가 없을 때는 규칙 기반 분석으로 자동 전환합니다. 따라서 통계, 워드클라우드와 Word 보고서는 계속 생성할 수 있습니다.

## 3. 실행 환경

- Python 3.10 이상 권장
- Windows 권장
- `OPENAI_API_KEY` 환경변수
- 프로젝트의 [`requirements.txt`](./requirements.txt)에 정의된 패키지 사용

주요 확인 패키지 버전은 다음과 같습니다.

| 패키지 | 버전 |
|---|---:|
| crewai | 1.15.1 |
| gradio | 6.19.0 |
| openai | 2.44.0 |
| pandas | 2.2.3 |
| plotly | 6.8.0 |
| wordcloud | 1.9.6 |
| python-docx | 1.2.0 |
| kaleido | 1.3.0 |

## 4. 설치

PowerShell에서 프로젝트 폴더로 이동합니다.

```powershell
cd E:\KBA_AI\work\client_VOC_analysis
```

가상환경 사용을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

현재 PC 환경과 동일한 패키지를 설치합니다.

```powershell
python -m pip install -r requirements.txt
```

## 5. OpenAI API 키 설정

현재 PowerShell 창에서만 API 키를 설정하려면 다음 명령을 사용합니다.

```powershell
$env:OPENAI_API_KEY="여기에_API_KEY_입력"
```

사용할 모델을 변경하려면 `VOC_LLM_MODEL`을 설정합니다. 기본값은 `openai/gpt-4o-mini`입니다.

```powershell
$env:VOC_LLM_MODEL="openai/gpt-4o-mini"
```

> API 키를 코드나 CSV 파일에 직접 저장하지 마세요.

## 6. 실행

다음 명령을 실행합니다.

```powershell
python voc_analysis_agent.py
```

Gradio 서버가 실행되면 기본 웹 브라우저가 자동으로 열립니다.

일반적으로 다음 주소를 사용합니다.

```text
http://127.0.0.1:7860
```

## 7. CSV 파일 형식

업로드 CSV에는 다음 열이 모두 있어야 합니다.

| 열 이름 | 설명 | 예시 |
|---|---|---|
| 순번 | VOC 식별 번호 | 1 |
| 일자 | VOC 접수 일자 | 2026-10-01 |
| 고객명 | 고객사 또는 고객 이름 | 가나상사 |
| 산업군 | 고객 산업 분류 | 제조 |
| 지역 | 고객 지역 | 서울 |
| 제품명 | 대상 제품 | Alpha |
| 분야 | 불만 유형 또는 업무 분야 | 품질 |
| 불만 | 고객의 VOC 원문 | 제품 오류가 반복되고 응답이 늦습니다 |

CSV 예시는 다음과 같습니다.

```csv
순번,일자,고객명,산업군,지역,제품명,분야,불만
1,2026-10-01,가나상사,제조,서울,Alpha,품질,제품 오류가 반복되고 응답이 늦습니다
2,2026-10-02,다라은행,금융,부산,Beta,지원,고객 지원 응답이 늦고 설명이 부족합니다
3,2026-10-03,마바테크,제조,경기,Alpha,성능,처리 속도가 느리고 오류가 발생합니다
```

지원하는 문자 인코딩은 다음과 같습니다.

- UTF-8 with BOM
- UTF-8
- CP949
- EUC-KR

## 8. Word 보고서 구성

생성된 보고서는 다음 내용을 포함합니다.

1. 의사결정 요약
2. 분석 범위와 기준
3. 산업군별 VOC 통계
4. 분야별 VOC 통계
5. 제품별 VOC 통계
6. 불만 키워드 워드클라우드
7. 산업군별 주요 이슈와 개선 과제
8. 공통 대응 방안
9. VOC 분석 메모

보고서는 Windows의 `맑은 고딕`을 기준으로 생성하여 한글 깨짐을 방지합니다.

## 9. 한글 폰트

### 웹 UI

- 제목·탭·버튼: `Jua`
- 본문: `Gowun Dodum`
- 웹 폰트 연결 실패 시: 맑은 고딕 또는 시스템 한글 폰트

### 워드클라우드

프로그램은 운영체제에서 다음 한글 폰트를 순서대로 탐색합니다.

- Windows: 맑은 고딕
- Linux: Noto Sans CJK 또는 나눔고딕
- macOS: Apple SD Gothic Neo

자동으로 폰트를 찾지 못하면 `VOC_KOREAN_FONT` 환경변수에 직접 경로를 지정할 수 있습니다.

```powershell
$env:VOC_KOREAN_FONT="C:\Windows\Fonts\malgun.ttf"
```

## 10. 개인정보 및 보안

CrewAI 분석을 실행하면 다음 필드의 일부 표본이 OpenAI API로 전송됩니다.

- 산업군
- 제품명
- 분야
- 불만 내용

`고객명`과 `지역`은 LLM 전송 데이터에서 제외됩니다. 다만 불만 원문 자체에 개인정보나 기밀정보가 포함될 수 있으므로 업로드 전에 반드시 비식별화하고 회사의 데이터 처리 정책을 확인하세요.

## 11. 문제 해결

### `OPENAI_API_KEY` 관련 오류

환경변수 설정 여부를 확인합니다.

```powershell
Test-Path Env:OPENAI_API_KEY
```

API 키가 없어도 규칙 기반 분석으로 Word 보고서를 생성할 수 있습니다.

### CSV 필수 열 누락 오류

CSV 첫 행의 열 이름이 아래 값과 정확히 일치하는지 확인합니다.

```text
순번, 일자, 고객명, 산업군, 지역, 제품명, 분야, 불만
```

열 이름 앞뒤의 공백은 자동으로 제거되지만 다른 이름으로 작성된 열은 자동 변환하지 않습니다.

### 한글이 깨지는 경우

CSV를 UTF-8 with BOM 또는 CP949로 다시 저장한 후 업로드합니다. 워드클라우드 폰트 오류라면 `VOC_KOREAN_FONT`에 한글 폰트 파일의 절대 경로를 지정합니다.

### 보고서 그래프가 이미지로 들어가지 않는 경우

화면의 Plotly 그래프는 정상 표시되지만, PC의 Kaleido 실행 환경에 따라 Word 보고서의 그래프 이미지 변환이 제한될 수 있습니다. 이 경우에도 통계표와 워드클라우드는 보고서에 포함됩니다.

### 기본 포트가 이미 사용 중인 경우

다른 Gradio 또는 Python 프로그램을 종료한 후 다시 실행합니다. 필요하면 `voc_analysis_agent.py` 마지막의 `launch()` 호출에 `server_port` 값을 추가할 수 있습니다.

## 12. 프로젝트 파일

```text
client_VOC_analysis/
├─ voc_analysis_agent.py   # 전체 애플리케이션
├─ requirements.txt        # 현재 PC의 패키지 버전
├─ requirements_2.txt      # 추가 보관본
└─ README.md               # 사용 설명서
```


