# naver-news-briefing

네이버 Search API 기반으로 **뉴스 검색 / 브리핑 / 지속 감시 / 키워드 그룹 / 멀티 브리핑**을 수행하는 OpenClaw 스킬입니다.

이 스킬은 GUI 앱이 아니라 **채팅형 자동화**에 맞춰 설계되어 있습니다. 즉, 한 번 검색하고 끝내는 용도뿐 아니라:
- 특정 주제를 계속 감시하고
- 새 기사만 추려서 보고하고
- 여러 주제를 한 번에 묶어 아침 브리핑을 만들고
- cron/메시징 레이어에 연결해 자동으로 알려주는
흐름에 최적화되어 있습니다.

## 핵심 기능

- 한국어 자연어 질의 기반 뉴스 검색
- `-제외어` 기반 필터링
- 최근 기간 해석
  - `오늘`
  - `최근 3일`
  - `최근 2주`
  - `한달`
  - `이번주`
  - `지난주`
- 문장형 한국어 요청 정규화
  - 예: `삼성전자 관련해서 증권사 리포트 말고 최근 일주일 핵심만 알려줘`
- 원샷 브리핑
- watch rule 저장/목록/삭제/체크
- 키워드 그룹 저장/관리
- 여러 질의를 묶은 멀티 브리핑
- 템플릿 지원
  - `concise`
  - `analyst`
  - `morning-briefing`
  - `watch-alert`
- chat-friendly text / machine-friendly JSON 출력
- Windows DPAPI 기반 자격증명 저장 패턴

## 이 스킬이 잘 맞는 요청 예시

- `최근 3일 반도체 뉴스 브리핑해줘`
- `삼성전자 뉴스에서 증권사 리포트 말고 최근 일주일 핵심만 보고 싶어`
- `AI 데이터센터 뉴스 계속 감시해줘`
- `반도체, 환율, 2차전지 뉴스 묶어서 아침 브리핑 만들어줘`
- `새 기사만 1시간마다 체크해서 알려주는 파이프라인 만들고 싶어`

## 설치

### ClawHub로 설치

```bash
clawhub install naver-news-briefing
```

### 로컬에서 바로 사용

```bash
python scripts/naver_news_briefing.py --help
```

## 사전 준비

네이버 개발자센터에서 Search API 자격증명을 발급받아야 합니다.

```bash
python scripts/naver_news_briefing.py setup --client-id YOUR_ID --client-secret YOUR_SECRET
python scripts/naver_news_briefing.py check-credentials --json
```

## 빠른 시작

### 1) 원샷 뉴스 브리핑

```bash
python scripts/naver_news_briefing.py search "최근 3일 반도체 뉴스 브리핑 -광고"
```

### 2) JSON 출력

```bash
python scripts/naver_news_briefing.py search "삼성전자 관련해서 증권사 리포트 말고 최근 일주일 핵심만 알려줘" --json
```

### 3) watch rule 추가

```bash
python scripts/naver_news_briefing.py watch-add semiconductor "최근 7일 반도체 -광고"
```

### 4) watch 점검

```bash
python scripts/naver_news_briefing.py watch-check
python scripts/naver_news_briefing.py watch-check --json
```

## 키워드 그룹

반복적으로 함께 보는 주제들을 하나의 그룹으로 저장할 수 있습니다.

### 그룹 추가

```bash
python scripts/naver_news_briefing.py group-add market-watch \
  "최근 3일 반도체 -광고" \
  "오늘 AI 데이터센터 -주가" \
  --label "아침 시장" \
  --tag 테크 \
  --tag 모니터링 \
  --context "오전 보고용"
```

### 그룹 목록

```bash
python scripts/naver_news_briefing.py group-list
python scripts/naver_news_briefing.py group-list market-watch --json
```

### 그룹 수정

```bash
python scripts/naver_news_briefing.py group-update market-watch --add-query "배터리 공급망 -광고" --tag 공급망
```

### 그룹 삭제

```bash
python scripts/naver_news_briefing.py group-remove market-watch
```

## 멀티 브리핑

여러 질의나 그룹을 묶어서 한 번에 브리핑할 수 있습니다.

### 그룹 기반 브리핑

```bash
python scripts/naver_news_briefing.py brief-multi --group market-watch --template concise
```

### 그룹 + 직접 질의 혼합

```bash
python scripts/naver_news_briefing.py brief-multi \
  --group market-watch \
  --query "환율 뉴스 브리핑" \
  --template morning-briefing --json
```

## 출력 모드

- 기본: 사람이 읽기 쉬운 한국어 브리핑 텍스트
- `--json`: 자동화/상위 레이어 연동용 구조화 출력

이 구조 덕분에 OpenClaw cron, Telegram, Discord, 다른 브리핑 워크플로우에 바로 붙이기 쉽습니다.

## 자연어 처리 범위

현재는 **검색 친화형 한국어 자연어**에 최적화되어 있습니다.

잘 되는 입력 예시:
- `최근 3일 반도체 뉴스 브리핑 -광고`
- `삼성전자 관련해서 최근 일주일 핵심 뉴스만 브리핑해줘`
- `삼성전자 관련해서 증권사 리포트 말고 최근 일주일 핵심만 알려줘`
- `AI 데이터센터 뉴스 중에 주가 얘기 빼고 이번주만`

가장 안정적인 형식은:
- 기간 표현 + 핵심 키워드 + 제외어

예:
- `최근 7일 반도체 공급망 -광고 -주가`

## 저장 파일

- `data/config.json`: API 자격증명 및 기본 설정
- `data/watch_state.db`: watch/group 상태 저장
- `references/upstream-notes.md`: upstream 앱에서 어떤 개념을 가져왔는지 정리한 메모

## 테스트

```bash
python -m pytest scripts/tests -q
```

## 한계

- 기사 **본문 크롤링/본문 요약**은 하지 않습니다.
- 네이버 Search API가 제공하는 **제목 / 요약 / 링크 / 발행시각** 메타데이터를 기반으로 브리핑합니다.
- 자연어 처리는 실용형 정규화 수준이며, 완전 자유 대화형 intent parser는 아닙니다.
- watch dedupe는 `(watch_id, link)` 기준이라 기사 링크가 같으면 재알림하지 않습니다.

## 왜 이 스킬이 유용한가

기존 GUI형 뉴스 수집/관리 앱의 핵심 개념을 가져오되, OpenClaw에서 바로 쓰기 좋게 바꿨습니다.
즉, **검색 도구**가 아니라:
- 자동 브리핑 엔진
- 뉴스 감시 엔진
- 주제 그룹 관리 도구
- cron 친화형 텍스트/JSON 출력기
로 쓰는 쪽에 더 가깝습니다.
