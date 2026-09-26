from __future__ import annotations

import argparse
import json

from nb_stores.group_store import (
    create_group,
    get_group,
    list_groups,
    remove_group,
    update_group,
)

from nb_cli.rendering import _format_group_text, _print_payload


def cmd_group_add(args: argparse.Namespace) -> int:
    group = create_group(name=args.name, queries=args.query, label=args.label, tags=args.tag, context=args.context, template=args.template)
    _print_payload(group, as_json=args.json, render_text=_format_group_text)
    return 0


def cmd_group_list(args: argparse.Namespace) -> int:
    groups = [get_group(args.name_or_id)] if args.name_or_id else list_groups()
    if args.json:
        print(json.dumps(groups if not args.name_or_id else groups[0], ensure_ascii=False, indent=2))
        return 0
    if not groups:
        print("등록된 키워드 그룹이 없습니다.")
        return 0
    print("\n\n".join(_format_group_text(group) for group in groups))
    return 0


def cmd_group_remove(args: argparse.Namespace) -> int:
    deleted = remove_group(args.name_or_id)
    if deleted:
        print(f"삭제 완료: {args.name_or_id}")
        return 0
    print(f"삭제 대상 없음: {args.name_or_id}")
    return 1


def cmd_group_update(args: argparse.Namespace) -> int:
    tags = None
    if args.tag is not None or args.clear_tags:
        tags = [] if args.clear_tags else args.tag
    group = update_group(args.name_or_id, label=args.label, context=args.context, tags=tags, template=args.template, replace_queries=args.set_query, add_queries=args.add_query, remove_queries=args.remove_query)
    _print_payload(group, as_json=args.json, render_text=_format_group_text)
    return 0


__all__ = ["cmd_group_add", "cmd_group_list", "cmd_group_remove", "cmd_group_update"]
