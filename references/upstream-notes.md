# Upstream notes: `navernews-tabsearch`

Use these notes when extending or debugging the skill.

## Reused patterns

- `core.query_parser.py`
  - Preserve the upstream split between:
    - API query = all positive keywords joined by spaces
    - tab/db keyword = first positive keyword only
    - exclude words = `-단어` tokens
  - Preserve `build_fetch_key(search_query, exclude_words)` normalization.
- `core.config_store.py`
  - Reuse Windows-first credential handling with DPAPI-encrypted `client_secret_enc` and atomic config writes.
- `core.naver_api` + `core.workers_support.api_worker.ApiWorker` (v32.12.0 NAVER API HUB)
  - Reuse request shape: `https://naverapihub.apigw.ntruss.com/search/v1/news`
  - Use gateway headers `X-NCP-APIGW-API-KEY-ID`, `X-NCP-APIGW-API-KEY`
  - Reuse `parse_naver_api_error` (Search flat + Gateway nested + `errMsg`/`errId` 호환) and `format_naver_http_error` (401/403 auth 안내, 429 일일 한도 안내, SE01~SE99 한글 힌트)
  - Legacy Developers Center endpoint로는 되돌리지 않는다. 기존 개발자센터 키는 무효하다.
  - Send `format=json` explicitly, default `sort=date` with `sim` opt-in via `normalize_api_sort`, clean `<b>` tags, prefer `news.naver.com` links when present, filter exclude words on title/description.
  - `lastBuildDate`는 `raw_meta`로 유지한다. 일일 호출량 추적(`core.api_quota`)과 리다이렉트 차단·`Retry-After` 대기는 GUI 연속 새로고침용이라 이 스킬에는 이식하지 않는다.
- Repo persistence style
  - Keep state on local disk inside the skill (`data/`), use atomic JSON for config and SQLite for watch state / dedupe.

## Intentional simplifications vs upstream GUI app

- No PyQt UI, tabs, bookmarks, tray, or backup rotation UI.
- No full article database; only persistent watch rules, keyword groups, and seen-link dedupe for cron-style monitoring.
- Adapt the upstream tab-search/bookmark mindset into CLI-friendly persistent keyword groups (`group-*`) plus combined briefing templates (`brief-multi`) instead of recreating GUI tabs.
- Focus on CLI/stdout output that OpenClaw can relay into chat or scheduled jobs.

## Relevant upstream files

- `README.md`
- `core/query_parser.py`
- `core/config_store.py`
- `core/workers.py`
- `core/database.py`
- `tests/test_query_parser_search_policy.py`
