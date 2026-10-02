# AI 호출 계약

이 문서는 Chat module이 OpenAI 요청을 구성하는 규칙을 정의합니다. 사용 model, system prompt,
conversation context 선택, OpenAI message role과 순서는 이 문서의 책임입니다. HTTP 결과는
[API 계약](../api/API.md), persistence schema와 저장 동작은 [DB schema 계약](../db/DB.md),
environment variable의 정확한 key와 실행 환경별 값은 [실행·배포 계약](../DEPLOYMENT.md)을
따릅니다.

## 1. 사용 model

Chat은 application 실행 설정에 구성된 OpenAI model을 사용합니다. Model은 user request나 Browser
입력으로 선택하거나 변경할 수 없습니다. 현재 실행 환경에서 사용하는 model 값과 설정 key는
[실행·배포 계약](../DEPLOYMENT.md)을 따릅니다. Chat module은 configured model을 모든 OpenAI
요청에 사용합니다.

## 2. System prompt

모든 OpenAI 요청의 첫 message는 다음 고정 system prompt입니다.

```text
You are a warm, practical conversational assistant. Answer clearly and concisely in the user's language. Use the previous conversation to understand follow-up questions. Ask one focused clarifying question when essential details are missing. Be honest about uncertainty and avoid inventing facts. Use plain text only and do not use Markdown formatting.
```

이 prompt는 user question과 이전 대화보다 앞에 한 번만 포함합니다.

## 3. Conversation context 선택

Chat Service는 현재 login 사용자 ID로 성공한 `ChatExchange`만 조회합니다. 조회 대상은 최신순으로
정렬된 최대 5건이며, OpenAI message를 만들 때는 이를 과거순으로 다시 정렬합니다.

- 다른 사용자의 대화는 context에 포함하지 않습니다.
- `failed` record는 context query에서 제외합니다. 성공 record에 answer가 없으면 message를 만들지 않고
  오류로 처리합니다.
- 이전 성공 대화가 없으면 system prompt와 현재 question만으로 요청을 구성합니다.

저장 record의 status와 query 정책은 [DB schema 계약](../db/DB.md)을 따릅니다.

## 4. Message role과 순서

각 이전 성공 대화는 질문을 `user`, 답변을 `assistant` role로 추가합니다. 현재 question은 항상
마지막 `user` message입니다.

```text
1. system: 고정 system prompt
2. user: 가장 오래된 이전 성공 question
3. assistant: 해당 question의 answer
4. ... 최대 5건의 이전 성공 대화 반복 ...
5. user: 현재 question
```

이 순서는 이전 대화가 최신순으로 API에 전달되는 것을 방지하고, 현재 question이 답변을 생성할
대상임을 보장합니다. 현재 question은 validation과 normalization을 거친 뒤 항상 마지막 `user`
message로 추가합니다. request payload와 validation의 HTTP 계약은 [API 계약](../api/API.md)을
따릅니다.

## 5. 실패·timeout·429 정책

SDK의 자동 retry는 `max_retries=0`으로 끄고, Adapter가 일시적인 429만 최초 호출 이후 최대
2회 재시도합니다. 대기 시간은 `max(2 ** retry_index, Retry-After) + uniform(0, 0.25)`초입니다.
`retry_index`는 0부터 시작하므로 기본 대기는 약 1초, 2초이며 작은 epsilon은 jitter로 사용합니다.
`Retry-After`는 delta seconds와 HTTP date를 지원하고 잘못된 값은 무시합니다.

- epsilon을 더하기 전 대기가 10초보다 길면 즉시 `openai_rate_limited`로 종료하고 필요한
  대기 시간을 `Retry-After` response header로 전달합니다. 요구된 대기를 줄여 조기 재시도하지 않습니다.
- `insufficient_quota`는 재시도하지 않고 `openai_quota_exceeded`로 분류합니다.
- `OPENAI_TIMEOUT_SECONDS`는 호출·backoff 전체 시간 예산이며 SDK 요청 timeout에도 적용합니다.
- Timeout, 다른 API 오류, 빈 응답은 재시도하지 않습니다. 진행 중인 요청과 speculative retry를
  병렬 실행하지 않습니다. Browser는 자동 재전송하지 않습니다.
- 재시도마다 `ai_retry_scheduled` event를 기록합니다. 최종 성공·실패 결과만 한 번 DB에 저장하며
  실패 기록은 이후 대화 context에서 제외합니다.
- 실패를 성공으로 표시하는 fallback answer를 생성하지 않습니다. 첫 choice의 비어 있지 않은
  text content만 answer로 사용합니다.

| 상황 | 추가 재시도 | 처리 |
| --- | ---: | --- |
| 일시적인 429 | 최대 2회 | 지수적 backoff + jitter, 소진 시 429 |
| quota 부족 | 0회 | 503, 관리자 문의 안내 |
| 전체 시간 예산 초과 | 0회 | 504 |
| 다른 OpenAI 오류·비정상 응답 | 0회 | 502 |

HTTP status·사용자 message는 [API 계약](../api/API.md), 저장 정책은 [DB 계약](../db/DB.md)을
따릅니다. Retry 전략의 참고 기준은 [OpenAI rate limit guide](https://developers.openai.com/api/docs/guides/rate-limits)입니다.
