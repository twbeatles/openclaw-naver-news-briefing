# naver-news-briefing

Naver News Search API 기반 OpenClaw 스킬입니다.

주요 기능:
- 자연어 한국어 뉴스 검색 / 브리핑
- `-제외어` 포함 검색
- `오늘`, `최근 N일`, `이번주`, `지난주` 같은 최근 기간 해석
- 지속 감시 규칙(watch) 추가 / 목록 / 삭제
- cron 친화적인 watch check 텍스트/JSON 출력
- Windows DPAPI 기반 자격증명 저장 패턴

## Install in OpenClaw

```bash
clawhub install naver-news-briefing
```

또는 이 저장소를 내려받아 스킬 폴더로 복사해 사용할 수 있습니다.

## Quick start

```bash
python scripts/naver_news_briefing.py setup --client-id YOUR_ID --client-secret YOUR_SECRET
python scripts/naver_news_briefing.py check-credentials --json
python scripts/naver_news_briefing.py search "최근 3일 반도체 뉴스 브리핑 -광고"
python scripts/naver_news_briefing.py watch-add semiconductor "최근 7일 반도체 -광고"
python scripts/naver_news_briefing.py watch-check --json
```

## Files

- `SKILL.md`: OpenClaw skill instructions
- `scripts/naver_news_briefing.py`: main CLI entrypoint
- `references/upstream-notes.md`: upstream adaptation notes
- `data/config.json`: local config template

## Notes

- 본문 크롤링은 하지 않고, 네이버 Search API가 제공하는 제목/요약/링크/발행시각 메타데이터를 기반으로 동작합니다.
- watch 중복 제거는 `(watch_id, link)` 기준입니다.
