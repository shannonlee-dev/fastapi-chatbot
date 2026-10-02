# DB 스키마 계약

이 문서는 현재 저장소가 따르는 영속 저장 스키마와 DB 동작 계약을 정의합니다. 구현 변경으로
계약이 달라지는 경우 코드와 이 문서를 같은 변경에서 함께 갱신합니다. 이 문서는 구현 완료 상태를
의미하지 않습니다.

## 1. 모델 원칙

- `users 1 : N chat_exchanges`
- `chat_exchanges` 한 기록은 사용자 질문과 AI 답변 한 쌍이며 해당 채팅 요청의 운영
  메타데이터를 함께 저장합니다.
- 운영 메타데이터를 위한 별도 로그 테이블은 만들지 않습니다.
- 사용자별 하나의 연속 대화만 제공하므로 대화방과 메시지 테이블을 분리하지 않습니다.
- 초기 테이블 생성은 `Base.metadata.create_all()`을 사용하고 Alembic은 도입하지 않습니다.

## 2. 테이블 스키마

### `users`

| Field | Type | 조건 |
| --- | --- | --- |
| `id` | Integer | PK |
| `username` | String | Unique, Not Null |
| `password_hash` | String | Not Null |
| `role` | String | Not Null. 사용자 역할 저장 |
| `created_at` | DateTime | Not Null, UTC |

`role`은 일반 사용자와 관리자를 구분합니다. 초기 관리자 생성 규칙은
[아키텍처](../ARCHITECTURE.md)의 인증 계약을 따릅니다.

### `chat_exchanges`

| Field | Type | 조건 |
| --- | --- | --- |
| `id` | Integer | PK. API의 `chat_exchange_id` |
| `user_id` | Integer | FK → `users.id`, Not Null |
| `question` | Text | Not Null |
| `answer` | Text | 성공 시 답변, 실패 시 Null 가능 |
| `status` | String | Not Null, `success` 또는 `failed` |
| `error_message` | Text | Nullable, 안전한 내부 요약만 저장 |
| `created_at` | DateTime | Not Null, UTC |
| `request_id` | String(64) | Unique, Not Null |
| `user_agent` | String(512) | Nullable |
| `response_time_ms` | Integer | Not Null, 0 이상. 처리 시간(ms) |
| `error_code` | String(50) | Nullable |

## 3. 상태와 운영 메타데이터 불변식

| 상태 | 답변 | error_message | error_code |
| --- | --- | --- | --- |
| `success` | Not Null | Null | Null |
| `failed` | Null | Not Null | 실패 원인 코드 |

DB 스키마는 `CheckConstraint`로 상태 값과 답변·error 메시지 조합을 함께 강제합니다.

- `request_id`: 최대 64자, `UNIQUE`, `NOT NULL`. 서버 로그와 DB 기록을 연결하는 요청별 ID입니다.
- `response_time_ms`: `NOT NULL`, 0 이상의 정수인 요청 처리 시간입니다.
- `error_code`: 최대 50자이며 성공 시 Null입니다.
- `user_agent`: 최대 512자이며 헤더가 없으면 Null을 허용합니다.
- raw 헤더, 쿠키, Authorization, 세션 ID, OpenAI API 키, 비밀번호와 `password_hash`는
  운영 메타데이터에 저장하지 않습니다.
- `request_method`, `request_path`는 채팅 요청에서 고정이므로 `chat_exchanges`에 저장하지 않습니다.

## 4. 조회 정책

### 사용자 대화 기록 조회

사용자 화면과 API 조회 필드는 `error_message`와 운영 메타데이터를 제외합니다.

### 관리자 운영 메타데이터 조회

관리자 조회 필드는 정확히 `user_id`, `username`, `chat_exchange_id`, `created_at`, `request_id`,
`user_agent`, `response_time_ms`, `status`, `error_code`만 반환합니다. `question`, `answer`,
`error_message`, `password_hash`와 그 밖의 민감정보는 포함하지 않습니다.

이 조회를 위해 별도 관리자 JSON API, 수정·삭제 CRUD, 고급 검색·페이지 단위 조회, 별도 운영 로그 테이블은
추가하지 않습니다.

