from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Tuple


def parse_naver_api_error(payload: Any) -> Tuple[str, str]:
    """Search 평면(flat)과 Gateway 중첩(nested) 오류를 모두 파싱한다."""
    if not isinstance(payload, Mapping):
        return "", "알 수 없는 오류"
    flat_code = str(payload.get("errorCode", "") or "").strip()
    flat_msg = str(payload.get("errorMessage", "") or "").strip()
    if flat_code or flat_msg:
        return flat_code, flat_msg or "알 수 없는 오류"
    nested = payload.get("error")
    if isinstance(nested, Mapping):
        nested_code = str(nested.get("errorCode", "") or "").strip()
        nested_msg = str(nested.get("message", "") or "").strip()
        details = str(nested.get("details", "") or "").strip()
        if details and nested_msg and details not in nested_msg:
            message = f"{nested_msg} ({details})"
        else:
            message = nested_msg or details or "알 수 없는 오류"
        if nested_code or message != "알 수 없는 오류":
            return nested_code, message
    # Search Trend / Shopping Insight 스타일(errMsg/errId) — news에는 쓰이지 않지만
    # 게이트웨이가 이 형태로 내려줄 수 있어 하위 호환용으로 둔다.
    # Upstream: navernews-tabsearch core/naver_api.py (v32.12.0).
    err_msg = str(payload.get("errMsg", "") or "").strip()
    err_id = str(payload.get("errId", "") or "").strip()
    if err_msg or err_id:
        return err_id, err_msg or "알 수 없는 오류"
    return "", "알 수 없는 오류"


def format_naver_http_error(
    status_code: int, error_code: str, error_message: str
) -> str:
    """사용자에게 보여줄 HTTP 오류 문구를 만든다. 401/403은 키 발급처를 안내한다."""
    code = str(error_code or "").strip()
    msg = str(error_message or "").strip() or "알 수 없는 오류"
    status = int(status_code or 0)
    if status in (401, 403):
        base = "인증 실패 — NAVER API HUB Client ID/Secret을 확인하세요."
        if code:
            return f"API 오류 {status} ({code}): {base} {msg}"
        return f"API 오류 {status}: {base} {msg}"

    if status == 429:
        base = (
            "API 요청 제한 초과 — 잠시 후 다시 시도해주세요. "
            "(Search API 일일 호출 한도 25,000건에 포함될 수 있으니 "
            "자동 새로고침 간격을 확인하세요.)"
        )
        if code:
            return f"API 오류 {status} ({code}): {base} {msg}"
        return f"API 오류 {status}: {base} {msg}"

    hint = naver_error_hint(code)
    if status in (400, 404) and hint:
        return f"API 오류 {status} ({code}): {hint} {msg}"

    if code:
        if hint:
            return f"API 오류 {status} ({code}): {hint} {msg}"
        return f"API 오류 {status} ({code}): {msg}"
    return f"API 오류 {status}: {msg}"


# 공식 문서(2026-10-08 개정) 기준 Search API 오류 코드별 안내.
# https://api.ncloud-docs.com/docs/en/naver-api-hub-search-news
# Upstream: navernews-tabsearch core/naver_api.py (v32.12.0).
NAVER_SEARCH_ERROR_HINTS = {
    "SE01": "검색어(query)를 확인하세요. URL·파라미터 오타나 빈 검색어가 원인일 수 있습니다.",
    "SE02": "display 값은 1~100 범위여야 합니다.",
    "SE03": "start 값은 1~1,000 범위여야 합니다.",
    "SE04": "sort 값은 sim(정확도순) 또는 date(최신순)여야 합니다.",
    "SE05": "요청 URL을 확인하세요. (잘못된 검색 API 경로)",
    "SE06": "검색어를 UTF-8로 인코딩해야 합니다.",
    "SE99": "네이버 서버 내부 오류입니다. 잠시 후 다시 시도해주세요.",
}


def naver_error_hint(error_code: str) -> str:
    """Search API 오류 코드(SE01~SE99)에 대한 한글 안내를 반환한다."""
    return NAVER_SEARCH_ERROR_HINTS.get(str(error_code or "").strip().upper(), "")


def apply_naver_error_fields(
    target: MutableMapping[str, Any],
    payload: Any,
) -> Tuple[str, str]:
    """파싱 결과를 target dict에 error_code/error_message로 채운다."""
    code, message = parse_naver_api_error(payload)
    target["error_code"] = code
    target["error_message"] = message
    return code, message


__all__ = [
    "NAVER_SEARCH_ERROR_HINTS",
    "apply_naver_error_fields",
    "format_naver_http_error",
    "naver_error_hint",
    "parse_naver_api_error",
]
