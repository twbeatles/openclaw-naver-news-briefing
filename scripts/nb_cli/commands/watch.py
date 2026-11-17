from __future__ import annotations

import argparse
import json
from typing import List

from nb_query import build_intent
from nb_stores.watch_store import add_rule, get_rule, list_rules, remove_rule

from nb_cli.rendering import (
    _brief_lines,
    _format_watch_status_lines,
    _format_watch_text,
    _print_payload,
    _strip_html,
)
from nb_cli.services import _run_rule

ANNOUNCE_PREVIEW_LIMIT = 10


def cmd_watch_add(args: argparse.Namespace) -> int:
    intent = build_intent(args.query, limit=args.limit, days=args.days)
    rule = add_rule(
        name=args.name,
        raw_query=intent.raw_query,
        search_query=intent.search_query,
        db_keyword=intent.db_keyword,
        exclude_words=intent.exclude_words,
        fetch_key=intent.fetch_key,
        days=intent.days,
        limit=intent.limit,
        label=args.label,
        tags=args.tag,
        context=args.context,
        template=args.template,
    )
    _print_payload(rule, as_json=args.json, render_text=_format_watch_text)
    return 0


def cmd_watch_list(args: argparse.Namespace) -> int:
    rules = list_rules()
    if args.json:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        return 0
    if not rules:
        print("등록된 watch rule이 없습니다.")
        return 0
    print("\n\n".join(_format_watch_text(rule) for rule in rules))
    return 0


def cmd_watch_remove(args: argparse.Namespace) -> int:
    deleted = remove_rule(args.name_or_id)
    if deleted:
        print(f"삭제 완료: {args.name_or_id}")
        return 0
    print(f"삭제 대상 없음: {args.name_or_id}")
    return 1


def cmd_watch_check(args: argparse.Namespace) -> int:
    targets = [get_rule(args.name_or_id)] if args.name_or_id else list_rules()
    payload = [_run_rule(rule) for rule in targets]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not payload:
        print("체크할 watch rule이 없습니다.")
        return 0
    if getattr(args, "announce_text", False):
        if len(payload) != 1:
            print("NO_REPLY")
            return 0
        entry = payload[0]
        new_items = entry.get("new_items", [])
        if not new_items:
            print("NO_REPLY")
            return 0
        summary = entry.get("summary", {})
        new_count = summary.get("new_count", len(new_items))
        latest_iso = new_items[0].get("pub_date_iso")
        latest_text = latest_iso.replace("T", " ")[:16] if latest_iso else "최신 없음"
        preview_items = new_items[:ANNOUNCE_PREVIEW_LIMIT]
        lines = [
            f"확인 요약: 새 뉴스 {new_count}건, 현재 검색 상위 {summary.get('displayed', 0)}건 / 전체 {summary.get('total', 0)}건, 최신 {latest_text}"
        ]
        for item in preview_items:
            title = _strip_html(item.get("title", "제목 없음"))
            publisher = item.get("publisher") or "정보 없음"
            pub_iso = item.get("pub_date_iso")
            pub_text = (
                pub_iso.replace("T", " ")[:16]
                if pub_iso
                else item.get("pub_date", "시간 없음")
            )
            link = item.get("link") or item.get("original_link") or ""
            lines.append(f"- {title} / {publisher} / {pub_text} / {link}")
        extra_count = max(0, new_count - len(preview_items))
        if extra_count > 0:
            lines.append(f"- 외 추가 새 뉴스 {extra_count}건")
        print("\n".join(lines))
        return 0
    lines: List[str] = []
    for entry in payload:
        rule = entry["rule"]
        lines.extend(_format_watch_status_lines(entry))
        lines.extend(
            _brief_lines(
                {
                    "query": rule["search_query"],
                    "exclude_words": rule["exclude_words"],
                    "days": rule.get("days"),
                    "total": entry["summary"]["total"],
                    "displayed": len(entry["new_items"]),
                    "filtered_out": entry["summary"]["filtered_out"],
                    "too_old": entry["summary"]["too_old"],
                    "items": entry["new_items"],
                },
                title=f"watch: {rule['name']} 신규 기사 요약",
            )
        )
        lines.append("")
    print("\n".join(lines).strip())
    return 0


__all__ = [
    "ANNOUNCE_PREVIEW_LIMIT",
    "cmd_watch_add",
    "cmd_watch_check",
    "cmd_watch_list",
    "cmd_watch_remove",
]
