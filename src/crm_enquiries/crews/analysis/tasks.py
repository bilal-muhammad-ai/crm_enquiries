"""Analysis crew tasks."""

import json

from crewai import Agent, Task

from crm_enquiries.schemas.analysis import EnquiryAnalysis
from crm_enquiries.schemas.intake import EnquiryType


def classify_enquiry_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Analyze this enquiry. Preserve the form-submitted enquiry_type '{enquiry_type}'. "
            "Do NOT change enquiry_type unless the message clearly contradicts it — if so, set "
            "type_contradiction=true and explain in type_contradiction_note.\n\n"
            "Client: {name} ({email})\n"
            "Company: {company}\n"
            "Enquiry type: {enquiry_type}\n"
            "Message: {message}\n\n"
            "Return ONLY valid JSON with keys: enquiry_type, priority (1-5), intent_tags (list), "
            "type_contradiction (bool), type_contradiction_note (string or null)."
        ),
        expected_output="Valid JSON object with classification fields.",
        agent=agent,
    )


def map_crm_fields_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Using the classification output, produce CRM field updates as JSON with keys: "
            "suggested_assignee_role, crm_field_updates (dict). "
            "For superyacht + high priority, suggest senior assignee."
        ),
        expected_output="Valid JSON with suggested_assignee_role and crm_field_updates.",
        agent=agent,
        context=context,
    )


def summarize_enquiry_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Write a 2-3 sentence internal_summary based on all prior analysis. "
            "Return ONLY valid JSON: {{\"internal_summary\": \"...\"}}"
        ),
        expected_output='Valid JSON: {"internal_summary": "..."}',
        agent=agent,
        context=context,
    )


def parse_analysis_output(raw: str, enquiry_type: str) -> EnquiryAnalysis:
    """Parse crew output into EnquiryAnalysis with rule-based fallback."""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return EnquiryAnalysis(
                enquiry_type=data.get("enquiry_type", enquiry_type),
                priority=int(data.get("priority", 3)),
                intent_tags=data.get("intent_tags", []),
                suggested_assignee_role=data.get("suggested_assignee_role", "Client Relationship Manager"),
                internal_summary=data.get("internal_summary", "Enquiry received and awaiting review."),
                type_contradiction=bool(data.get("type_contradiction", False)),
                type_contradiction_note=data.get("type_contradiction_note"),
                crm_field_updates=data.get("crm_field_updates", {}),
            )
    except (json.JSONDecodeError, ValueError):
        pass
    return rule_based_analysis(enquiry_type, "")


def rule_based_analysis(enquiry_type: str, message: str) -> EnquiryAnalysis:
    message_lower = message.lower()
    tags = []
    priority = 3
    if "nda" in message_lower:
        tags.append("nda")
    if any(w in message_lower for w in ("showroom", "visit", "manchester", "abu dhabi")):
        tags.append("showroom_visit")
    if any(w in message_lower for w in ("bespoke", "custom", "designed by gf", "motif")):
        tags.append("bespoke_design")
    if any(w in message_lower for w in ("urgent", "asap", "short lead", "deadline")):
        tags.append("short_lead_time")
        priority = 4
    if enquiry_type == "superyacht":
        priority = max(priority, 4)
    try:
        et = EnquiryType(enquiry_type)
    except ValueError:
        et = EnquiryType.GENERAL
    return EnquiryAnalysis(
        enquiry_type=et,
        priority=priority,
        intent_tags=tags,
        suggested_assignee_role=(
            "Senior Client Relationship Manager" if priority >= 4 else "Client Relationship Manager"
        ),
        internal_summary=f"{et.value.replace('_', ' ').title()} enquiry received. Intent tags: {', '.join(tags) or 'general'}.",
        crm_field_updates={},
    )
