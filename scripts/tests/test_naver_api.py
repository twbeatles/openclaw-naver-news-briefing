import pytest
from nb_api import (
    ALLOWED_API_SORTS,
    API_FORMAT,
    API_KEY_HEADER,
    API_KEY_ID_HEADER,
    API_URL,
    DEFAULT_API_SORT,
    NAVER_SEARCH_ERROR_HINTS,
    apply_naver_error_fields,
    clean_item,
    fetch_news,
    format_naver_http_error,
    naver_auth_headers,
    naver_error_hint,
    normalize_api_sort,
    parse_naver_api_error,
)


class DummyResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, *, headers, params, timeout):
        return DummyResponse(200, self.payload)


SAMPLE = {
    "total": 3,
    "items": [
        {
            "title": "<b>반도체</b> 시장 확대",
            "description": "좋은 뉴스",
            "link": "https://news.naver.com/a",
            "originallink": "https://example.com/a",
            "pubDate": "Wed, 25 Mar 2026 10:00:00 +0900",
        },
        {
            "title": "광고성 기사",
            "description": "광고 포함",
            "link": "https://example.com/b",
            "originallink": "https://example.com/b",
            "pubDate": "Wed, 25 Mar 2026 10:00:00 +0900",
        },
    ],
}


def test_clean_item_prefers_naver_link_and_strips_html():
    item = clean_item(SAMPLE["items"][0])
    assert item.title == "반도체 시장 확대"
    assert item.link == "https://news.naver.com/a"
    assert item.publisher == "example.com"


def test_fetch_news_applies_exclude_words_and_limit():
    result = fetch_news(
        client_id="id",
        client_secret="secret",
        search_query="반도체",
        exclude_words=["광고"],
        limit=5,
        timeout=5,
        session=DummySession(SAMPLE),
    )
    assert result["displayed"] == 1
    assert result["filtered_out"] == 1
    assert result["items"][0]["title"] == "반도체 시장 확대"


def test_api_url_is_naver_api_hub():
    assert API_URL == "https://naverapihub.apigw.ntruss.com/search/v1/news"
    assert "openapi.naver.com" not in API_URL
    assert "news.json" not in API_URL


def test_auth_headers_use_gateway_names():
    headers = naver_auth_headers("  my-id  ", "  my-secret  ")
    assert headers == {API_KEY_ID_HEADER: "my-id", API_KEY_HEADER: "my-secret"}
    assert headers == {
        "X-NCP-APIGW-API-KEY-ID": "my-id",
        "X-NCP-APIGW-API-KEY": "my-secret",
    }
    assert "X-Naver-Client-Id" not in headers
    assert "X-Naver-Client-Secret" not in headers


def test_parse_flat_and_nested_errors():
    code, message = parse_naver_api_error(
        {"errorCode": "SE02", "errorMessage": "Invalid display value"}
    )
    assert (code, message) == ("SE02", "Invalid display value")
    code, message = parse_naver_api_error(
        {
            "error": {
                "errorCode": "200",
                "message": "Authentication Failed",
                "details": "missing",
            }
        }
    )
    assert code == "200"
    assert "Authentication Failed" in message and "missing" in message
    assert parse_naver_api_error({}) == ("", "알 수 없는 오류")
    assert parse_naver_api_error(None) == ("", "알 수 없는 오류")


def test_format_auth_error_points_to_api_hub():
    text = format_naver_http_error(401, "200", "Authentication Failed")
    assert "401" in text and "API HUB" in text and "Authentication Failed" in text


class CapturingSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, *, headers, params, timeout):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return DummyResponse(200, self.payload)


def test_fetch_news_uses_hub_url_and_headers():
    session = CapturingSession(SAMPLE)
    fetch_news(
        client_id="id",
        client_secret="secret",
        search_query="반도체",
        exclude_words=[],
        limit=5,
        timeout=5,
        session=session,
    )
    assert len(session.calls) == 1
    assert (
        session.calls[0]["url"] == "https://naverapihub.apigw.ntruss.com/search/v1/news"
    )
    assert session.calls[0]["headers"] == {
        "X-NCP-APIGW-API-KEY-ID": "id",
        "X-NCP-APIGW-API-KEY": "secret",
    }


