"""Naver news briefing skill CLI — 얇은 진입점.

실제 구현은 `nb_cli`(명령/서비스/렌더링), `nb_api`, `nb_query`,
`nb_stores`, `nb_briefing`, `nb_planning` 패키지에 있다.
이 모듈은 CLI 실행 경로(`python scripts/naver_news_briefing.py ...`)와
기존 프로그래밍 진입점(`main`, `cmd_*`)을 그대로 유지하기 위한 facade다.
"""

from __future__ import annotations

from nb_cli import (
    ANNOUNCE_PREVIEW_LIMIT,
    MISSING_CREDENTIALS_ERROR,
    build_parser,
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
    main,
)

__all__ = [
    "ANNOUNCE_PREVIEW_LIMIT",
    "MISSING_CREDENTIALS_ERROR",
    "build_parser",
    "cmd_brief_multi",
    "cmd_check_credentials",
    "cmd_group_add",
    "cmd_group_list",
    "cmd_group_remove",
    "cmd_group_update",
    "cmd_integration_plan",
    "cmd_plan",
    "cmd_plan_save",
    "cmd_search",
    "cmd_setup",
    "cmd_watch_add",
    "cmd_watch_check",
    "cmd_watch_list",
    "cmd_watch_remove",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
