from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from config_store import get_runtime_credentials, set_credentials
from naver_api import fetch_news
from query_utils import build_intent
from watch_store import add_rule, get_rule, list_rules, mark_seen, remove_rule


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


def cmd_setup(args: argparse.Namespace) -> int:
    set_credentials(args.client_id, args.client_secret, args.timeout)
    print("저장 완료: 네이버 API 자격증명을 data/config.json에 저장했습니다.")
    return 0


def cmd_check_credentials(args: argparse.Namespace) -> int:
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    ok = bool(client_id and client_secret)
    payload = {
        "configured": ok,
        "client_id_present": bool(client_id),
        "client_secret_present": bool(client_secret),
        "timeout": timeout,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else ("OK" if ok else "MISSING"))
    return 0 if ok else 1


def run_search(query: str, *, limit: int, days: int | None, as_json: bool) -> int:
    intent = build_intent(query, limit=limit, days=days)
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    result = fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=intent.search_query,
        exclude_words=intent.exclude_words,
        limit=intent.limit,
        days=intent.days,
        timeout=timeout,
    )
    result["intent"] = {
        "db_keyword": intent.db_keyword,
        "fetch_key": intent.fetch_key,
        "raw_query": intent.raw_query,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n".join(_brief_lines(result)))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    return run_search(args.query, limit=args.limit, days=args.days, as_json=args.json)


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
    )
    print(json.dumps(rule, ensure_ascii=False, indent=2) if args.json else f"등록 완료: {rule['name']} -> {rule['raw_query']}")
    return 0


def cmd_watch_list(args: argparse.Namespace) -> int:
    rules = list_rules()
    if args.json:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        return 0
    if not rules:
        print("등록된 watch rule이 없습니다.")
        return 0
    for rule in rules:
        extra = []
        if rule.get("days"):
            extra.append(f"최근 {rule['days']}일")
        if rule.get("exclude_words"):
            extra.append("제외=" + ", ".join(rule["exclude_words"]))
        extra_txt = f" ({'; '.join(extra)})" if extra else ""
        print(f"- {rule['name']}: {rule['raw_query']}{extra_txt}")
    return 0


def cmd_watch_remove(args: argparse.Namespace) -> int:
    deleted = remove_rule(args.name_or_id)
    if deleted:
        print(f"삭제 완료: {args.name_or_id}")
        return 0
    print(f"삭제 대상 없음: {args.name_or_id}")
    return 1


def _run_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    result = fetch_news(
        client_id=client_id,
        client_secret=client_secret,
        search_query=rule["search_query"],
        exclude_words=rule["exclude_words"],
        limit=rule["limit"],
        days=rule.get("days"),
        timeout=timeout,
    )
    new_items = mark_seen(rule["id"], result["items"])
    return {
        "rule": rule,
        "summary": {
            "query": result["query"],
            "total": result["total"],
            "displayed": result["displayed"],
            "new_count": len(new_items),
            "filtered_out": result["filtered_out"],
            "too_old": result["too_old"],
        },
        "new_items": new_items,
        "all_items": result["items"],
    }


def cmd_watch_check(args: argparse.Namespace) -> int:
    targets = [get_rule(args.name_or_id)] if args.name_or_id else list_rules()
    payload = [_run_rule(rule) for rule in targets]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not payload:
        print("체크할 watch rule이 없습니다.")
        return 0
    lines: List[str] = []
    for entry in payload:
        rule = entry["rule"]
        lines.append(f"## {rule['name']} ({entry['summary']['new_count']}건 신규)")
        lines.extend(_brief_lines({
            "query": rule["search_query"],
            "exclude_words": rule["exclude_words"],
            "days": rule.get("days"),
            "total": entry["summary"]["total"],
            "displayed": len(entry["new_items"]),
            "filtered_out": entry["summary"]["filtered_out"],
            "too_old": entry["summary"]["too_old"],
            "items": entry["new_items"],
        }, title=f"watch: {rule['name']}"))
        lines.append("")
    print("\n".join(lines).strip())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Naver news briefing skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup", help="네이버 API 자격증명 저장")
    p.add_argument("--client-id", required=True)
    p.add_argument("--client-secret", required=True)
    p.add_argument("--timeout", type=int, default=15)
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("check-credentials", help="자격증명 상태 확인")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_check_credentials)

    p = sub.add_parser("search", help="원샷 뉴스 검색/브리핑")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--days", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("watch-add", help="watch rule 추가")
    p.add_argument("name")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--days", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_watch_add)

    p = sub.add_parser("watch-list", help="watch rule 목록")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_watch_list)

    p = sub.add_parser("watch-remove", help="watch rule 삭제")
    p.add_argument("name_or_id")
    p.set_defaults(func=cmd_watch_remove)

    p = sub.add_parser("watch-check", help="watch rule 신규 기사 체크")
    p.add_argument("name_or_id", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_watch_check)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
