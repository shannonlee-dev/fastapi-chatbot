# 프런트엔드 UI 계약

이 문서는 화면 구조, 폼 레이아웃, 브라우저 상태, 상호작용, 접근성과 반응형 동작을 정의합니다.
HTTP 상태·요청·응답·오류 `code`는 [API 계약](../api/API.md), 모듈 의존 방향은
[아키텍처](../ARCHITECTURE.md)를 따릅니다. 이 문서는 UI 계약을 정의하며 현재 구현 구성은
[구현 상태와 책임](#8-구현-상태와-책임)에 기록합니다.

## 1. 범위와 기술 경계

- `src/chatbot/ui`가 Jinja2로 HTML을 서버 렌더링하고 브라우저 JavaScript가 `POST /api/chat`을
  호출합니다.
- 프런트엔드는 별도 build 과정 없이 HTML, CSS, vanilla JavaScript로 구성합니다.
- 초기 버전에는 React 등 UI framework, 상태관리 library, toast package, streaming, 자동 retry,
  별도 animation library를 도입하지 않습니다.
- 구체적인 색상, spacing, typography 값은 구현 세부사항입니다. 다만 모든 화면에서 같은 시각
  규칙을 사용하고 상태·focus를 명확히 구분해야 합니다.

## 2. 화면과 서버 경로 연결

이 section은 각 화면이 서버 경로를 어떻게 사용하는지 설명합니다. 정확한 HTTP method, 상태,
redirect, 요청과 응답 스키마는 [API 계약](../api/API.md)을 따릅니다.

### `/`

- 별도 page를 렌더링하지 않으며, 서버가 실제 사용자가 확인된 세션이면 대화 화면으로, 그 외에는
  로그인 화면으로 `303` 이동시킵니다. 대응 사용자가 없는 만료된 세션은 제거합니다.

### `/signup`

- `signup.html`에 사용자명·비밀번호 폼과 로그인 화면 링크를 렌더링합니다.
- 유효한 로그인 세션으로 접근하면 폼을 렌더링하지 않고 `/chat`으로 `303` 이동합니다.
- 폼은 같은 경로로 제출합니다. 성공 시 브라우저는 로그인 화면으로 이동하고, 입력 오류 시 같은
  화면에 안전한 메시지를 표시합니다.
- 템플릿 문맥과 `RegistrationReason`별 메시지는
  [API 계약의 폼 계약](../api/API.md#폼-요청과-템플릿-문맥)를 그대로 사용합니다.

### `/login`

- `login.html`에 사용자명·비밀번호 폼과 회원가입 화면 링크를 렌더링합니다.
- 유효한 로그인 세션으로 접근하면 폼을 렌더링하지 않고 `/chat`으로 `303` 이동합니다.
- 폼은 같은 경로로 제출합니다. 성공 시 브라우저는 대화 화면으로 이동하고, 인증 실패 시 같은
  화면에 안전한 메시지를 표시합니다.
- 템플릿 문맥은 [API 계약의 폼 계약](../api/API.md#폼-요청과-템플릿-문맥)를
  그대로 사용합니다.

### `/chat`

- `chat.html`에 질문 폼과 로그인 사용자의 이전 대화를 함께 렌더링합니다.
- `chat_exchanges` 템플릿 변수에는 `chat_exchange_id`, `question`, `answer`, `status`,
  `created_at` 필드가 포함됩니다.
- `is_admin: bool` 템플릿 변수로 관리자 탐색 렌더링 여부를 결정합니다.
- 브라우저 JavaScript는 `POST /api/chat`을 호출해 pending 대화 항목을 실제 답변 또는 오류로
  교체합니다. 사용하는 JSON 필드와 오류 계약은 [API 계약](../api/API.md)을 따릅니다.

### `/admin/logs`

- 별도 JSON API를 사용하지 않고 `admin_logs.html`에 허용된 읽기 전용 운영 메타데이터를 테이블로
  렌더링합니다.
- `src/chatbot/admin/router.py`가 전달하는 템플릿 변수 이름은 `items`입니다. UI는 이 문맥 이름이나
  필드를 임의로 바꾸지 않습니다.
- 표시 가능한 조회 필드는 [DB 스키마 계약](../db/DB.md#관리자-운영-메타데이터-조회)을
  따릅니다.
- `src/chatbot/ui`는 `/admin/logs`의 접근 제어와 관리자 데이터 조합을 담당하지 않습니다.

### `/logout`

- 로그아웃 button은 `/logout` 폼을 제출하고 서버 응답에 따라 로그인 화면으로 이동합니다.
- JavaScript 로그아웃이나 `GET /logout`은 제공하지 않습니다.

브라우저의 화면 표시만으로 접근을 허용하지 않으며, 인증과 관리자 권한은 서버가 최종 판별합니다.

## 3. 공통 UI 기준

### 레이아웃과 내용

- 각 화면은 하나의 명확한 page heading과 주요 내용을 포함합니다.
- 고정 UI 문구는 한국어로 작성합니다. JSON API의 사용자용 `detail`은 서버가 반환한 언어를
  변환하지 않고 그대로 표시합니다.
- DB·API의 UTC 시각은 화면에서 `YYYY-MM-DD HH:mm:ss KST`로 변환해 표시하고, 원본 UTC 값은
  `time` element의 `datetime` attribute에 유지합니다.
- 인증 폼과 보호 HTML 응답은 `Cache-Control: no-store`를 사용합니다. 모든 UI 화면은
  BFCache에서 복원되면 내용을 숨긴 뒤 reload하여 서버가 현재 세션을 다시 확인하게 합니다.

### 안전한 텍스트 렌더링

- 질문, 답변, 사용자명, 사용자-Agent, API `detail`은 신뢰할 수 없는 텍스트로 취급합니다. Jinja2
  autoescape를 유지하고 JavaScript에서는 HTML로 삽입하지 않고 텍스트로 렌더링합니다.
- 질문, 답변, API `detail`은 Markdown이나 HTML로 parsing하지 않는 plain 텍스트입니다. 원문의
  줄바꿈은 보존하고 공백 없는 긴 문자열도 화면 영역을 넘지 않도록 wrapping합니다.

### 반응형·접근성

- 최소 360px 너비의 mobile 화면 영역부터 desktop까지 주요 내용과 폼을 사용할 수 있어야
  합니다.
- 화면 너비가 줄어들어도 폼 요소와 button이 화면 영역 밖으로 잘리지 않아야 합니다.
- Heading hierarchy, landmark, 레이블, button, 테이블 헤더를 의미에 맞는 semantic HTML로
  작성합니다.
- 모든 폼 요소에는 화면에 보이는 레이블을 연결합니다. Placeholder만 레이블로 사용하지
  않습니다.
- Keyboard focus 순서는 화면의 읽기 순서와 일치해야 하며 focus indicator를 제거하지 않습니다.
- 상태를 색상만으로 구분하지 않고 텍스트 또는 icon의 accessible 이름을 함께 제공합니다.
- 비활성화한 button에는 실제 `disabled` attribute를 사용합니다.

## 4. 회원가입 화면

### 기본 상태

- 사용자명과 비밀번호 입력, 회원가입 button, 로그인 화면으로 이동하는 링크를 제공합니다.
- 브라우저 폼 요소는 [API 계약](../api/API.md#2-html폼-경로)의 사용자명·비밀번호 검증 조건을
  반영합니다. 최종 검증은 서버가 수행합니다.
- 폼은 `method="post"`, `action="/signup"`이고 input 이름은 `username`, `password`입니다.
- 사용자명에는 `required`, `minlength="3"`, `maxlength="30"`, `autocomplete="username"`을,
  비밀번호에는 `required`, `minlength="8"`, `maxlength="72"`, `autocomplete="new-password"`를
  적용합니다.

### 오류 표시

- 중복 사용자명 또는 길이 오류는 같은 화면의 폼과 연결된 오류 영역에 표시합니다.
- 오류가 발생하면 사용자가 입력한 사용자명은 유지할 수 있지만 비밀번호는 HTML이나 템플릿
  문맥으로 다시 전달하거나 채우지 않습니다.
- 오류 영역은 메시지가 있을 때 `role="alert"`를 사용하고 관련 요소와 `aria-describedby`로
  연결합니다.

## 5. 로그인 화면

### 기본 상태

- 사용자명과 비밀번호 입력, 로그인 button, 회원가입 화면으로 이동하는 링크를 제공합니다.
- 폼은 `method="post"`, `action="/login"`이고 input 이름은 `username`, `password`입니다.
- 사용자명에는 `required`, `maxlength="30"`, `autocomplete="username"`을, 비밀번호에는
  `required`, `maxlength="72"`, `autocomplete="current-password"`를 적용합니다. 로그인 실패의
  최종 판별과 메시지 통일은 서버가 담당합니다.

### 오류 표시

- 인증 실패는 사용자명 존재 여부를 구분하지 않고
  `아이디 또는 비밀번호가 올바르지 않습니다.`만 표시합니다.
- 인증 실패 후 사용자명은 유지할 수 있지만 비밀번호는 다시 채우지 않습니다.
- 오류 영역은 메시지가 있을 때 `role="alert"`를 사용하고 사용자명·비밀번호 요소와
  `aria-describedby`로 연결합니다.

## 6. 대화 화면

### 서버 렌더링 데이터

`GET /chat`은 다음 `chat_exchanges`를 최신순으로 전달합니다.

| Field | 화면 표시 |
| --- | --- |
| `chat_exchange_id` | 기록 식별에 사용하며 반드시 본문에 노출할 필요는 없음 |
| `question` | 사용자 질문 텍스트 |
| `answer` | 성공한 AI 답변 텍스트 |
| `status` | `success` 또는 `failed` 상태 표시 |
| `created_at` | 원본 UTC 시각을 KST로 변환해 표시 |

- 같은 문맥의 `is_admin`은 인증이 검증한 boolean이며, UI가 역할 문자열이나 DB 기록을 직접
  판별하지 않습니다.
- 화면은 전달받은 `chat_exchanges`를 역순으로 렌더링해 과거 대화를 위쪽에, 최신 대화를
  최하단에 표시합니다.
- 대화 헤더와 질문 폼은 화면 영역 안에 유지하고, 대화 기록 영역만 독립적으로 세로 스크롤합니다.
  대화 기록이 있으면 최초 렌더링 후 최신 대화가 보이도록 스크롤합니다.
- 각 대화 항목은 사용자 질문을 오른쪽에, 서버가 반환한 AI 답변 또는 실패 안내를 왼쪽에
  배치해 발화 주체를 구분합니다.
- 기록이 없으면 입력 폼을 그대로 제공하고 `아직 대화 기록이 없습니다.`를 표시합니다.
- `answer=null`이고 `status=failed`이면 답변 대신 `답변을 생성하지 못했습니다.`를 표시합니다.
- 내부 `error_message`와 운영 메타데이터는 템플릿에 전달하거나 DOM에 포함하지 않습니다.
- 사용자용 별도 `/logs` 화면은 만들지 않습니다. 이 화면이 본인의 대화 기록 조회 역할을 함께
  수행합니다.

### 탐색

- 로그아웃 button은 `POST /logout` 폼으로 동작합니다.
- 서버가 현재 사용자를 관리자로 판별한 경우에만 `/admin/logs`로 이동하는
  `관리자 운영 기록` 링크를 button 형태로 제공합니다. 일반 사용자에게는 이 링크를
  렌더링하거나 DOM에 포함하지 않습니다.

### 입력 폼

- 질문 `textarea`, 전송 button, 폼 오류 영역을 제공합니다.
- 질문 요소에는 `required`와 `maxlength="1000"`을 적용합니다.
- 질문 아래에는 `현재 글자 수 / 1000` 형식의 counter를 항상 표시하고 `aria-describedby`로 질문
  요소와 연결합니다. Counter는 매 입력을 live announcement하지 않습니다.
- 질문 `textarea`는 2줄 기준으로 시작합니다. Desktop에서는 기존 `7rem` 최소 높이를 유지하고,
  `30rem` 이하 mobile 화면 영역에서는 `4.75rem` 최소 높이로 줄여 대화 기록 영역을 확보합니다.
- `maxlength="1000"`은 일반적인 입력 과정에서 1000자 초과 작성을 제한합니다. JavaScript의
  길이 검증은 programmatic value 변경처럼 HTML constraint를 우회한 상황을 위한 방어입니다.
- 제출 시 JavaScript가 값을 `trim()`하고, 결과가 1~1000자가 아니면 API를 호출하지 않습니다.
- 공백 입력에는 `질문을 입력해주세요.`, 1000자 초과 입력에는
  `질문은 1000자 이하로 입력해주세요.`를 표시합니다.
- 유효한 질문은 공백을 제거한 전송값을 별도로 보관한 뒤 질문 요소에서 즉시 제거합니다.
  Counter도 즉시 `0 / 1000`으로 되돌립니다. Client 검증에 실패한 값과 count는 유지합니다.
- Primary pointer가 fine인 환경에서는 Enter가 폼을 제출하고 Shift+Enter가 줄바꿈을 유지합니다.
  Primary pointer가 coarse인 환경에서는 Enter가 줄바꿈을 유지하고 전송 button으로 제출합니다.
- IME composition 중인 Enter는 제출하지 않습니다. Keyboard 제출 동작은 유지하지만 별도 입력 방식
  보조 함수 문구는 표시하지 않습니다.

### 브라우저 상태 전이

| 상태 | 동작 |
| --- | --- |
| Idle | 진행 중인 요청이 없고 질문 요소와 전송 button을 사용할 수 있음 |
| Submitting | 전송 button을 비활성화하고 질문을 오른쪽에 즉시 추가하며 왼쪽 AI 답변 위치에 `답변 생성 중…`을 표시하고 추가 submit을 무시함 |

- 한 번에 하나의 `POST /api/chat` 요청만 진행할 수 있습니다.
- 요청은 `fetch("/api/chat")`에 `method: "POST"`, `Content-Type: application/json`,
  `Accept: application/json`, `credentials: "same-origin"`을 사용하고 본문은 정확히
  `{"message": trimmedQuestion}`입니다.
- Submitting 중에도 질문 요소는 활성 상태로 유지해 다음 질문 초안을 작성할 수 있습니다.
- Submitting을 시작할 때 전송한 질문과 AI 로딩 영역으로 구성한 pending 대화 항목을
  최하단에 추가하고 빈 대화 기록 안내를 제거한 뒤 최신 항목으로 스크롤합니다.
- 성공하면 pending 대화 항목의 로딩을 응답 `answer`로 교체하고 `chat_exchange_id`와
  `created_at`을 해당 항목에 연결합니다. 같은 질문을 포함한 새 항목을 중복 생성하지 않으며
  별도 성공 상태도 표시하지 않습니다.
- 성공 응답의 `answer`는 텍스트로 삽입합니다. `created_at` 원본 UTC 값은 `time[datetime]`에 유지하고
  화면 텍스트만 `Asia/Seoul` 기준 KST로 변환합니다. 응답 필드가 누락되거나 타입이 계약과 다르면
  비정상 응답으로 처리합니다.
- 처리 오류는 pending 대화 항목의 로딩을 안전한 오류 메시지로 교체합니다. 실패 대화
  항목에는 임의의 `chat_exchange_id`나 시각을 만들지 않습니다.
- Pending 대화 항목에 표시된 실패 결과 자체는 영구 저장의 증거가 아닙니다. 일부 서버 오류는
  [DB 스키마 계약의 저장 정책](../db/DB.md#5-저장-정책)에 따라 실패 기록으로 저장될 수
  있으며, 새로고침 후에는 `GET /chat`이 렌더링한 실제 서버 이력만 표시합니다.
- 성공·실패와 관계없이 현재 작성 중인 다음 질문 초안을 비우거나 전송한 질문을 복원하지
  않습니다.
- 응답을 교체하기 직전 대화 기록이 bottom에서 `48px` 이내라면 교체 후 최신 항목을 계속
  표시합니다. 사용자가 그보다 위의 기록을 읽고 있으면 현재 스크롤 위치를 강제로 바꾸지 않습니다.
- Redirect를 제외한 공통 종료 경로는 로딩 상태를 정리하고 전송 button을 다시 활성화한 뒤
  질문 요소에 focus를 이동합니다.
- AI 답변 위치의 로딩 영역에는 `aria-live="polite"`, 즉시 확인해야 하는 폼 오류와 실패
  대화 항목에는 `role="alert"`를 적용합니다.
- 성공은 별도 상태 문구 없이 pending 대화 항목의 로딩을 실제 답변으로 교체해 표시합니다.
- 자동 retry는 하지 않습니다.

### 대화 API 오류 처리

프런트엔드는 `detail` 문자열을 비교하지 않고 안정적인 `code`로 동작을 결정합니다.
요청 전 클라이언트 검증 오류는 pending 대화 항목을 만들지 않고 폼 오류로 표시합니다.
요청을 시작한 뒤 받은 `POST /api/chat` 오류는 다음 기준으로 pending 항목을 처리합니다.

| `code`·상황 | 브라우저 동작 |
| --- | --- |
| `validation_error` | pending 대화 항목의 AI 답변을 안전한 `detail`로 교체 |
| `not_authenticated` | `/login`으로 이동 |
| `internal_error`, `openai_api_error`, `openai_timeout` | pending 대화 항목의 AI 답변을 안전한 `detail`로 교체 |
| 네트워크 오류, JSON이 아닌 응답, 문자열이 아닌 `detail`, 알 수 없는 `code` | pending 대화 항목의 AI 답변을 `요청을 처리하지 못했습니다.`로 교체 |

정확한 상태·`code`·`detail`은 [API 계약의 오류 응답](../api/API.md#6-오류-응답)을
따릅니다. 내부 예외, SQL, 기술 구성, 쿠키, 키, 내부 `error_message`는 화면에 표시하지 않습니다.

## 7. 관리자 운영 메타데이터 화면

- `/admin/logs`는 서버 실행 환경 로그 파일이 아니라 `chat_exchanges`에 저장된 사용자별 운영
  메타데이터를 읽기 전용 테이블로 표시합니다.
- `src/chatbot/admin/router.py`가 경로와 `require_admin` 기반 접근 제어를 소유하고, `src/chatbot/ui`는
  `admin_logs.html`과 공통 static 표현 자원만 제공합니다.
- 로그아웃 button은 `POST /logout` 폼으로 동작하며, `/chat`으로 돌아가는 링크를 함께
  제공합니다.
- [DB 스키마 계약](../db/DB.md#관리자-운영-메타데이터-조회)에 정의된 안전한 조회 필드를
  각각 테이블 열로 표시합니다.
- Nullable 값은 빈 cell 대신 `-`처럼 값이 없음을 알 수 있는 텍스트로 표시합니다.
- Record가 없으면 테이블 대신 `표시할 운영 기록이 없습니다.`를 표시합니다.
- `status`와 `error_code`는 색상만으로 구분하지 않고 텍스트를 그대로 제공합니다.
- 질문·답변 원문, 내부 `error_message`, 비밀번호와 `password_hash`는 표시하거나 DOM에 포함하지
  않습니다.
- 별도 관리자 JSON API, 수정·삭제 CRUD, 고급 검색·페이지 단위 조회, 별도 운영 로그 테이블은 제공하지
  않습니다.
- 테이블에는 내용을 설명하는 caption과 열별 헤더를 제공합니다.
- 좁은 화면에서는 테이블 열을 숨겨 의미를 잃게 하지 않고 테이블 container에 가로 스크롤을
  제공합니다.
- 테이블 위에 `표를 좌우로 스크롤하면 모든 열을 확인할 수 있습니다.`를 표시하고 스크롤 region의
  accessible description으로 연결합니다. Scrollbar의 track과 thumb도 구분해 가로 스크롤 가능성을
  드러냅니다.
- 테이블은 `72rem`의 적정 최소 너비를 유지하며 헤더와 짧은 identifier·상태 값은 줄바꿈하지
  않습니다. `request_id`는 최소 `16rem`에서 자연스러운 구분점으로만 줄바꿈하고,
  `user_agent`는 `20rem` 너비 안에서 긴 technical 토큰을 wrapping합니다.

현재 `admin_logs.html`은 관리자 경로와 safe 조회 필드를 유지하면서 탐색, 빈 상태, nullable `-`
표시, caption, 반응형 테이블과 공통 스타일을 제공합니다. Route·문맥 ownership은 변경하지 않습니다.

## 8. 구현 상태와 책임

현재 UI/FE 구현은 다음 구성을 따릅니다.

1. `src/chatbot/ui/router.py`가 `/`, 인증 폼 경로, `/logout`, `/chat`을 소유합니다.
2. `signup.html`, `login.html`, `chat.html`, `admin_logs.html`과 공통 템플릿이 화면을 렌더링하고,
   `styles.css`, `chat.js`, `page-lifecycle.js`가 공통 스타일과 브라우저 상호작용을 담당합니다.
3. `src/chatbot/main.py`가 UI 라우터를 한 번 등록하고 `src/chatbot/ui/static`을 `/static`에 연결합니다. 관리자·대화
   경로는 각 소유 라우터에서만 등록합니다.
4. `tests/ui/test_router.py`와 `tests/ui/test_templates.py`가 HTML 경로, 민감정보 미노출, 템플릿과
   static asset 연결을 검증합니다. 실제 브라우저 상호작용은 아래 수동 확인 사항로 반복 확인합니다.

UI는 인증 모듈의 `require_authenticated_user()`와 `AuthenticatedUser(user_id, is_admin)`을
사용합니다. 대화 이력·JSON API와 관리자 경로의 공개 인터페이스를 유지하며 스키마나 경로
ownership을 변경하지 않습니다.

## 9. 수동 검증 확인 사항

아래 항목은 구현 미완료 목록이 아니라 배포와 UI regression 확인 시 반복 수행하는 수동
확인 사항입니다. 실행 결과는 이 계약 문서의 checkbox 상태로 지속 관리하지 않습니다.

### 인증 화면

- [ ] `/`가 인증 상태에 맞는 화면으로 이동함
- [ ] 회원가입 성공은 `/login`, 일반 사용자·관리자 로그인 성공은 `/chat`으로 이동함
- [ ] 로그인 사용자의 `/login`·`/signup` 접근은 `/chat`으로 이동하고 만료된 세션은 폼을 표시함
- [ ] 회원가입·로그인 오류가 같은 화면에 안전하게 표시되고 비밀번호가 다시 채워지지 않음
- [ ] 비로그인 사용자의 보호 화면 접근과 일반 사용자의 `/admin/logs` 접근이 계약대로 차단됨

### 대화 화면

- [ ] 본인의 이전 대화만 과거부터 최신 순서로 표시되고 빈 기록·실패 기록 안내가 동작함
- [ ] 대화 기록이 길어도 헤더와 질문 폼은 보이며 기록 영역만 스크롤되고 최초 진입 시 최신 대화가 표시됨
- [ ] 빈 문자열·공백·1자·1000자·1000자 초과 입력을 검증함
- [ ] Mobile textarea가 2줄 높이로 시작하고 Counter가 입력과 전송 후 초기화 상태를 반영하며 Desktop Enter·Shift+Enter·IME와 Mobile Enter가 계약대로 동작함
- [ ] 전송 직후 pending 대화 항목과 `답변 생성 중…`이 표시되고 중복 전송이 차단됨
- [ ] 성공·실패 후 같은 pending 항목이 교체되고 작성 중인 다음 초안이 유지됨
- [ ] 실패 항목에 임의 ID·시각이 없으며 새로고침 후 실제 서버 이력만 표시됨
- [ ] 네트워크·비정상 응답에서 기본 오류 문구와 상태 복구가 동작함
- [ ] `not_authenticated` 응답에서 로그인 화면으로 이동함
- [ ] 대화 시각은 KST로 보이지만 `time[datetime]`은 UTC 원본을 유지함
- [ ] 질문·답변·오류의 줄바꿈과 긴 문자열이 표시되고 HTML·Markdown으로 실행되지 않음

### 관리자·공통 UI

- [ ] 관리자 테이블에 허용된 운영 메타데이터만 표시됨
- [ ] 360px에서 헤더와 짧은 identifier가 글자 중간에서 끊기지 않고 안내와 scrollbar를 통해 테이블 container의 가로 스크롤을 알 수 있음
- [ ] 질문·답변·내부 오류·민감정보가 관리자 DOM에 포함되지 않음
- [ ] `/chat`에서 관리자에게만 `관리자 운영 기록` button이 표시됨
- [ ] 보호 화면에서 로그아웃할 수 있고 관리자 화면에서 `/chat`으로 이동할 수 있음
- [ ] 로그인·로그아웃 후 뒤로가기로 BFCache 화면이 복원되면 서버가 세션을 다시 확인함
- [ ] 360px mobile 화면에서 폼을 사용할 수 있고 테이블을 가로 스크롤할 수 있음
- [ ] Keyboard만으로 주요 action을 실행하고 로딩·오류 상태를 보조 기술로 확인할 수 있음
