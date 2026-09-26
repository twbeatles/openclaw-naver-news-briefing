import pytest
from nb_api import (
    API_KEY_HEADER,
    API_KEY_ID_HEADER,
    API_URL,
    clean_item,
    fetch_news,
    format_naver_http_error,
    naver_auth_headers,
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
    assert headers == {"X-NCP-APIGW-API-KEY-ID": "my-id", "X-NCP-APIGW-API-KEY": "my-secret"}
    assert "X-Naver-Client-Id" not in headers
    assert "X-Naver-Client-Secret" not in headers


def test_parse_flat_and_nested_errors():
    code, message = parse_naver_api_error({"errorCode": "SE02", "errorMessage": "Invalid display value"})
    assert (code, message) == ("SE02", "Invalid display value")
    code, message = parse_naver_api_error(
        {"error": {"errorCode": "200", "message": "Authentication Failed", "details": "missing"}}
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
    assert session.calls[0]["url"] == "https://naverapihub.apigw.ntruss.com/search/v1/news"
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
            return DummyResponse(500, {"errorCode": "SE99", "errorMessage": "일시 오류"})
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
