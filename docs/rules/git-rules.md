# Git 규칙

## 브랜치

- 장기 브랜치는 `main`만 사용합니다.
- 작업 브랜치는 `feature/*` 형식으로 만듭니다.
- `develop` 브랜치는 만들지 않습니다.
- `main` 직접 push를 금지합니다.

## 커밋

- `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:` 형식을 사용합니다.
- `test:`는 테스트 코드의 추가·수정·정리에 사용합니다.
- `refactor:`는 동작 변경 없는 운영 환경 코드 구조 개선에 사용합니다.
- 한 커밋은 한 가지 목적만 가지며, 단순 줄바꿈이나 파일 이동만으로 수를 채우지 않습니다.

```text
feat: description

- Detail 1
- Detail 2
- Detail 3
```
