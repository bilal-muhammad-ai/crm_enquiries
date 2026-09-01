"""Response crew tasks and parsers."""

import json
import re

from crewai import Agent, Task

from crm_enquiries.schemas.email_draft import EmailDraft


def retrieve_knowledge_task(agent: Agent) -> Task:
    return Task(
        description=(
            "Review the FAQ context provided and identify the most relevant sections for this enquiry.\n\n"
            "Enquiry type: {enquiry_type}\n"
            "Client message: {message}\n"
            "Analysis summary: {internal_summary}\n"
            "Intent tags: {intent_tags}\n\n"
            "FAQ Context:\n{faq_context}\n\n"
            "List the key FAQ points to address and cite source sections."
        ),
        expected_output="Bullet list of relevant FAQ points with source citations.",
        agent=agent,
    )


def compose_email_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Draft a personalized email reply to {name} ({email}) for their {enquiry_type} enquiry.\n\n"
            "Client message: {message}\n\n"
            "Use ONLY facts from the FAQ context and knowledge retrieval. "
            "Suggest a brief-taking meeting if appropriate.\n\n"
            "Return ONLY valid JSON with keys: subject, body_plain, body_html, kb_citations (list), "
            "suggested_meeting (bool), meeting_context (string or null)."
        ),
        expected_output="Valid JSON email draft.",
        agent=agent,
        context=context,
    )


def validate_email_task(agent: Agent, context: list[Task]) -> Task:
    return Task(
        description=(
            "Validate the email draft against the FAQ context. "
            "Return ONLY valid JSON: {{\"validation_passed\": true/false, "
            "\"validation_issues\": [], \"subject\": \"...\", \"body_plain\": \"...\", "
            "\"body_html\": \"...\", \"kb_citations\": [], \"suggested_meeting\": bool, "
            "\"meeting_context\": null or string}}"
        ),
        expected_output="Validated JSON email draft.",
        agent=agent,
        context=context,
    )


def rule_based_draft(inputs: dict) -> EmailDraft:
    name = inputs.get("name", "Client")
    enquiry_type = inputs.get("enquiry_type", "general").replace("_", " ")
    first_name = name.split()[0] if name else "there"

    subject = f"Thank you for your {enquiry_type} enquiry — Glancy Fawcett"
    body_plain = (
        f"Dear {first_name},\n\n"
        f"Thank you for contacting Glancy Fawcett regarding your {enquiry_type} project. "
        f"We would be delighted to discuss your requirements with one of our Client Relationship Managers.\n\n"
        f"We are happy to sign NDAs and can arrange brief-taking sessions at our Manchester or Abu Dhabi "
        f"showrooms, or remotely via video call. Please call +44(0)161 876 5356 to book an appointment "
        f"(Monday–Friday, 9am–5:30pm).\n\n"
        f"Our standard payment terms are 50% on invoice, with the balance on delivery.\n\n"
        f"We look forward to supporting your project.\n\n"
        f"Warm regards,\n"
        f"Glancy Fawcett Client Team\n"
        f"sales@glancyfawcett.com"
    )
    body_html = body_plain.replace("\n", "<br>\n")
    return EmailDraft(
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
        kb_citations=["03_starting_your_project.md", "06_commercial_payment_terms.md", "07_showrooms.md"],
        suggested_meeting=True,
        meeting_context="brief-taking session with a Client Relationship Manager",
        validation_passed=True,
    )


def parse_email_draft(raw: str, inputs: dict) -> EmailDraft:
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(raw[start:end])
            return EmailDraft(
                subject=data.get("subject", "Your enquiry — Glancy Fawcett"),
                body_plain=data.get("body_plain", ""),
                body_html=data.get("body_html", data.get("body_plain", "").replace("\n", "<br>\n")),
                kb_citations=data.get("kb_citations", []),
                suggested_meeting=bool(data.get("suggested_meeting", False)),
                meeting_context=data.get("meeting_context"),
                validation_passed=bool(data.get("validation_passed", True)),
                validation_issues=data.get("validation_issues", []),
            )
    except (json.JSONDecodeError, ValueError):
        pass
    return rule_based_draft(inputs)
