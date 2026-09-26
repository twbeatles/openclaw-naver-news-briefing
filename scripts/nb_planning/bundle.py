from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from nb_planning.service import parse_automation_request, plan_to_dict


def _default_skill_dir() -> Path:
    # scripts/nb_planning/bundle.py -> parents[2] == 스킬 루트
    return Path(__file__).resolve().parents[2]


def build_integration_bundle(raw: str, *, skill_dir: str | Path | None = None, assistant_channel: str = "telegram") -> Dict[str, Any]:
    plan = parse_automation_request(raw)
    skill_root = Path(skill_dir).resolve() if skill_dir else _default_skill_dir()
    cli_rel = str(skill_root / "scripts" / "naver_news_briefing.py")
    save_as = "group" if plan.query_mode == "group" else "watch"
    save_command = f'python scripts/naver_news_briefing.py plan-save "{plan.raw_request}" --as {save_as} --name {plan.name_hint}'
    run_command = plan.operator_hints.recommended_command
    shell_run = f'cd "{skill_root}" && {run_command}'
    shell_save = f'cd "{skill_root}" && {save_command}'
    schedule_payload = {
        "kind": plan.schedule.kind,
        "label": plan.schedule.label,
        "cron": plan.schedule.cron,
        "time": plan.schedule.time,
        "interval_minutes": plan.schedule.interval_minutes,
        "days_of_week": plan.schedule.days_of_week,
    }
    confirmation = f"'{plan.raw_request}' 요청을 {plan.schedule.label} {plan.operator_hints.storage_target} 자동화로 해석했습니다. 저장 이름은 '{plan.name_hint}'를 추천하고, 저장 뒤에는 '{run_command}'를 스케줄러에 연결하면 됩니다."
    cadence_phrase = plan.schedule.label if plan.schedule.label.endswith("마다") else f"{plan.schedule.label}마다"
    system_event_text = (
        f"{cadence_phrase} {assistant_channel} 채널에 네이버 뉴스 자동화를 실행하세요. "
        f"먼저 {save_command} 로 상태를 저장하고, 이후 {run_command} 결과를 전달합니다."
        if plan.schedule.kind != "manual"
        else f"필요할 때 {run_command} 를 수동 실행하는 네이버 뉴스 브리핑 요청입니다."
    )
    openclaw_prompt = (
        "다음 뉴스 자동화 계획을 기준으로 cron/작업을 생성하세요.\n"
        f"- 사용자 요청: {plan.raw_request}\n"
        f"- 저장 명령: {save_command}\n"
        f"- 실행 명령: {run_command}\n"
        f"- 일정: {json.dumps(schedule_payload, ensure_ascii=False)}\n"
        f"- 전달 포맷: {plan.operator_hints.delivery_format}\n"
        f"- 확인 문구: {confirmation}"
    )
    bundle = {
        "plan": plan_to_dict(plan),
        "storage": {
            "target": save_as,
            "name": plan.name_hint,
            "save_command": save_command,
            "shell_save_command": shell_save,
        },
        "runner": {
            "command": run_command,
            "shell_command": shell_run,
            "delivery_format": plan.operator_hints.delivery_format,
            "assistant_channel": assistant_channel,
        },
        "automation": {
            "schedule": schedule_payload,
            "cron_line": f"{plan.schedule.cron} {shell_run}" if plan.schedule.cron else None,
            "system_event_text": system_event_text,
            "openclaw_prompt": openclaw_prompt,
        },
        "assistant_summary": {
            "confirmation": confirmation,
            "user_summary": confirmation,
            "next_step": "저장 명령을 한 번 실행한 뒤 cron/OpenClaw 작업에서 실행 명령을 연결하세요.",
        },
        "artifacts": {
            "skill_dir": str(skill_root),
            "cli_path": cli_rel,
        },
    }
    return bundle


def render_integration_bundle_text(bundle: Dict[str, Any]) -> str:
    plan = bundle["plan"]
    storage = bundle["storage"]
    runner = bundle["runner"]
    automation = bundle["automation"]
    assistant_summary = bundle["assistant_summary"]
    lines = [
        "## OpenClaw 연동 번들",
        f"- 요청: {plan['raw_request']}",
        f"- 저장 대상: {storage['target']} ({storage['name']})",
        f"- 일정: {automation['schedule']['label']}",
        f"- 저장 명령: {storage['save_command']}",
        f"- 실행 명령: {runner['command']}",
    ]
    if automation.get("cron_line"):
        lines.append(f"- cron 한 줄 예시: {automation['cron_line']}")
    lines.append("- OpenClaw systemEvent 제안:")
    lines.append(f"  {automation['system_event_text']}")
    lines.append("- OpenClaw 작업 생성용 프롬프트:")
    for line in str(automation["openclaw_prompt"]).splitlines():
        lines.append(f"  {line}")
    lines.append("- 사용자 확인 문구:")
    lines.append(f"  {assistant_summary['confirmation']}")
    return "\n".join(lines)


__all__ = ["build_integration_bundle", "render_integration_bundle_text"]
