"""Crew output validation tests."""

from crm_enquiries.crews.analysis.crew import run_analysis
from crm_enquiries.crews.analysis.tasks import parse_analysis_output, rule_based_analysis
from crm_enquiries.crews.meeting.crew import run_meeting_analysis
from crm_enquiries.crews.response.crew import run_response_crew
from crm_enquiries.schemas.analysis import EnquiryAnalysis
from crm_enquiries.schemas.email_draft import EmailDraft
from crm_enquiries.schemas.meeting import MeetingAnalysis
from crm_enquiries.services.knowledge_base import KnowledgeBaseService


def test_rule_based_analysis_detects_tags():
    result = rule_based_analysis("superyacht", "We need an NDA and showroom visit in Manchester ASAP")
    assert isinstance(result, EnquiryAnalysis)
    assert result.priority >= 4
    assert "nda" in result.intent_tags
    assert "showroom_visit" in result.intent_tags


def test_parse_analysis_output_json():
    raw = '{"enquiry_type": "general", "priority": 2, "intent_tags": ["general"], "internal_summary": "Test"}'
    result = parse_analysis_output(raw, "general")
    assert result.priority == 2
    assert result.internal_summary == "Test"


def test_run_analysis_without_llm():
    result = run_analysis(
        {
            "name": "Test User",
            "email": "test@example.com",
            "company": "Test Co",
            "enquiry_type": "residential",
            "message": "Looking for bespoke linens",
        },
        use_llm=False,
    )
    assert result.enquiry_type.value == "residential"


def test_run_response_crew_without_llm():
    draft = run_response_crew(
        {
            "name": "Test User",
            "email": "test@example.com",
            "enquiry_type": "general",
            "message": "General enquiry about services",
            "internal_summary": "General enquiry",
            "intent_tags": [],
        },
        use_llm=False,
    )
    assert isinstance(draft, EmailDraft)
    assert draft.validation_passed
    assert "Glancy Fawcett" in draft.body_plain


def test_run_meeting_analysis_without_llm():
    analysis = run_meeting_analysis(
        {
            "summary": "Client needs superyacht tableware. NDA discussed.",
            "transcript": "Client: We need tableware. GF: We can send NDA.",
        },
        use_llm=False,
    )
    assert isinstance(analysis, MeetingAnalysis)
    assert analysis.crm_status == "Brief Taken"
    assert len(analysis.action_items) >= 1


def test_knowledge_base_file_fallback():
    kb = KnowledgeBaseService()
    results = kb.query("showroom Manchester appointment", top_k=3)
    assert len(results) > 0
    assert "content" in results[0]
