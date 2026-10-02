# API 계약

이 문서는 현재 저장소가 따르는 HTTP/API 계약을 정의합니다. 구현 변경으로 계약이 달라지는
경우 코드와 이 문서를 같은 변경에서 함께 갱신합니다. 이 문서는 구현 완료 상태를 의미하지 않습니다.

## 1. 공통 계약

| 항목 | 계약 |
| --- | --- |
| 인증 | Starlette `SessionMiddleware`의 서명된 세션 쿠키 사용. JWT·토큰 인증 없음 |
| 세션 데이터 | 로그인 사용자 ID만 저장. 서명되지만 암호화된 저장소로 간주하지 않음 |
| Secret 키 | SessionMiddleware는 애플리케이션 실행 설정에서 제공되는 세션 비밀값을 사용. 설정 키와 환경별 값은 [실행·배포 계약](../DEPLOYMENT.md)을 따름 |
| 만료 | 8시간(`max_age=28800`) |
| 쿠키 | `HttpOnly=true`, `SameSite=Lax`, 배포 환경 `Secure=true` |
| 요청 ID | 서버가 요청마다 생성하고 `X-Request-ID` 응답 헤더로 반환. 클라이언트 제공 값은 재사용하지 않음 |
| 관리자 | `users.role`로 판별. 초기 관리자 생성는 [아키텍처](../ARCHITECTURE.md)의 인증 계약을 따름 |
| 시간 | DB와 API는 UTC ISO 8601(`Z`) 사용. HTML의 사용자 표시만 UI 계약에 따라 KST로 변환 |
| 내부정보 | SQL 오류, 전체 기술 구성, 키, 쿠키, 내부 `error_message`를 API·화면에 노출하지 않음 |

## 2. HTML·폼 경로

이 section은 HTTP 동작과 템플릿 데이터의 기준입니다. 화면 구조와 브라우저 상호작용은
[프런트엔드 UI 계약](../ui/UI.md)을 따릅니다.

| Method | 경로 | 성공 | 실패·비로그인 | 설명 |
| --- | --- | --- | --- | --- |
| `GET` | `/` | 유효한 로그인 `303 /chat` · 비로그인·만료된 세션 `303 /login` | 해당 없음 | 메인화면 |
| `GET` | `/signup` | 비로그인 `200 signup.html` · 유효한 로그인 `303 /chat` | 해당 없음 | 회원가입화면 |
| `POST` | `/signup` | 자동 로그인 없이 `303 /login` | 동일 화면 `400` | 회원가입 처리 |
| `GET` | `/login` | 비로그인 `200 login.html` · 유효한 로그인 `303 /chat` | 해당 없음 | 로그인화면 |
| `POST` | `/login` | 세션 생성 후 `303 /chat` | 동일 화면 `400` | 로그인 처리 |
| `POST` | `/logout` | 세션 삭제 후 `303 /login` | 비로그인도 `303 /login` | 로그아웃 처리 |
| `GET` | `/chat` | 본인 이전 대화와 입력창을 포함한 `200 chat.html` | 비로그인·만료된 세션 `303 /login` | 채팅·사용자 대화 로그 화면 |
| `GET` | `/admin/logs` | 관리자 `200 admin_logs.html` | 비로그인 `303 /login`, 비관리자 `403` | `src/chatbot/admin/router.py`가 소유하는 관리자 전용 채팅 운영 메타데이터 조회 화면 |
| `GET` | `/static/{path}` | 존재하는 CSS·JavaScript asset `200` | 없는 asset `404` | 인증이 필요 없는 UI static asset |

- 폼 성공 후 이동은 모두 `303 See Other`를 사용합니다.
- 인증 폼·보호 HTML 응답과 세션을 변경하는 redirect는 `Cache-Control: no-store`를 사용합니다.
  BFCache 복원 시 UI는 page를 reload하여 서버가 현재 세션을 다시 확인하게 합니다.
- `username`: 앞뒤 공백 제거 후 Python 문자열 길이 3~30자, `password`: 공백을 제거하지 않은 입력값의
  Python 문자열 길이 8~72자입니다.
