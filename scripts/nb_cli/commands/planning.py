from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from nb_planning import (
    build_integration_bundle,
    parse_automation_request,
    plan_to_dict,
    render_integration_bundle_text,
    render_plan_text,
)
from nb_query import build_intent
from nb_stores.group_store import create_group
from nb_stores.watch_store import add_rule

from nb_cli.rendering import _dedupe_preserve_order, _print_payload


def cmd_plan(args: argparse.Namespace) -> int:
    plan = parse_automation_request(args.request)
    _print_payload(
        plan_to_dict(plan),
        as_json=args.json,
        render_text=lambda _: render_plan_text(plan),
    )
    return 0


def cmd_integration_plan(args: argparse.Namespace) -> int:
    bundle = build_integration_bundle(
        args.request,
        # scripts/nb_cli/commands/planning.py -> parents[3] == 스킬 루트
        skill_dir=args.skill_dir or str(Path(__file__).resolve().parents[3]),
        assistant_channel=args.channel,
    )
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as fp:
            json.dump(bundle, fp, ensure_ascii=False, indent=2)
    _print_payload(
        bundle, as_json=args.json, render_text=render_integration_bundle_text
    )
    return 0


def cmd_plan_save(args: argparse.Namespace) -> int:
    plan = parse_automation_request(args.request)
    created: Dict[str, Any] = {"plan": plan_to_dict(plan), "created": []}
    name = args.name or plan.name_hint
    label = args.label or (
        "아침 브리핑" if plan.template == "morning-briefing" else None
    )
    tags = list(args.tag or [])
    if plan.schedule.kind != "manual":
        tags.append(plan.schedule.kind)
    if plan.watch_intent != "none":
        tags.append("watch")
    if plan.query_mode == "group":
        tags.append("group")
    tags = _dedupe_preserve_order(tags)
    if not plan.queries:
        raise ValueError(
            "저장 가능한 주제 키워드를 찾지 못했습니다. 요청에 관심 주제를 포함해 주세요."
        )

    if args.as_type == "watch" and plan.query_mode == "group":
        raise ValueError(
            "여러 주제를 포함한 그룹형 브리핑 요청입니다. --as group 으로 저장해 주세요."
        )

    if args.as_type == "group" or plan.query_mode == "group":
        group = create_group(
            name=name,
            queries=plan.queries,
            label=label,
            tags=tags,
            context=plan.raw_request,
            template=plan.template,
            schedule=plan_to_dict(plan)["schedule"],
            operator_hints=plan_to_dict(plan)["operator_hints"],
        )
        created["created"].append({"type": "group", "value": group})
    else:
        intent = build_intent(plan.primary_query or plan.queries[0])
        rule = add_rule(
            name=name,
            raw_query=intent.raw_query,
            search_query=intent.search_query,
            db_keyword=intent.db_keyword,
            exclude_words=intent.exclude_words,
            fetch_key=intent.fetch_key,
            days=intent.days,
            limit=intent.limit,
            label=label,
            tags=tags,
            context=plan.raw_request,
            template=plan.template,
            schedule=plan_to_dict(plan)["schedule"],
            operator_hints=plan_to_dict(plan)["operator_hints"],
        )
        created["created"].append({"type": "watch", "value": rule})

    _print_payload(
        created,
        as_json=args.json,
        render_text=lambda payload: (
            render_plan_text(plan)
            + "\n- 저장 결과:\n"
            + "\n".join(
                f"  - {item['type']}: {item['value']['name']}"
                for item in payload["created"]
            )
        ),
    )
    return 0


__all__ = ["cmd_integration_plan", "cmd_plan", "cmd_plan_save"]
