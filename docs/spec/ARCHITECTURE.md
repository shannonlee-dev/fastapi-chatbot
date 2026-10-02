# 아키텍처

이 문서는 애플리케이션 구조, 모듈 책임과 모듈 간 인터페이스를 설명합니다. 구현 변경으로
이 계약이 달라지는 경우 코드와 이 문서를 같은 변경에서 함께 갱신합니다. HTTP 결과, DB 스키마,
프런트엔드 동작, 실행·배포 설정의 상세값은 각 기술 문서에서 정의합니다.

## 구조 개요

애플리케이션은 하나의 FastAPI 프로세스 안에서 책임별 모듈을 분리하는 모듈형 모놀리식 구조입니다.

```text
Browser
   |
   v
FastAPI (Main + Auth + UI + Chat + Admin + Core)
   |                                      |
   v                                      v
SQLite                                OpenAI API
```
## 주요 구성요소

| 구성요소 | 역할 |
| --- | --- |
| 브라우저 | 회원가입·로그인, 질문 입력, AI 답변과 본인 기록 확인, 관리자 운영 메타데이터 조회 |
| `src/chatbot/main.py` | FastAPI 애플리케이션 생성, SessionMiddleware와 라우터 등록, DB·관리자 초기화 조립 |
| `src/chatbot/auth` | 사용자, 회원가입·로그인·로그아웃, 비밀번호 검증, 인증·관리자 의존성 |
| `src/chatbot/chat` | 질문 검증, OpenAI 호출, 사용자 ChatExchange 저장·조회 |
| `src/chatbot/admin` | 관리자 전용 경로와 운영 메타데이터 조회 |
| `src/chatbot/core` | 환경 변수, SQLAlchemy Base·DB 세션, 보안, 요청 ID, 공통 로깅 |
| `src/chatbot/ui` | Jinja2 화면 라우터, 대화·본인 기록·관리자 템플릿, CSS·JavaScript static asset |
| SQLite | 사용자, 질문·답변 쌍, 상태, UTC 시각, 요청별 운영 메타데이터 저장 |
| OpenAI API | 현재 질문과 사용자별 최근 성공 문맥으로 답변 생성 |

## 디렉토리 구조

```text
src/chatbot/
├── main.py
├── admin/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   └── schemas.py
├── auth/
├── chat/
├── core/
└── ui/
    ├── router.py
    ├── templates/
    └── static/
```

## 모듈 경계

> 🧱 파일 소유권은 동시 수정 충돌을 줄이기 위한 기본 경계입니다. 공용 파일 변경은
> 관련 담당자와 합의한 뒤 PR에 명시합니다.

### 모듈 책임과 소유권

| 경로·영역 | 책임 | 소유자 |
| --- | --- | --- |
| `src/chatbot/main.py` | 애플리케이션 생성, SessionMiddleware, 라우터 등록, 상태, DB·관리자 초기화 | 김대웅 |
| `src/chatbot/auth/**` | 사용자, 회원가입·로그인·로그아웃, 비밀번호, 인증·관리자 의존성 | 김대웅 |
| `src/chatbot/chat/**` | 질문 검증, OpenAI 호출, 사용자 ChatExchange 저장·조회 | 이상헌 |
| `src/chatbot/admin/**` | 관리자 전용 경로와 운영 메타데이터 조회 | 이상헌 |
| `src/chatbot/core/database.py` | SQLAlchemy Base, 엔진, 세션 factory와 요청별 DB 세션 | 이상헌 |
| `src/chatbot/core/db_types.py` | SQLAlchemy 모델 공용 UTC datetime 타입과 default factory | 이상헌 |
| `src/chatbot/core/config.py` | 환경 변수 로딩·타입 변환·검증 | 이상헌 |
| `src/chatbot/core/request_id.py` | HTTP 요청 ID 생성·전달 인터페이스 | 김대웅 |
| `src/chatbot/core/security.py` | 비밀번호·세션 보안 보조 함수 | 김대웅 |
| 공통 로깅·상태 | 로그 설정과 필수 이벤트 형식, `GET /health` | 김대웅 |
| `src/chatbot/ui/**` | HTML·폼 라우터, 템플릿, CSS·JavaScript, 화면 흐름 | 김우종 |

