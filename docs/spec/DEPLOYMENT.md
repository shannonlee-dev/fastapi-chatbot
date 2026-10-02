# 실행·배포 계약

이 문서는 애플리케이션 환경 변수, 로컬 실행과 Railway 배포 구성을 정의합니다. 설정 변경으로
계약이 달라지는 경우 코드, `.env.example`과 이 문서를 같은 변경에서 함께 갱신합니다. 아래 내용은
배포 대상 구성이며 특정 환경의 배포 완료 상태를 의미하지 않습니다.

## 1. 환경 변수

```text
SESSION_SECRET=
# OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-nano
OPENAI_TIMEOUT_SECONDS=30
DATABASE_URL=sqlite:///./data/chatbot.db
APP_ENV=local
LOG_LEVEL=INFO
ADMIN_USERNAME=admin
# ADMIN_INITIAL_PASSWORD=
PORT=
```

| 이름 | 기본값·허용값 | 용도와 관리 원칙 |
| --- | --- | --- |
| `SESSION_SECRET` | 기본값 없음 | 서명된 세션 쿠키에 사용하는 비밀값. 애플리케이션 시작 전에 비어 있지 않은 값을 제공하고 저장소에 실제 값을 기록하지 않음 |
| `OPENAI_API_KEY` | 기본값 없음 | 서버의 OpenAI API 인증 비밀값. 브라우저에 노출하거나 저장소에 실제 값을 기록하지 않음 |
| `OPENAI_MODEL` | 설정값: `gpt-5-nano` | 대화 답변 생성에 사용할 OpenAI 모델. 현재 비용 우선 선택값 |
| `OPENAI_TIMEOUT_SECONDS` | `30` | OpenAI 요청 시간 제한. 0보다 큰 숫자만 허용 |
| `DATABASE_URL` | 로컬 기본값: `sqlite:///./data/chatbot.db`; 배포 기본값: `sqlite:////data/chatbot.db` | 로컬 SQLite 연결 URL. 운영 환경에서는 명시적으로 설정하지 않으면 애플리케이션 시작을 거부해 임시 파일로의 대체 동작을 막음 |
| `APP_ENV` | `local`; `production` 허용 | 실행 환경을 구분. `production`에서는 운영 환경 보안·설정 검증을 적용 |
| `LOG_LEVEL` | `INFO` | 애플리케이션 로그 수준 |
| `ADMIN_USERNAME` | `admin` | 자동 생성하는 초기 관리자 사용자명. 기본값은 `admin`이며 앞뒤 공백 제거 후 3~30자를 허용 |
| `ADMIN_INITIAL_PASSWORD` | 기본값 없음 | 관리자 역할 계정이 없을 때 초기 관리자 생성에 사용하는 비밀값. 실제 값을 저장소에 기록하지 않음 |
| `PORT` | 기본값 없음 | Railway 변수에서 직접 설정하는 HTTP 서버 포트 |

`ADMIN_INITIAL_PASSWORD`는 관리자 역할 계정이 하나도 없을 때 초기 관리자 생성 과정에서 사용합니다.
기존 관리자 처리, 누락·유효성 실패와 로깅 규칙은 [아키텍처](ARCHITECTURE.md)에서 정의합니다.

## 2. 로컬 실행

1. Python 의존성을 설치합니다.

   ```bash
   uv sync --frozen
   ```

2. `.env.example`을 `.env`로 복사합니다. 애플리케이션 시작에는 `SESSION_SECRET`을, 대화 사용에는
   `OPENAI_API_KEY`와 `OPENAI_MODEL`을 설정합니다. 초기 관리자가 없는 DB에서는
   `ADMIN_INITIAL_PASSWORD`도 설정합니다. `.env`는 커밋하지 않습니다.

3. 애플리케이션을 실행합니다.

   ```bash
   uv run --frozen uvicorn chatbot.main:app --reload
   ```

기본 SQLite 파일은 저장소의 `data/chatbot.db`에 생성됩니다. 스키마와 SQLite 연결 동작은
[DB 스키마 계약](db/DB.md)을 따릅니다.

## 3. Railway 배포

### 변수

- `APP_ENV=production`
- `DATABASE_URL=sqlite:////data/chatbot.db`
- `ADMIN_USERNAME=admin`
- `OPENAI_MODEL=gpt-5-nano`
- `PORT`는 Railway 변수에서 사용할 포트 번호를 직접 설정합니다.
- `SESSION_SECRET`, `OPENAI_API_KEY`, `ADMIN_INITIAL_PASSWORD`는 Railway 변수에서 실제 값을
  제공합니다.
- `OPENAI_TIMEOUT_SECONDS`와 `LOG_LEVEL`은 공통 기본값을 사용하거나 Railway 변수에서 유효한
  값으로 재정의할 수 있습니다.

### 영속 볼륨

- Railway 볼륨 연결 경로는 `/data`입니다.
- SQLite 파일은 `/data/chatbot.db`를 사용합니다.
- 서비스 재시작과 새 배포 후에도 기존 SQLite 데이터가 유지되어야 합니다.

### 시작과 상태 확인

시작 명령:

```bash
uv run --frozen uvicorn chatbot.main:app --host 0.0.0.0 --port $PORT
```

상태 확인 경로:

```text
/health
```

상태 확인의 HTTP 응답 계약은 [API 계약](api/API.md#8-상태-api)을 따릅니다.

## 4. 기존 배포 URL과 외부 실행 검증

### 기존 배포 URL 기록

아래 주소와 응답은 2026-08-11 당시 기록이며 현재 서비스 상태를 보장하지 않습니다. 새 배포 검증에는 자신의 배포 주소를 사용합니다.

배포 URL: https://codyssey-b7-1-production.up.railway.app

운영 환경 서비스 URL은 Railway 서비스에 연결한 공개 HTTPS 도메인입니다. 실제 URL은 배포가
생성하는 환경별 값이므로 소스 코드나 환경 공통 기본값으로 고정하지 않습니다.

### 프로세스 접근성 실행 검증

외부 네트워크에서 발급된 URL을 사용해 다음 실행 검증을 실행합니다.

```bash
DEPLOYMENT_URL=https://codyssey-b7-1-production.up.railway.app
curl --fail --silent --show-error "$DEPLOYMENT_URL/health"
```

정상 응답은 API 상태 계약과 일치해야 합니다. 이 확인은 프로세스 접근성을 검증하며 OpenAI 호출이나
DB 읽기·쓰기 상태를 검사하지 않습니다.

2026-08-11 외부 네트워크에서 위 명령을 실행해 다음 정상 응답을 확인했습니다.

```json
{"status":"ok"}
```

### 배포 후 기능 실행 검증

`/health` 확인과 별도로, 외부 브라우저에서 실제 서비스 기능을 다음 순서로 확인합니다.

1. `/signup`과 `/login`에 접근해 일반 사용자 회원가입과 로그인 흐름을 확인합니다.
2. 로그인한 사용자로 `/chat`에 접근해 질문을 전송하고 AI 답변이 화면에 표시되는지 확인합니다.
3. 관리자 계정으로 로그인한 뒤 `/admin/logs`에 접근해 관리자 운영 메타데이터 화면이 표시되는지
   확인합니다.

이 검증은 인증, 대화 요청·응답과 관리자 권한이 배포 환경에서 함께 동작하는지 확인합니다.