class FlakySession:
    def __init__(self, payload):
        self.payload = payload
        self.attempts = 0

    def get(self, url, *, headers, params, timeout):
        self.attempts += 1
        if self.attempts == 1:
            return DummyResponse(
                500, {"errorCode": "SE99", "errorMessage": "일시 오류"}
            )
        return DummyResponse(200, self.payload)


def test_fetch_news_retries_transient_5xx():
    session = FlakySession(SAMPLE)
    result = fetch_news(
        client_id="id",
        client_secret="secret",
        search_query="반도체",
        exclude_words=[],
        limit=5,
        timeout=5,
        session=session,
    )
    assert session.attempts == 2
    assert result["displayed"] == 2


class UnauthorizedSession:
    def get(self, url, *, headers, params, timeout):
        return DummyResponse(401, {"errorCode": "200", "errorMessage": "Auth fail"})


def test_fetch_news_auth_error_is_actionable():
    with pytest.raises(RuntimeError, match="API HUB"):
        fetch_news(
            client_id="id",
            client_secret="secret",
            search_query="반도체",
            exclude_words=[],
            limit=5,
            timeout=5,
            session=UnauthorizedSession(),
        )


def test_search_format_is_json_explicit():
    assert API_FORMAT == "json"


def test_normalize_api_sort_matches_upstream_policy():
    assert DEFAULT_API_SORT == "date"
    assert set(ALLOWED_API_SORTS) == {"date", "sim"}
    assert normalize_api_sort("sim") == "sim"
    assert normalize_api_sort("DATE") == "date"
    assert normalize_api_sort("bogus") == "date"
    assert normalize_api_sort("", fallback="sim") == "sim"
    assert normalize_api_sort(None, fallback="bogus") == "date"


def test_fetch_news_sends_format_and_default_sort():
    session = CapturingSession(SAMPLE)
    result = fetch_news(
        client_id="id",
        client_secret="secret",
        search_query="반도체",
        exclude_words=[],
        limit=5,
        timeout=5,
        session=session,
    )
    assert session.calls[0]["params"]["format"] == "json"
    assert session.calls[0]["params"]["sort"] == "date"
    assert result["sort"] == "date"


def test_fetch_news_accepts_sim_sort():
    session = CapturingSession(SAMPLE)
    result = fetch_news(
        client_id="id",
        client_secret="secret",
        search_query="반도체",
        exclude_words=[],
        limit=5,
        timeout=5,
        sort="sim",
        session=session,
    )
    assert session.calls[0]["params"]["sort"] == "sim"
    assert result["sort"] == "sim"


def test_parse_legacy_err_msg_shape():
    code, message = parse_naver_api_error(
        {"errId": "E001", "errMsg": "legacy failure"}
    )
    assert (code, message) == ("E001", "legacy failure")


def test_error_hint_covers_documented_codes():
    assert "display" in naver_error_hint("SE02")
    assert "1,000" in naver_error_hint("SE03")
    assert "sort" in naver_error_hint("SE04").lower()
    assert naver_error_hint("UNKNOWN_CODE") == ""
    assert set(NAVER_SEARCH_ERROR_HINTS) >= {
        "SE01",
        "SE02",
        "SE03",
        "SE04",
        "SE05",
        "SE06",
        "SE99",
    }


def test_format_bad_request_includes_hint():
    text = format_naver_http_error(400, "SE02", "Invalid display value.")
    assert "400" in text
    assert "SE02" in text
    assert "1~100" in text
    assert "Invalid display value." in text


def test_format_rate_limit_mentions_daily_quota():
    text = format_naver_http_error(429, "", "Too Many Requests")
    assert "429" in text
    assert "25,000" in text
    assert "Too Many Requests" in text


def test_apply_naver_error_fields_fills_mapping():
    target: dict = {}
    code, message = apply_naver_error_fields(
        target, {"errorCode": "SE04", "errorMessage": "bad sort"}
    )
    assert (code, message) == ("SE04", "bad sort")
    assert target == {"error_code": "SE04", "error_message": "bad sort"}
