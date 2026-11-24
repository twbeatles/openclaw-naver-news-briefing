from __future__ import annotations

import argparse
from typing import Any, Dict, List

from nb_briefing import (
    build_combined_payload,
    render_combined_json,
    render_combined_text,
)
from nb_stores.group_store import get_group

from nb_cli.services import _run_query_entry


def cmd_brief_multi(args: argparse.Namespace) -> int:
    entries: List[Dict[str, Any]] = []
    groups: List[Dict[str, Any]] = []
    template = args.template
    sort = getattr(args, "sort", "date") or "date"
    for group_name in args.group or []:
        group = get_group(group_name)
        groups.append(group)
        if not args.template and group.get("template"):
            template = group["template"]
        for query in group["queries"]:
            entries.append(
                _run_query_entry(
                    query, limit=args.limit, days=args.days, sort=sort, group=group
                )
            )
    for query in args.query or []:
        entries.append(
            _run_query_entry(query, limit=args.limit, days=args.days, sort=sort)
        )
    if not entries:
        raise ValueError(
            "brief-multi에는 --query 또는 --group이 최소 1개 이상 필요합니다."
        )
    payload = build_combined_payload(entries, template=template, source_groups=groups)
    if args.json:
        print(render_combined_json(payload))
    else:
        print(render_combined_text(payload))
    return 0


__all__ = ["cmd_brief_multi"]
