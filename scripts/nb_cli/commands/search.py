from __future__ import annotations

import argparse
import json

from nb_cli.rendering import _brief_lines
from nb_cli.services import run_search


def cmd_search(args: argparse.Namespace) -> int:
    result = run_search(
        args.query,
        limit=args.limit,
        days=args.days,
        sort=getattr(args, "sort", "date") or "date",
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n".join(_brief_lines(result)))
    return 0


__all__ = ["cmd_search"]