### 공통 원칙

- 의존 방향은 `Main·Router → Service → Repository → Core`입니다.
- `src/chatbot/main.py`는 라우터·미들웨어·모델·DB 초기화를 조립하고 business rule을 구현하지 않습니다.
- 라우터는 HTTP·폼·템플릿 변환, 서비스는 사용 흐름과 트랜잭션, 저장소는 DB 조회·변경만 담당합니다.
- 저장소는 `commit()`하지 않습니다. 쓰기 사용 흐름의 서비스가 성공 시 `commit()`, 실패 시 `rollback()`합니다.
- `src/chatbot/chat`은 인증이 제공한 `user_id: int`만 사용하며 쿠키와 사용자 조회 방식을 알지 않습니다.
- `src/chatbot/admin`은 관리자 read-side 예외로 `app.auth.models.User`와
  `app.chat.models.ChatExchange` ORM 모델을 읽기 전용 쿼리에 직접 사용할 수 있습니다. 관리자는
  인증·대화 서비스 또는 저장소를 조합 호출하지 않습니다.
- `src/chatbot/ui`는 인증·대화 서비스를 호출하고 저장소와 OpenAI를 직접 호출하지 않습니다.
  `admin_logs.html`과 공통 CSS·JavaScript 등 관리자 표현 자원은 제공하지만 `/admin/logs` 경로와
  관리자 데이터 조합은 소유하지 않습니다.

## 공유 인터페이스

### 설정

`src/chatbot/core/config.py`는 환경 변수의 로딩, 타입 변환과 값 자체의 검증을 담당합니다.
정확한 설정 키, 기본값과 환경별 값은 [실행·배포 계약](DEPLOYMENT.md)에서 정의합니다. 각 business
모듈은 자신이 소비하는 설정의 use-case 조건을 검증합니다.

### 데이터베이스

```python
from chatbot.core.database import Base, SessionLocal, get_db, init_db
```

- `Base`, 엔진과 세션 factory는 `src/chatbot/core/database.py`에서만 생성합니다.
- `get_db()`는 요청별 세션을 열고 반드시 닫으며 자동 커밋하지 않습니다.
- `User`와 `ChatExchange`는 같은 `Base`를 사용합니다.
- `src/chatbot/main.py`가 두 모델을 import한 뒤 `init_db()`를 호출합니다.
- SQLite 연결과 스키마의 상세 동작은 [DB 스키마 계약](db/DB.md)을 따릅니다.

### 요청 ID

```python
from chatbot.core.request_id import RequestIdMiddleware, get_request_id
```

- `RequestIdMiddleware`는 HTTP 요청마다 서버-generated UUID를 생성하고
  `request.state.request_id`에 저장합니다.
- 클라이언트가 보낸 요청 ID는 신뢰하거나 서버 요청 ID로 재사용하지 않습니다.
- `get_request_id()`는 라우터가 현재 요청 ID를 서비스에 전달하는 공용 인터페이스입니다.
- 응답의 `X-Request-ID`, 서버 로그와 `ChatExchange.request_id`는 같은 값을 사용합니다.
- 공통 기반는 공통 로깅 설정을 제공하고, 라우터는 요청 ID를 서비스에 전달합니다. 각 서비스는
  자신이 소유한 요청 수신, 외부 API 호출과 영속 저장 성공·실패 이벤트를 애플리케이션 로깅
  인터페이스로 기록합니다.

### 인증 → UI·대화

```python
from chatbot.auth.service import (
    authenticate_user,
    ensure_initial_admin,
    register_user,
)
from chatbot.auth.dependencies import (
    AuthenticatedUser,
    clear_session_user_id,
    get_current_user_id,
    get_optional_authenticated_user,
    get_session_user_id,
    require_authenticated_user,
    require_admin,
    set_session_user_id,
)
```

