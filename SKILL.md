---
name: naver-news-briefing
description: Search, brief, and monitor Naver News via the Naver Search API using natural-language Korean queries. Use when the user wants 네이버 뉴스 브리핑, 최근 N일 뉴스 요약, 제외어 포함 뉴스 검색, 여러 질의를 한 번에 묶은 멀티 브리핑, 키워드 그룹 저장/관리, 특정 키워드의 지속 감시 규칙 추가/목록/삭제, or cron-friendly periodic checks that print chat-ready text or JSON summaries. Prefer this skill for local workspace-based Naver news watch workflows backed by persistent state.
---

# naver-news-briefing

Use the CLI script at `scripts/naver_news_briefing.py`.

## Workflow

1. Store credentials once.
   - `python scripts/naver_news_briefing.py setup --client-id ... --client-secret ...`
   - Verify with `python scripts/naver_news_briefing.py check-credentials --json`
2. Run a one-shot briefing.
   - `python scripts/naver_news_briefing.py search "최근 3일 반도체 뉴스 브리핑 -광고"`
   - Add `--json` for machine-readable output.
3. Manage persistent keyword groups for recurring briefings.
   - Add: `python scripts/naver_news_briefing.py group-add market-watch "최근 3일 반도체 -광고" "오늘 AI 데이터센터 -주가" --label "아침 시장" --tag 테크 --tag 모니터링 --context "오전 보고용"`
   - List: `python scripts/naver_news_briefing.py group-list`
   - Inspect one group: `python scripts/naver_news_briefing.py group-list market-watch --json`
   - Update: `python scripts/naver_news_briefing.py group-update market-watch --add-query "배터리 공급망 -광고" --tag 테크 --tag 공급망`
   - Remove: `python scripts/naver_news_briefing.py group-remove market-watch`
4. Run multi-query/group briefings with reusable templates.
   - Group briefing: `python scripts/naver_news_briefing.py brief-multi --group market-watch --template concise`
   - Mixed briefing: `python scripts/naver_news_briefing.py brief-multi --group market-watch --query "환율 뉴스 브리핑" --template morning-briefing --json`
   - Templates: `concise`, `analyst`, `morning-briefing`, `watch-alert`
5. Manage persistent watch rules.
   - Add: `python scripts/naver_news_briefing.py watch-add semiconductor "최근 7일 반도체 -광고"`
   - List: `python scripts/naver_news_briefing.py watch-list`
   - Remove: `python scripts/naver_news_briefing.py watch-remove semiconductor`
6. Run watch checks for cron / automation.
   - All rules: `python scripts/naver_news_briefing.py watch-check`
   - One rule: `python scripts/naver_news_briefing.py watch-check semiconductor --json`

## Behavior

- Parse positive keywords and `-제외어` using the upstream tab-search policy.
- Interpret recent-news phrases such as `오늘`, `최근 3일`, `이번주` as a date window and remove that phrase from the API search query.
- Store config in `data/config.json` and store watch/group state together in `data/watch_state.db`.
- Use DPAPI-backed secret storage on Windows when possible.
- Deduplicate watch notifications by `(watch_id, link)` so repeated cron runs emit only newly seen items.
- Persist keyword groups with ordered queries plus optional `label`, `tags`, and `context` metadata so the same set can be reused across briefing and monitoring workflows.
- `brief-multi` returns chat-friendly combined text by default and structured JSON with `--json`.

## Notes

- Read `references/upstream-notes.md` before major edits.
- The skill uses headline/summary metadata from the Naver Search API. It does not fetch or summarize full article bodies.
- If a natural-language query becomes too chatty, restate it as concise keywords plus `-제외어` tokens before running search/watch commands.
- Keep additions additive: preserve existing `search`, `watch-add`, `watch-list`, `watch-remove`, and `watch-check` flows.