- 중복 사용자명·길이 오류는 사용자용 메시지와 함께 동일 화면을 `400`으로 다시 렌더링합니다.
- 로그인 실패는 `아이디 또는 비밀번호가 올바르지 않습니다.`만 사용해 사용자명 존재 여부를
  구분하지 않습니다.
- HTML 경로에서 예상하지 못한 인증·DB·템플릿 오류가 발생하면 내부정보가 없는
  `500 text/html` 응답에 `서버 오류가 발생했습니다.`를 표시합니다. JSON 오류 본문을 HTML 경로에
  사용하지 않습니다.
- `GET /chat`이 사용자 대화 로그 조회 역할을 겸하며 사용자용 별도 `/logs`는 만들지 않습니다.

### 폼 요청과 템플릿 문맥

- `POST /signup`, `POST /login`, `POST /logout`은 브라우저 기본
  `application/x-www-form-urlencoded` 폼입니다. File upload와 `multipart/form-data`는 사용하지
  않습니다.
- 회원가입·로그인 폼 필드 이름은 정확히 `username`, `password`입니다. 로그아웃 폼에는 필수 본문
  필드가 없습니다.
- 회원가입·로그인에서 필드가 누락되거나 빈 값이면 동일한 입력 오류 정책으로 처리하며 framework의
  기본 `422` JSON 본문을 브라우저에 노출하지 않습니다.
- Password는 trim하거나 템플릿 문맥, HTML value, 로그, URL에 전달하지 않습니다.
- `signup.html`과 `login.html`의 문맥은 `error: str | None`, `username: str`을 포함합니다. 비로그인
  최초 `GET`은 각각 `error=None`, `username=""`이며 실패한 `POST`는 normalized 사용자명과 안전한
  오류 메시지만 다시 전달합니다. 유효한 로그인 세션의 `GET`은 템플릿을 렌더링하지 않습니다.
- `RegistrationError.reason`은 다음처럼 `signup.html`의 `error`로 변환합니다.

| `RegistrationReason` | `error` |
| --- | --- |
| `username_length` | `아이디는 3자 이상 30자 이하로 입력해주세요.` |
| `password_length` | `비밀번호는 8자 이상 72자 이하로 입력해주세요.` |
| `duplicate_username` | `이미 사용 중인 아이디입니다.` |

- 로그인은 사용자명 누락·비밀번호 누락·인증 실패를 구분하지 않고 모두
  `아이디 또는 비밀번호가 올바르지 않습니다.`로 변환합니다.
- 템플릿 문맥 키는 이 문서에서 정의한 값만 외부 계약입니다. Starlette/FastAPI가 렌더링에
  사용하는 `request` 객체는 business 템플릿 데이터로 간주하지 않습니다.

### 대화 화면 계약

`GET /chat`은 로그인 사용자의 기록만 최신순으로 조회해 입력창과 함께 `chat.html`을 렌더링합니다.

- 템플릿 문맥: `{"chat_exchanges": chat_exchanges, "is_admin": is_admin}`
- `chat_exchanges` 항목: `chat_exchange_id`, `question`, `answer`, `status`, `created_at`
- `is_admin`: `bool`
- `answer=null`이고 `status=failed`이면 `답변을 생성하지 못했습니다.` 표시
- 내부 `error_message`와 운영 메타데이터는 템플릿에 전달하지 않음
- `chat_exchanges`는 안전한 사용자용 조회 필드가며 `is_admin`은 인증이 검증한 값입니다.
- 세션 값이 없거나 유효하지 않거나 대응 사용자가 없는 만료된 세션이면 이력을 조회하거나
  템플릿을 렌더링하지 않고 세션을 제거한 뒤 `303 /login`을 반환합니다.

### 관리자 채팅 운영 메타데이터 화면 계약

`GET /admin/logs`는 관리자만 접근하는 읽기 전용 화면이며 서버 실행 환경 로그 파일을 보여주지
않습니다. `chat_exchanges`에 저장된 사용자별 운영 메타데이터를 조회합니다.

