# naver-news-briefing

OpenClaw skill for Naver News briefing, watch rules, keyword groups, and multi-query briefing templates via the Naver Search API.

## Features
- natural-language Korean query handling
- recent-window interpretation (`오늘`, `최근 N일`, `이번주`, `지난주`)
- exclude-word support via `-키워드`
- one-shot search / briefing
- persistent watch rules
- keyword groups
- multi-briefing templates: `concise`, `analyst`, `morning-briefing`, `watch-alert`
- chat-friendly text and JSON output

## Quick start
```bash
python scripts/naver_news_briefing.py setup --client-id YOUR_ID --client-secret YOUR_SECRET
python scripts/naver_news_briefing.py search "최근 3일 반도체 뉴스 브리핑 -광고"
python scripts/naver_news_briefing.py group-add market-watch "최근 3일 반도체 -광고" "오늘 AI 데이터센터 -주가"
python scripts/naver_news_briefing.py brief-multi --group market-watch --template morning-briefing
```

## Install
```bash
clawhub install naver-news-briefing
```
