# 아나바다 — 물건의 다음 이야기

크림색과 숲 초록색을 사용한 반응형 Flask 물품 공유 앱입니다.

## 디렉토리 구조

```text
share/
├── app.py                      # 앱 설정, 회원 관리, 검색, CRUD 라우팅
├── models.py                   # User / Item 모델
├── requirements-anabada.txt     # 이 프로젝트의 의존성
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── auth.html
│   ├── item_detail.html
│   ├── item_form.html
│   └── error.html
├── static/
│   ├── style.css
│   └── uploads/                 # 실행 시 생성
└── instance/                   # 실행 시 생성
    ├── anabada.db
    └── secret.key
```

## 실행 (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-anabada.txt
.\.venv\Scripts\python.exe app.py
```

브라우저에서 http://127.0.0.1:5000 에 접속합니다. SQLite DB와 업로드 폴더는 자동 생성됩니다. 기존 requirements.txt는 보존했습니다.

## 코드 읽는 순서

1. `app.py`의 `create_app`: Flask 설정, SQLite, 로그인 연결, CSRF 보호.
2. `models.py`: 사용자 비밀번호 해시와 User / Item 관계, 생성·수정 시각(UTC).
3. `app.py` 라우팅: 회원가입 → 로그인 → 목록 검색 → 상세 → 등록·수정 → 완료 전환 → 삭제.
4. `base.html` → `index.html` → `item_detail.html` → `item_form.html` → `auth.html`과 `static/style.css`.

## 기능과 동작

- 회원가입, 로그인, POST 로그아웃. 비밀번호는 해시로 저장합니다.
- 작성자만 수정·삭제·상태 변경 가능하며 서버에서 권한을 검사합니다.
- 제목·설명 검색, 무료 나눔 필터, 12개씩 페이지 이동.
- 가격 0원 또는 무료 체크 시 무료 나눔으로 표시합니다.
- 거래가능 ↔ 거래완료 전환. 완료된 물품도 목록에 표시합니다.
- 사진 선택은 선택 사항입니다. JPG/PNG/WEBP를 검증하고 최대 1600px JPEG로 저장합니다. 요청 전체 최대 8MB입니다. 교체·삭제 시 기존 사진을 삭제합니다.
- 폼에 CSRF 보호를 적용합니다. 사용자 텍스트는 Jinja2 자동 이스케이프를 사용합니다.
- 초기 목록은 비어 있습니다. 회원가입 후 직접 물품을 등록하세요.
- 거래 연락, 채팅, 결제는 포함하지 않습니다.

Bootstrap 및 웹폰트는 CDN을 사용하므로 인터넷 연결이 필요합니다. 자체 CSS는 로컬에 있습니다.

로컬 실습 서버는 기본적으로 디버그를 끕니다. 개발 중 필요하면 `$env:FLASK_DEBUG='1'`로 켜세요. 외부 배포에는 별도 WSGI 서버와 HTTPS, 로그인 시도 제한을 구성하세요. `SECRET_KEY` 환경변수로 고정 키를 지정할 수 있습니다. `instance/secret.key`와 DB는 공개 저장소에 올리지 마세요.

## 기능 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

임시 SQLite DB로 로그인, 이미지 업로드, 검색, 무료 필터, 작성자 권한, 수정·완료·삭제, CSRF를 검사합니다.
