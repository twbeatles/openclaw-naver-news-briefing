from __future__ import annotations

import argparse
import getpass
import json
from typing import Any, Dict

from nb_stores.config_store import get_runtime_credentials, set_credentials

from nb_cli.rendering import (
    DEFAULT_TEST_QUERY,
    _render_check_credentials_text,
    _render_setup_success,
)
from nb_cli.services import _perform_live_check


def _prompt_required(prompt: str, *, secret: bool = False) -> str:
    while True:
        value = (getpass.getpass(prompt) if secret else input(prompt)).strip()
        if value:
            return value
        print("값이 비어 있습니다. 다시 입력해 주세요.")


def _validate_credential_value(name: str, value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{name} 값이 비어 있습니다.")
    if any(ch.isspace() for ch in cleaned):
        raise ValueError(f"{name} 값에 공백이 포함되어 있습니다. 복사 과정에서 줄바꿈/공백이 들어갔는지 확인해 주세요.")
    if len(cleaned) < 5:
        raise ValueError(f"{name} 값이 너무 짧습니다. NAVER API HUB에서 발급받은 값을 다시 확인해 주세요.")
    return cleaned


def cmd_setup(args: argparse.Namespace) -> int:
    client_id = (args.client_id or "").strip()
    client_secret = (args.client_secret or "").strip()
    if not client_id:
        print("client_id가 없어 대화형 입력으로 전환합니다.")
        client_id = _prompt_required("네이버 client_id: ")
    if not client_secret:
        print("client_secret이 없어 대화형 입력으로 전환합니다.")
        client_secret = _prompt_required("네이버 client_secret: ", secret=True)

    client_id = _validate_credential_value("client_id", client_id)
    client_secret = _validate_credential_value("client_secret", client_secret)
    set_credentials(client_id, client_secret, args.timeout)

    live_checked = False
    live_query = args.test_search or (DEFAULT_TEST_QUERY if args.live_check else None)
    if live_query:
        result = _perform_live_check(live_query, limit=1)
        live_checked = True
        if args.json:
            print(json.dumps({
                "saved": True,
                "timeout": args.timeout,
                "live_check": {
                    "query": live_query,
                    "ok": True,
                    "displayed": result.get("displayed", 0),
                    "total": result.get("total", 0),
                },
            }, ensure_ascii=False, indent=2))
            return 0

    print(_render_setup_success(args.timeout, live_checked=live_checked, live_query=live_query))
    return 0


def cmd_check_credentials(args: argparse.Namespace) -> int:
    client_id, client_secret, timeout, _ = get_runtime_credentials()
    ok = bool(client_id and client_secret)
    payload: Dict[str, Any] = {"configured": ok, "client_id_present": bool(client_id), "client_secret_present": bool(client_secret), "timeout": timeout}
    if ok and args.live_check:
        query = args.query or DEFAULT_TEST_QUERY
        try:
            result = _perform_live_check(query, limit=1)
            payload["live_check"] = {
                "query": query,
                "ok": True,
                "displayed": result.get("displayed", 0),
                "total": result.get("total", 0),
            }
        except Exception as exc:
            payload["live_check"] = {"query": query, "ok": False, "error": str(exc)}
            ok = False
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else _render_check_credentials_text(payload))
    return 0 if ok else 1


__all__ = ["cmd_check_credentials", "cmd_setup"]
