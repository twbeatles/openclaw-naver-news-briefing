from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from nb_query import build_intent

from nb_planning.detect import (
    GROUP_HINTS,
    detect_action,
    detect_briefing_focus,
    detect_schedule,
    detect_template,
    detect_watch_intent,
    extract_queries,
    normalize_request,
    suggest_name,
)
from nb_planning.models import AutomationPlan, OperatorHints


def build_commands(plan: AutomationPlan) -> List[str]:
    commands: List[str] = []
    if plan.query_mode == "group":
        quoted_queries = " ".join(f'"{query}"' for query in plan.queries)
        commands.append(
            f'python scripts/naver_news_briefing.py group-add {plan.name_hint} {quoted_queries} --label "자동 생성 그룹" --context "{plan.raw_request}" --template {plan.template}'
        )
        commands.append(
            f"python scripts/naver_news_briefing.py brief-multi --group {plan.name_hint} --template {plan.template}"
        )
        commands.append(
            f'python scripts/naver_news_briefing.py plan-save "{plan.raw_request}" --as group --name {plan.name_hint}'
        )
    else:
        query = plan.primary_query or ""
        if "monitor" in plan.action:
            commands.append(
                f'python scripts/naver_news_briefing.py watch-add {plan.name_hint} "{query}" --template {plan.template}'
            )
            commands.append(
                f"python scripts/naver_news_briefing.py watch-check {plan.name_hint} --json"
            )
        if "briefing" in plan.action:
            commands.append(f'python scripts/naver_news_briefing.py search "{query}"')
        commands.append(
            f'python scripts/naver_news_briefing.py plan-save "{plan.raw_request}" --as watch --name {plan.name_hint}'
        )
    return commands


def build_operator_hints(plan: AutomationPlan) -> OperatorHints:
    storage_target = "group" if plan.query_mode == "group" else "watch"
    recommended_runner = "cron" if plan.schedule.kind != "manual" else "manual"
    if storage_target == "group":
        recommended_command = f"python scripts/naver_news_briefing.py brief-multi --group {plan.name_hint} --template {plan.template}"
        delivery_format = "chat-briefing"
    else:
        recommended_command = (
            f"python scripts/naver_news_briefing.py watch-check {plan.name_hint} --json"
            if "monitor" in plan.action
            else f'python scripts/naver_news_briefing.py search "{plan.primary_query or ""}"'
        )
        delivery_format = "watch-json" if "monitor" in plan.action else "chat-briefing"
    notes = [
        "스케줄 실행은 이 스킬이 아니라 외부 cron/작업 스케줄러/OpenClaw cron에서 연결하는 방식이 가장 안정적입니다.",
        "watch는 새 기사 감지용, group은 반복 브리핑용으로 두면 운영이 단순합니다.",
    ]
    cron_examples: List[str] = []
    if plan.schedule.cron:
        cron_examples.append(f"{plan.schedule.cron} {recommended_command}")
        cron_examples.append(
            f"{plan.schedule.cron} # 위 명령 실행 후 stdout/json을 텔레그램·디스코드 전송"
        )
    return OperatorHints(
        recommended_runner=recommended_runner,
        recommended_command=recommended_command,
        delivery_format=delivery_format,
        storage_target=storage_target,
        cadence_summary=plan.schedule.label,
        cron_examples=cron_examples,
        notes=notes,
    )


def parse_automation_request(raw: str) -> AutomationPlan:
    request = normalize_request(raw)
    action = detect_action(request)
    schedule = detect_schedule(request)
    queries = extract_queries(request)
    query_mode = (
        "group"
        if len(queries) > 1 or any(hint in request for hint in GROUP_HINTS)
        else "single"
    )
    primary_query = queries[0] if queries else None
    intent = None
    rationale: List[str] = []
    if primary_query:
        built = build_intent(primary_query)
        intent = asdict(built)
        rationale.append(f"핵심 검색어를 '{built.search_query}'로 정규화했습니다.")
        if built.exclude_words:
            rationale.append(
                "제외어를 유지해 watch/search 명령으로 바로 연결할 수 있게 했습니다."
            )
    else:
        rationale.append(
            "주제 키워드가 없어 저장 가능한 watch/search 명령은 만들지 않았습니다."
        )
    if schedule.kind != "manual":
        rationale.append(f"일정 표현을 '{schedule.label}' 구조로 해석했습니다.")
    group_reason = None
    if query_mode == "group":
        group_reason = "여러 주제를 한 번에 반복 브리핑하기 좋은 요청입니다."
        rationale.append("여러 주제를 감지해 그룹 기반 브리핑/자동화로 분류했습니다.")

    template = detect_template(request, action, schedule)
    plan = AutomationPlan(
        raw_request=request,
        action=action,
        query_mode=query_mode,
        queries=queries,
        primary_query=primary_query,
        intent=intent,
        schedule=schedule,
        name_hint=suggest_name(queries, action),
        template=template,
        briefing_focus=detect_briefing_focus(request, template),
        watch_intent=detect_watch_intent(request, action),
        group_reason=group_reason,
        rationale=rationale,
        suggested_commands=[],
        operator_hints=OperatorHints(
            recommended_runner="manual",
            recommended_command="",
            delivery_format="text",
            storage_target="watch" if query_mode == "single" else "group",
            cadence_summary=schedule.label,
        ),
    )
    commands = build_commands(plan)
    hints = build_operator_hints(plan)
    return AutomationPlan(
        **{
            **asdict(plan),
            "suggested_commands": commands,
            "operator_hints": hints,
            "schedule": plan.schedule,
        }
    )


def render_plan_text(plan: AutomationPlan) -> str:
    lines = [
        "## 뉴스 자동화 계획",
        f"- 요청: {plan.raw_request}",
        f"- 작업 유형: {plan.action}",
        f"- 일정: {plan.schedule.label}",
    ]
    if plan.queries:
        lines.append("- 해석된 질의: " + ", ".join(plan.queries))
    lines.append(f"- 저장 대상 추천: {plan.operator_hints.storage_target}")
    if plan.name_hint:
        lines.append(f"- 저장 이름 제안: {plan.name_hint}")
    lines.append(f"- 추천 템플릿: {plan.template} ({plan.briefing_focus})")
    lines.append(f"- watch 의도: {plan.watch_intent}")
    if plan.schedule.cron:
        lines.append(f"- cron 힌트: {plan.schedule.cron}")
    if plan.group_reason:
        lines.append(f"- 그룹 판단: {plan.group_reason}")
    if plan.rationale:
        lines.append("- 해석 근거:")
        lines.extend(f"  - {item}" for item in plan.rationale)
    lines.append("- 운영 힌트:")
    lines.append(f"  - 실행 방식: {plan.operator_hints.recommended_runner}")
    lines.append(f"  - 추천 실행 명령: {plan.operator_hints.recommended_command}")
    for note in plan.operator_hints.notes:
        lines.append(f"  - {note}")
    if plan.operator_hints.cron_examples:
        lines.append("- cron 예시:")
        lines.extend(f"  - {item}" for item in plan.operator_hints.cron_examples)
    if plan.suggested_commands:
        lines.append("- 추천 명령:")
        lines.extend(f"  - {cmd}" for cmd in plan.suggested_commands)
    return "\n".join(lines)


def plan_to_dict(plan: AutomationPlan) -> Dict[str, Any]:
    payload = asdict(plan)
    payload["schedule"] = asdict(plan.schedule)
    payload["operator_hints"] = asdict(plan.operator_hints)
    return payload


__all__ = [
    "build_commands",
    "build_operator_hints",
    "parse_automation_request",
    "plan_to_dict",
    "render_plan_text",
]
