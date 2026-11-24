from __future__ import annotations

import argparse
import sys
from typing import List

from nb_briefing import supported_templates
from nb_stores.group_store import list_groups
from nb_stores.watch_store import list_rules

from nb_cli.commands import (
    cmd_brief_multi,
    cmd_check_credentials,
    cmd_group_add,
    cmd_group_list,
    cmd_group_remove,
    cmd_group_update,
    cmd_integration_plan,
    cmd_plan,
    cmd_plan_save,
    cmd_search,
    cmd_setup,
    cmd_watch_add,
    cmd_watch_check,
    cmd_watch_list,
    cmd_watch_remove,
)
from nb_cli.rendering import (
    _format_missing_named_resource,
    _render_missing_credentials_guidance,
)

MISSING_CREDENTIALS_ERROR = "네이버 API 자격증명이 설정되지 않았습니다."


def _format_exception_message(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    if MISSING_CREDENTIALS_ERROR in message:
        return _render_missing_credentials_guidance()
    if "keyword group not found:" in message:
        missing_name = (
            message.split("keyword group not found:", 1)[1].strip().strip("'")
        )
        available = [
            str(group.get("name")) for group in list_groups() if group.get("name")
        ]
        return _format_missing_named_resource("키워드 그룹", missing_name, available)
    if "watch rule not found:" in message:
        missing_name = message.split("watch rule not found:", 1)[1].strip().strip("'")
        available = [str(rule.get("name")) for rule in list_rules() if rule.get("name")]
        return _format_missing_named_resource("watch rule", missing_name, available)
    return f"ERROR: {message}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Naver news briefing skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup", help="네이버 API 자격증명 저장")
    p.add_argument("--client-id")
    p.add_argument("--client-secret")
    p.add_argument("--timeout", type=int, default=15)
    p.add_argument(
        "--live-check",
        action="store_true",
        help="저장 직후 실제 API 호출로 자격증명을 확인",
    )
    p.add_argument(
        "--test-search", help="저장 직후 테스트할 검색어 (설정 시 라이브 체크 수행)"
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("check-credentials", help="자격증명 상태 확인")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--live-check", action="store_true", help="실제 API 호출까지 포함해 확인"
    )
    p.add_argument("--query", help="라이브 체크용 검색어")
    p.set_defaults(func=cmd_check_credentials)

    p = sub.add_parser("search", help="원샷 뉴스 검색/브리핑")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--days", type=int)
    p.add_argument("--sort", choices=["date", "sim"], default="date")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("watch-add", help="watch rule 추가")
    p.add_argument("name")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--days", type=int)
    p.add_argument("--label")
    p.add_argument("--tag", action="append")
    p.add_argument("--context")
    p.add_argument("--template", choices=supported_templates())
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
    p.add_argument(
        "--announce-text",
        action="store_true",
        help="cron/announce friendly plain text output",
    )
    p.set_defaults(func=cmd_watch_check)

    p = sub.add_parser("group-add", help="키워드 그룹 추가")
    p.add_argument("name")
    p.add_argument("query", nargs="+")
    p.add_argument("--label")
    p.add_argument("--tag", action="append")
    p.add_argument("--context")
    p.add_argument("--template", choices=supported_templates())
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_group_add)

    p = sub.add_parser("group-list", help="키워드 그룹 조회/목록")
    p.add_argument("name_or_id", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_group_list)

    p = sub.add_parser("group-remove", help="키워드 그룹 삭제")
    p.add_argument("name_or_id")
    p.set_defaults(func=cmd_group_remove)

    p = sub.add_parser("group-update", help="키워드 그룹 수정")
    p.add_argument("name_or_id")
    p.add_argument("--label")
    p.add_argument("--context")
    p.add_argument("--template", choices=supported_templates())
    p.add_argument("--tag", action="append")
    p.add_argument("--clear-tags", action="store_true")
    p.add_argument("--set-query", action="append")
    p.add_argument("--add-query", action="append")
    p.add_argument("--remove-query", action="append")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_group_update)

    p = sub.add_parser("brief-multi", help="여러 쿼리/그룹을 묶어 한 번에 브리핑")
    p.add_argument("--query", action="append")
    p.add_argument("--group", action="append")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--days", type=int)
    p.add_argument("--sort", choices=["date", "sim"], default="date")
    p.add_argument("--template", choices=supported_templates())
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_brief_multi)

    p = sub.add_parser("plan", help="채팅형 자연어 요청을 자동화 계획으로 변환")
    p.add_argument("request")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser(
        "integration-plan", help="자연어 요청을 OpenClaw/cron 연동 번들로 변환"
    )
    p.add_argument("request")
    p.add_argument("--channel", default="telegram")
    p.add_argument("--skill-dir")
    p.add_argument("--output")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_integration_plan)

    p = sub.add_parser(
        "plan-save", help="자연어 요청을 해석해 watch/group 설정으로 저장"
    )
    p.add_argument("request")
    p.add_argument("--name")
    p.add_argument("--as", dest="as_type", choices=["watch", "group"])
    p.add_argument("--label")
    p.add_argument("--tag", action="append")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_plan_save)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(_format_exception_message(exc), file=sys.stderr)
        return 1


__all__ = ["MISSING_CREDENTIALS_ERROR", "build_parser", "main"]
