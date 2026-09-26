from __future__ import annotations

from typing import Any, Mapping, Tuple


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
    return "", "알 수 없는 오류"


def format_naver_http_error(status_code: int, error_code: str, error_message: str) -> str:
    """사용자에게 보여줄 HTTP 오류 문구를 만든다. 401/403은 키 발급처를 안내한다."""
    code = str(error_code or "").strip()
    msg = str(error_message or "").strip() or "알 수 없는 오류"
    status = int(status_code or 0)
    if status in (401, 403):
        base = "인증 실패 — NAVER API HUB Client ID/Secret을 확인하세요."
        if code:
            return f"API 오류 {status} ({code}): {base} {msg}"
        return f"API 오류 {status}: {base} {msg}"
    if code:
        return f"API 오류 {status} ({code}): {msg}"
    return f"API 오류 {status}: {msg}"


__all__ = ["format_naver_http_error", "parse_naver_api_error"]