## 5. 저장 정책

### 성공

- `status=success`, `answer`와 UTC `created_at` 저장
- `request_id`, 선택적 `user_agent`, `response_time_ms` 저장
- `error_message=null`, `error_code=null`

### 실패

- `status=failed`, `answer=null`, 안전한 내부 `error_message`, UTC `created_at` 저장
- `request_id`, 선택적 `user_agent`, `response_time_ms` 저장
- `error_code`로 실패 원인을 분류합니다. HTTP 상태와 사용자 오류 응답은
  [API 계약](../api/API.md)을 따릅니다.

## 6. SQLite 연결 동작

- 환경별 SQLite 연결 URL, 배포 볼륨과 재시작 영속 저장 구성은
  [실행·배포 계약](../DEPLOYMENT.md)을 따릅니다.

## 7. 스키마 변경과 마이그레이션

현재 초기 버전은 SQLAlchemy 모델과 `Base.metadata.create_all()`을 사용해 테이블을 생성합니다.

`create_all()`은 기존 테이블의 열 변경, 삭제, 이름 변경 등 스키마 마이그레이션을 수행하지 않으므로
기존 DB 스키마가 변경되는 경우 애플리케이션 시작만으로 마이그레이션이 완료된 것으로 간주하지 않습니다.

### 스키마 변경 절차

1. 변경 전 SQLite DB를 backup합니다.
2. 기존 스키마와 대상 스키마의 차이를 확인합니다.
3. 데이터 보존이 필요한 변경은 명시적인 마이그레이션 스크립트를 작성합니다.
4. 테스트 DB에서 마이그레이션을 먼저 실행합니다.
5. 기존 기록과 constraint가 유지되는지 검증합니다.
6. 애플리케이션 코드와 스키마 계약을 함께 배포합니다.
7. 마이그레이션 후 `scripts/check_logs.sql` 등 검증 절차로 데이터를 확인합니다.

### 초기 버전 정책

개발 단계에서 기존 데이터를 보존할 필요가 없는 경우에는 DB 파일을 제거하고 `create_all()`로
스키마를 다시 생성할 수 있습니다.

기존 데이터를 보존해야 하는 환경에서는 DB 파일 삭제를 마이그레이션 방법으로 사용하지 않습니다.

### Migration 도구 도입 기준

열 이름 변경/delete, constraint 변경, 복수 환경의 스키마 버전 관리 등 반복 가능한 마이그레이션이
필요해지면 Alembic 도입을 검토합니다.

## 8. DB 검증 방법

> 🔎 아래 명령은 구현 후 실제 DB 파일이 생성된 뒤 실행합니다. `scripts/check_logs.sql`은
> 운영 확인에 필요한 안전한 필드만 출력합니다.

### sqlite3 CLI

```bash
sqlite3 data/chatbot.db < scripts/check_logs.sql
```

스크립트는 사용자 역할, 최근 ChatExchange, 실패 ChatExchange의 `answer_is_null` 불변식,
사용자별 ChatExchange 수, 운영 메타데이터, 관리자 조회 필드를 순서대로 조회합니다.
관리자 조회 필드는 다음 필드만 출력합니다.

```text
user_id
username
chat_exchange_id
created_at
request_id
user_agent
response_time_ms
status
error_code
```

`password_hash`, 질문·답변 원문, 내부 오류 내용, 쿠키, Authorization, 비밀값은 스크립트
출력에 포함하지 않습니다.

확인 항목:

- `users.role`에 일반 사용자와 초기 `admin` 관리자의 역할이 구분되어 저장됨
- `chat_exchanges.user_id`가 로그인 사용자 `users.id`와 연결됨
- 성공 기록에 UTC 시각·`request_id`·`response_time_ms`가 존재함
- 실패 기록은 `answer IS NULL`, `status='failed'`이며 `error_code`로 실패 원인을 분류함
- `request_method`, `request_path`는 DB 운영 메타데이터에 저장하지 않음
- 사용자별 조회 결과가 서로 섞이지 않음
