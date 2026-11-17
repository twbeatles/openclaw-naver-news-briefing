from __future__ import annotations

import html
import json
import re
from datetime import datetime
from typing import Any, Callable, Dict, List


def _strip_html(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip()


def _brief_lines(result: Dict[str, Any], *, title: str | None = None) -> List[str]:
    lines: List[str] = []
    heading = title or f"네이버 뉴스 브리핑: {result['query']}"
    suffix = []
    if result.get("exclude_words"):
        suffix.append("제외=" + ", ".join(result["exclude_words"]))
    if result.get("days"):
        suffix.append(f"최근 {result['days']}일")
    meta = f" ({'; '.join(suffix)})" if suffix else ""
    lines.append(heading + meta)
    lines.append(f"- 총 검색 결과: {result.get('total', 0)}")
    lines.append(f"- 출력 기사 수: {result.get('displayed', 0)}")
    if result.get("filtered_out"):
        lines.append(f"- 제외어로 걸러진 수: {result['filtered_out']}")
    if result.get("too_old"):
        lines.append(f"- 기간 조건으로 제외된 수: {result['too_old']}")
    items = result.get("items", [])
    if not items:
        lines.append("- 새로 보여줄 기사가 없습니다.")
        return lines
    for idx, item in enumerate(items, start=1):
        publisher = item.get("publisher", "정보 없음")
        pub_date = item.get("pub_date", "")
        lines.append(f"{idx}. [{publisher}] {item.get('title', '').strip()}")
        if item.get("description"):
            lines.append(f"   - {item['description'].strip()[:180]}")
        if pub_date:
            lines.append(f"   - 발행: {pub_date}")
        if item.get("link"):
            lines.append(f"   - 링크: {item['link']}")
    return lines


def _print_payload(
    payload: Any, *, as_json: bool, render_text: Callable[[Any], str] | None = None
) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload) if render_text else payload)


def _format_watch_text(rule: Dict[str, Any]) -> str:
    extra = []
    if rule.get("days"):
        extra.append(f"최근 {rule['days']}일")
    if rule.get("exclude_words"):
        extra.append("제외=" + ", ".join(rule["exclude_words"]))
    if rule.get("template"):
        extra.append(f"template={rule['template']}")
    if rule.get("schedule", {}).get("label"):
        extra.append(f"schedule={rule['schedule']['label']}")
    lines = [
        f"- {rule['name']}: {rule['raw_query']}"
        + (f" ({'; '.join(extra)})" if extra else "")
    ]
    if rule.get("label"):
        lines.append(f"  label: {rule['label']}")
    if rule.get("tags"):
        lines.append("  tags: " + ", ".join(rule["tags"]))
    if rule.get("context"):
        lines.append(f"  context: {rule['context']}")
    return "\n".join(lines)


def _format_watch_status_lines(entry: Dict[str, Any]) -> List[str]:
    rule = entry["rule"]
    summary = entry["summary"]
    items = entry.get("all_items", [])
    now = datetime.now().strftime("%m월 %d일 %H:%M")
    query = summary.get("query") or rule.get("search_query") or rule.get("name")
    current_top_count = len(items)
    new_count = summary["new_count"]
    lines = [
        f"## {rule['name']}",
        f"- {now} 기준, '{query}' 관련 상위 {current_top_count}건을 확인했고 이번 체크에서 신규 기사 {new_count}건이 추가됐습니다.",
        f"- 전체 검색 결과: {summary.get('total', 0)}건",
        f"- 이번 확인 신규 기사: {new_count}건",
        f"- 현재 검색 상위 기사 수: {current_top_count}건",
    ]
    if items:
        latest_pub = next(
            (
                item.get("pub_date_iso") or item.get("pub_date")
                for item in items
                if item.get("pub_date_iso") or item.get("pub_date")
            ),
            None,
        )
        if latest_pub:
            lines.append(f"- 현재 기준 최신 기사 시각: {latest_pub}")
    return lines