- 템플릿에 전달하는 필드는 [DB 스키마 계약](../db/DB.md#관리자-운영-메타데이터-조회)의 안전한
  관리자 조회 필드를 따릅니다.
- 템플릿 문맥의 business 데이터는 정확히 `{"items": items}`입니다.
- 질문·답변 원문, 내부 `error_message`, `password_hash`와 그 밖의 민감정보는 조회 필드와 화면에서
  제외합니다.
- 별도 관리자 JSON API, 관리자 수정·삭제 CRUD, 고급 검색·페이지 단위 조회, 별도 운영 로그 테이블은
  제공하지 않습니다.
- 별도 역할·권한 테이블은 추가하지 않으며 사용자 역할은 `users.role`을 사용합니다.

## 3. JSON 경로

| Method | 경로 | 인증 | 역할 |
| --- | --- | --- | --- |
| `POST` | `/api/chat` | 필수 | Pydantic 질문 검증과 AI 답변 생성 |
| `GET` | `/api/chat-exchanges` | 필수 | 로그인 사용자의 전체 질문·답변을 JSON으로 반환 |
| `GET` | `/api/chat-exchanges/{chat_exchange_id}` | 필수 | 로그인 사용자의 특정 질문·답변 한 건을 JSON으로 반환 |
| `GET` | `/health` | 불필요 | 프로세스 상태만 확인 |

- 보호된 JSON 경로의 비로그인 응답은
  `401 {"code":"not_authenticated","detail":"로그인이 필요합니다."}`입니다.
- 사용자 API는 내부 `error_message`와 운영 메타데이터를 반환하지 않습니다.

## 4. 대화 API 요청과 응답

OpenAI 메시지 구성과 호출 정책은 [AI 호출 계약](../ai/AI.md)을 따릅니다.

### 요청

```http
POST /api/chat
Content-Type: application/json
```

```json
{"message":"FastAPI의 장점을 설명해주세요."}
```

- `message`는 문자열 필수이며, 앞뒤 공백 제거 결과가 1~1000자여야 합니다.
- 필드 누락·잘못된 자료형·잘못된 JSON은 `422 validation_error`입니다.
- 공백 입력과 1000자 초과 문자열은 `400 validation_error`입니다.

### 성공 응답

```json
{
  "chat_exchange_id": 15,
  "answer": "FastAPI는 Python 기반의 웹 프레임워크입니다.",
  "created_at": "2026-08-04T06:00:00Z"
}
```

- `chat_exchange_id`는 `chat_exchanges.id`를 의미합니다.
- 답변 저장이 성공한 뒤에만 `200 OK`를 반환합니다.

## 5. 대화 기록 조회 API

`GET /api/chat-exchanges`는 로그인 사용자의 전체 이력을 JSON array로 반환합니다.

```json
[
  {
    "chat_exchange_id": 15,
    "question": "FastAPI의 장점을 설명해주세요.",
    "answer": "FastAPI는 Python 기반의 웹 프레임워크입니다.",
    "status": "success",
    "created_at": "2026-08-04T06:00:00Z"
  }
]
```

`GET /api/chat-exchanges/{chat_exchange_id}`는 로그인 사용자가 소유한 한 건을 같은 필드로
반환합니다. 존재하지 않거나 다른 사용자의 기록면 모두 `404 conversation_not_found`를
반환합니다. 두 API 모두 내부 `error_message`와 운영 메타데이터를 반환하지 않습니다.

- `status=failed`인 항목은 `answer: null`을 반환합니다.

## 6. 오류 응답

JSON API 오류는 `{"code":"...","detail":"..."}` 형식으로 통일합니다. `code`는 안정적인
lower_snake_case 식별자이고, `detail`은 언어에 따라 변환되는 사용자용 안전 메시지입니다.

| 상태 | 상황 | 코드 | 기본 `ko` detail |
| --- | --- | --- | --- |
| `400` | 빈 문자열·공백 | `validation_error` | `질문을 입력해주세요.` |
| `400` | 공백 제거 후 1000자 초과 | `validation_error` | `질문은 1000자 이하로 입력해주세요.` |
| `401` | 비로그인 JSON 요청 | `not_authenticated` | `로그인이 필요합니다.` |
| `403` | 권한 부족 JSON 요청 | `forbidden` | `접근 권한이 없습니다.` |
| `404` | 대화 기록 없음 또는 다른 사용자 소유 | `conversation_not_found` | `대화 기록을 찾을 수 없습니다.` |
| `422` | 필드 누락·자료형·JSON 형식 오류 | `validation_error` | `요청 형식이 올바르지 않습니다.` |
| `500` | DB 저장·조회 실패를 포함한 내부 오류 | `internal_error` | `서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.` |
| `502` | OpenAI API 오류 | `openai_api_error` | `AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요.` |
| `504` | OpenAI 요청 시간 제한 | `openai_timeout` | `AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.` |

### i18n 오류 메시지

- 초기 지원 언어는 `ko`, `en`입니다.
- 언어 우선순위는 HTTP `Accept-Language` 헤더, 기본 언어 `ko` 순서입니다.
- 미지원 언어, 해석 불가 헤더, 누락된 번역 키는 모두 `ko`로 대체 동작합니다.
- 같은 `code`는 언어와 무관하게 의미와 HTTP 상태 코드가 동일합니다. 프런트엔드는 `detail`이
  아니라 `code`를 기준으로 분기합니다.
- 번역 메시지에는 내부 예외, 키, 쿠키, SQL, 기술 구성 정보를 포함하지 않습니다.
- 예를 들어 `openai_api_error`의 `en` detail은
  `Failed to generate an AI response. Please try again later.`입니다.

## 7. 대화 처리 결과의 HTTP 변환

저장 기록의 상태와 불변식은 [DB 스키마 계약](../db/DB.md), OpenAI 모델과 시간 제한 설정값은
[실행·배포 계약](../DEPLOYMENT.md)을 따릅니다. 처리 결과의 HTTP 상태와 오류 형식은 위 오류
응답 표를 따릅니다.

## 8. 상태 API

```json
{"status":"ok"}
```

- `GET /health`, 인증 불필요, 정상 `200`
- OpenAI를 호출하지 않고 초기 버전에서는 DB 연결도 검사하지 않음

## 9. API 스키마와 호환성 정책

`/api/...` JSON API의 요청과 응답은 Pydantic 스키마로 정의합니다. 라우터는 요청 모델과
`response_model`을 사용해 외부 API 스키마를 명시적으로 제한합니다.

현재 JSON API는 `/api/...` 경로를 사용하며 별도의 URL 버전 prefix를 두지 않습니다. 현재 단계에서는
브라우저 프런트엔드와 백엔드가 하나의 애플리케이션으로 함께 배포되므로, 호환 가능한 변경은 기존 API
경로에서 적용합니다.

### 호환 가능한 변경

다음 변경은 기존 클라이언트 동작을 깨지 않는 경우 같은 API 계약에서 적용할 수 있습니다.

- 응답에 optional 필드 추가
- 기존 의미와 타입을 유지한 설명·검증 보완
- 기존 error 코드의 의미를 변경하지 않는 내부 구현 변경

### 호환성을 깨는 변경

다음 변경은 breaking change로 취급합니다.

- 기존 요청 필드 삭제 또는 이름 변경
- 기존 optional 요청 필드를 required로 변경
- 요청/응답 필드 타입 변경
- 기존 응답 필드 삭제 또는 이름 변경
- 기존 필드의 null 허용 여부를 더 엄격하게 변경
- 기존 HTTP 상태 또는 안정적인 error `code`의 의미 변경
- 동일한 입력에 대한 API 의미를 호환되지 않게 변경

호환성을 깨는 변경를 기존 엔드포인트에 조용히 적용하지 않습니다.

### 버전 관리

현재 애플리케이션은 외부 독립 클라이언트를 제공하지 않으므로 `/api/v1` 같은 URL 버전을 선제적으로
도입하지 않습니다.

향후 mobile 애플리케이션, 외부 API consumer 또는 프런트엔드/백엔드 독립 배포처럼 이전 계약을
유지해야 하는 클라이언트가 생긴 상태에서 breaking change가 필요하면 versioned API를 도입합니다.

```text
/api/v1/chat
/api/v2/chat
```

새 버전을 도입하는 동안 기존 버전은 명시된 deprecation 기간 동안 유지하고, 제거 시점과
마이그레이션 방법을 API 문서에 기록합니다.

### 변경 절차

API 스키마를 변경하는 PR은 다음을 함께 갱신합니다.

- Pydantic 요청/응답 스키마
- 라우터의 `response_model`과 응답 선언
- 관련 API 테스트
- 이 API 계약의 요청/응답 예시
- breaking 여부와 필요한 버전 변경