```python
def register_user(*, db: Session, username: str, password: str) -> User: ...
def authenticate_user(*, db: Session, username: str, password: str) -> User | None: ...
def ensure_initial_admin(*, db: Session, app_settings: Settings) -> None: ...
def set_session_user_id(request: Request, *, user_id: int) -> None: ...
def get_session_user_id(request: Request) -> int | None: ...
def clear_session_user_id(request: Request) -> None: ...
def get_current_user_id(request: Request) -> int: ...
def get_optional_authenticated_user(...) -> AuthenticatedUser | None: ...
def require_authenticated_user(...) -> AuthenticatedUser: ...
def require_admin(...): ...
```

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    is_admin: bool
```

- `User`는 역할을 저장하는 `role` 필드를 포함합니다. 일반 회원가입 계정은 일반 사용자,
  초기 관리자 계정은 관리자 역할로 생성합니다.
- `ensure_initial_admin()`은 시작 시 `role=admin` 계정 존재 여부를 확인합니다. 사용자명과 관계없이
  관리자 역할 계정이 하나라도 있으면 기존 계정을 변경하지 않고 종료합니다.
- 관리자 역할 계정이 없으면 `create_app()`에서 전달된 실행 설정의 초기 관리자 비밀번호를
  검증·해시하여 `ADMIN_USERNAME`의 사용자명, 역할 `admin`인 초기 계정을 생성합니다. 이때 설정한
  사용자명이 일반 사용자 역할로 이미 존재하면 자동 승격하지 않고 명확한 설정 오류로 시작을 중단합니다.
- 초기 관리자 생성이 필요한데 비밀번호가 누락되었거나 유효하지 않으면 시작을 중단하고 원인을
  식별 가능한 로그에 남깁니다. 초기 비밀번호 원문은 기록하지 않습니다.
- 인증은 세션에 사용자 ID를 저장·조회·삭제하는 공개 보조 함수의 mechanics를 소유합니다.
  UI 라우터는 세션 키를 직접 읽거나 쓰지 않고, 로그인 인증 성공과 로그아웃 요청에서 이 보조 함수를
  호출합니다.
- `get_current_user_id()`는 JSON API가 로그인 사용자 ID를 얻는 공개 의존성입니다.
- `get_optional_authenticated_user()`는 세션의 사용자 ID를 실제 `users` 기록과 대조해 유효한
  `AuthenticatedUser` 또는 `None`을 반환하고, 형식이 잘못됐거나 대응 사용자가 없는 만료된 세션은
  제거합니다. 로그인·회원가입 화면은 이 결과로 로그인 사용자를 `/chat`으로 이동시킵니다.
- `require_authenticated_user()`는 HTML 보호 화면이 사용하는 인증-owned 공개 의존성입니다.
  Optional 의존성을 재사용해 `user_id`와 `is_admin`만 포함한 `AuthenticatedUser`를 반환합니다.
  유효한 사용자가 없으면 `303 /login`으로 이동시킵니다.
- `require_admin()`은 관리자 HTML 화면이 사용하는 공개 의존성이며 사용자 조회와 역할 판별을
  인증 모듈 안에서 수행합니다.
- `AuthenticatedUser`는 UI용 최소 read 모델이며 ORM `User`, 사용자명, `role` 원문이나
  `password_hash`를 UI에 전달하지 않습니다. UI 라우터는 인증 저장소나 사용자 모델을 직접
  import하지 않고 `is_admin`으로 관리자 탐색 렌더링 여부만 결정합니다.
- `require_authenticated_user()`는 현재 UI 라우터 구현 전에 인증 모듈에 추가되어야 하는 통합
  prerequisite입니다. 이 인터페이스가 추가될 때 인증 의존성 테스트와 이 문서를 함께 갱신합니다.
- 외부 HTTP 결과는 [API 계약](api/API.md)을 따르며 UI는 인증과 관리자 권한을 최종 판별하지 않습니다.

### 대화 → 인증·UI

- 대화는 인증이 제공한 사용자 식별자와 요청 ID를 받아 질문을 처리하고, 사용자 소유 대화 기록을
  제공합니다.
- 질문의 Pydantic 검증, OpenAI 호출과 메시지 구성은 각각 [API 계약](api/API.md)과
  [AI 호출 계약](ai/AI.md)을 따릅니다.
- 사용자용 이력은 안전한 필드만 제공하며, 내부 `error_message`와 운영 메타데이터는 포함하지
  않습니다. HTTP 결과는 [API 계약](api/API.md)을 따릅니다.

### 관리자 → 인증·UI·앱 진입점

```python
from chatbot.admin.service import list_admin_chat_operation_metadata
from chatbot.admin.router import router as admin_router
from chatbot.auth.dependencies import require_admin
```

- `src/chatbot/admin/router.py`가 `GET /admin/logs`를 소유하며, 관리자는 화면에 허용된 운영 메타데이터만
  제공합니다. 표시 필드는 [DB 스키마 계약](db/DB.md)을 따릅니다.
- 관리자는 별도 JSON API, 수정·삭제 CRUD, 고급 검색·페이지 단위 조회, 별도 운영 로그 테이블, 별도
  역할·권한 테이블을 제공하지 않습니다. 사용자 역할은 `users.role`을 사용합니다.
- 앱 진입점은 `admin_router` 등록만 담당합니다.

### UI·앱 진입점 통합

- `src/chatbot/ui`의 화면 구조, 브라우저 상태, 상호작용, 접근성, 반응형 동작은
  [프런트엔드 UI 계약](ui/UI.md)을 따릅니다.
- UI 라우터는 인증·대화 서비스와 인증 세션 보조 함수를 사용해 사용자 화면 흐름을 구성하고,
  대화 라우터는 인증과 DB 의존성을 대화 JSON API에 연결합니다. 경로와 HTTP 결과의 상세
  계약은 [API 계약](api/API.md)을 따릅니다.
- UI 라우터는 `GET /`, 회원가입·로그인·로그아웃 폼 경로와 `GET /chat`을 소유합니다. 관리자 라우터가
  이미 소유한 `GET /admin/logs`를 중복 등록하지 않습니다.
- 관리자 라우터는 권한 의존성과 관리자 서비스를 연결해 읽기 전용 운영 메타데이터를 UI 템플릿에
  전달합니다.
- `src/chatbot/main.py`는 `src/chatbot/ui/router.py`의 라우터를 한 번 등록하고 `src/chatbot/ui/static`을 `/static`에 연결합니다.
  UI asset은 인증 없이 조회할 수 있지만 템플릿과 JavaScript 외의 business API를 제공하지 않습니다.
- `src/chatbot/main.py`는 UI·대화·관리자 라우터, static 연결, SessionMiddleware, 로깅, 상태,
  `init_db()`를 연결하고, DB 초기화 후 요청을 받기 전에 `create_app()`이 선택한 실행 설정을 전달하여
  `ensure_initial_admin()`을 호출합니다.
- 서버 로그는 요청 수신, AI 호출·응답, DB 저장 성공·실패를 애플리케이션 로깅으로 남깁니다.
  `/admin/logs`는 서버 실행 환경 로그 파일을 표시하는 화면이 아닙니다.

## 개념적 요청 흐름

### 로그인과 로그아웃

UI 라우터가 폼을 HTTP 입력으로 변환하고 인증 서비스를 호출합니다. 인증 성공 또는 로그아웃 요청이면
인증이 제공하는 보조 함수로 세션 사용자 ID를 저장하거나 삭제하고, 라우터가 API 계약에 맞는 화면
이동을 반환합니다.

### 대화

인증된 사용자의 질문을 처리해 HTTP 응답으로 반환하며, UI는 브라우저 상태에 맞게 표시합니다.

### 관리자 조회

관리자만 운영 메타데이터를 조회할 수 있으며 UI 템플릿은 허용된 필드만 표시합니다.

## 핵심 제약

- 사용자마다 하나의 연속 대화만 제공
- 새 대화·대화방 선택·대화방 목록 없음
- `chat_exchanges` 한 기록은 질문과 답변 한 쌍
- 다른 사용자의 기록과 실패 기록은 AI 문맥에서 제외
- 사용자 기록은 `/chat` 화면과 본인 소유 기록만 반환하는 대화 기록 API에서 조회
- 관리자 수정·삭제 기능과 별도 로그 테이블 없음
- 초기 버전은 OpenAI 자동 재시도 없음
- 시간 제한·API 오류·비정상 OpenAI 응답에는 생성된 대체 답변을 사용하지 않고 실패
  기록을 저장한 뒤 API layer가 오류 응답으로 변환
- 스키마와 영속 저장 제약의 상세 계약은 [DB 스키마 계약](db/DB.md)을 따름
