"""Meeting analysis crew tasks."""

import json

from crewai import Agent, Task

from crm_enquiries.schemas.meeting import ActionItem, MeetingAnalysis


def parse_transcript_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Analyze this meeting transcript and summary.\n\n"
            "Summary: {summary}\n\n"
            "Transcript:\n{transcript}\n\n"
            "Return ONLY valid JSON with keys: meeting_summary, client_requirements (list), "
            "design_preferences (list), action_items (list of {{description, owner, due_hint}})."
        ),
        expected_output="Valid JSON with parsed meeting insights.",
        agent=agent,
    )


def map_crm_updates_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Map meeting insights to CRM updates. Return ONLY valid JSON: "
            '{{"crm_status": "Brief Taken", "crm_notes": "detailed notes"}}'
        ),
        expected_output="Valid JSON with crm_status and crm_notes.",
        agent=agent,
        context=context,
    )


def plan_followup_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Recommend follow-up actions. Return ONLY valid JSON: "
            '{{"suggested_follow_up_email": "draft email text or null"}}'
        ),
        expected_output="Valid JSON with suggested_follow_up_email.",
        agent=agent,
        context=context,
    )


def rule_based_meeting_analysis(summary: str, transcript: str) -> MeetingAnalysis:
    text = f"{summary}\n{transcript}".lower()
    requirements = []
    if "superyacht" in text or "yacht" in text:
        requirements.append("Superyacht outfitting")
    if "tableware" in text:
        requirements.append("Luxury tableware")
    if "nda" in text:
        requirements.append("NDA required before sharing designs")

    action_items = []
    if "nda" in text:
        action_items.append(ActionItem(description="Send NDA for signature"))
    if "showroom" in text or "visit" in text:
        action_items.append(ActionItem(description="Schedule showroom visit"))
    if "presentation" in text:
        action_items.append(ActionItem(description="Prepare tailored product presentation"))

    return MeetingAnalysis(
        meeting_summary=summary or "Meeting completed with client.",
        client_requirements=requirements or ["General luxury outfitting enquiry"],
        design_preferences=["To be confirmed from design renders"],
        action_items=action_items or [ActionItem(description="Follow up with client")],
        crm_status="Brief Taken",
        crm_notes=f"Meeting summary: {summary[:500] if summary else transcript[:500]}",
        suggested_follow_up_email=None,
    )


def parse_meeting_analysis(raw: str, summary: str, transcript: str) -> MeetingAnalysis:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            action_items = [
                ActionItem(**item) if isinstance(item, dict) else ActionItem(description=str(item))
                for item in data.get("action_items", [])
            ]
            return MeetingAnalysis(
                meeting_summary=data.get("meeting_summary", summary),
                client_requirements=data.get("client_requirements", []),
                design_preferences=data.get("design_preferences", []),
                action_items=action_items,
                crm_status=data.get("crm_status", "Brief Taken"),
                crm_notes=data.get("crm_notes", summary),
                suggested_follow_up_email=data.get("suggested_follow_up_email"),
            )
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return rule_based_meeting_analysis(summary, transcript)