def _format_group_text(group: Dict[str, Any]) -> str:
    lines = [f"- {group['name']} ({group['query_count']}개 쿼리)"]
    if group.get("label"):
        lines.append(f"  label: {group['label']}")
    if group.get("tags"):
        lines.append("  tags: " + ", ".join(group["tags"]))
    if group.get("template"):
        lines.append(f"  template: {group['template']}")
    if group.get("schedule", {}).get("label"):
        lines.append(f"  schedule: {group['schedule']['label']}")
    if group.get("context"):
        lines.append(f"  context: {group['context']}")
    for idx, query in enumerate(group.get("queries", []), start=1):
        lines.append(f"  {idx}. {query}")
    return "\n".join(lines)


DEFAULT_TEST_QUERY = "최근 1일 반도체 뉴스"


def _render_setup_success(
    timeout: int, *, live_checked: bool = False, live_query: str | None = None
) -> str:
    lines = [
        "네이버 Search API 자격증명을 저장했습니다.",
        "- 저장 위치: data/config.json",
        f"- 요청 타임아웃: {timeout}초",
    ]
    if live_checked:
        lines.append(f"- 라이브 API 확인: 성공 ({live_query or DEFAULT_TEST_QUERY})")
    else:
        lines.append("- 라이브 API 확인: 생략")
    lines.extend(
        [
            "- 다음 단계: python scripts/naver_news_briefing.py check-credentials --json",
            '- 그 다음: python scripts/naver_news_briefing.py search "최근 3일 반도체 뉴스 브리핑"',
        ]
    )
    return "\n".join(lines)


def _render_check_credentials_text(payload: Dict[str, Any]) -> str:
    lines = [
        "네이버 Search API 자격증명이 설정되어 있습니다."
        if payload["configured"]
        else "아직 네이버 Search API 자격증명이 설정되지 않았습니다.",
        f"- client_id 저장 여부: {'예' if payload['client_id_present'] else '아니오'}",
        f"- client_secret 저장 여부: {'예' if payload['client_secret_present'] else '아니오'}",
        f"- 요청 타임아웃: {payload['timeout']}초",
    ]
    live_check = payload.get("live_check")
    if isinstance(live_check, dict):
        if live_check.get("ok"):
            lines.append(f"- 라이브 API 확인: 성공 ({live_check.get('query')})")
            lines.append(
                f"- 테스트 결과: total={live_check.get('total', 0)}, displayed={live_check.get('displayed', 0)}"
            )
        else:
            lines.append(f"- 라이브 API 확인: 실패 ({live_check.get('query')})")
            if live_check.get("error"):
                lines.append(f"- 오류: {live_check['error']}")
    if payload["configured"]:
        lines.append(
            "- 다음 단계: search / watch / brief-multi / plan-save 를 실행하면 됩니다."
        )
    else:
        lines.append("- 먼저 실행: python scripts/naver_news_briefing.py setup")
        lines.append(
            "- 확인: python scripts/naver_news_briefing.py check-credentials --json"
        )
    return "\n".join(lines)


def _render_missing_credentials_guidance() -> str:
    return "\n".join(
        [
            "네이버 Search API 자격증명이 아직 설정되지 않았습니다.",
            "먼저 최초 온보딩(setup)을 완료해 주세요.",
            "",
            "실행 순서:",
            "1) python scripts/naver_news_briefing.py setup --client-id YOUR_ID --client-secret YOUR_SECRET",
            "2) python scripts/naver_news_briefing.py check-credentials --json",
            "3) 그 다음 search / watch / brief-multi / plan-save 명령을 실행",
            "",
            "참고: 자격증명은 data/config.json 에 저장되며 Windows에서는 가능하면 DPAPI로 보호합니다.",
        ]
    )


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _format_missing_named_resource(
    resource_label: str, missing_name: str, available_names: List[str]
) -> str:
    lines = [f"등록된 {resource_label}을(를) 찾지 못했습니다: {missing_name}"]
    if available_names:
        lines.append("현재 등록된 항목: " + ", ".join(available_names))
    else:
        lines.append("현재 등록된 항목이 없습니다.")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_TEST_QUERY",
    "_brief_lines",
    "_dedupe_preserve_order",
    "_format_group_text",
    "_format_missing_named_resource",
    "_format_watch_status_lines",
    "_format_watch_text",
    "_print_payload",
    "_render_check_credentials_text",
    "_render_missing_credentials_guidance",
    "_render_setup_success",
    "_strip_html",
]
