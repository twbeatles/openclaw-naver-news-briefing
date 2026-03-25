from query_utils import build_intent, parse_search_query, parse_tab_query


def test_parse_queries_match_upstream_policy():
    assert parse_search_query("인공지능 AI -광고 -코인") == ("인공지능 AI", ["광고", "코인"])
    assert parse_tab_query("인공지능 AI -광고 -코인") == ("인공지능", ["광고", "코인"])


def test_build_intent_detects_recent_days_and_strips_briefing_words():
    intent = build_intent("최근 3일 반도체 뉴스 브리핑 -광고", limit=7)
    assert intent.search_query == "반도체"
    assert intent.exclude_words == ["광고"]
    assert intent.days == 3
    assert intent.limit == 7
