"""Analysis crew agents."""

from crewai import Agent

from crm_enquiries.config import get_settings


def _llm() -> str:
    return get_settings().llm_model


def create_classifier_agent() -> Agent:
    return Agent(
        role="Enquiry Classifier",
        goal=(
            "Classify enquiry urgency and intent while preserving the form-submitted enquiry_type. "
            "Detect tags like nda, showroom_visit, bespoke_design, short_lead_time."
        ),
        backstory=(
            "You are a senior Client Relationship Manager at Glancy Fawcett with deep knowledge "
            "of superyacht, residential, and private aircraft outfitting enquiries."
        ),
        verbose=True,
        llm=_llm(),
    )


def create_crm_mapper_agent() -> Agent:
    return Agent(
        role="CRM Field Mapper",
        goal="Structure classification results into CRM-ready JSON field updates.",
        backstory="You translate enquiry analysis into precise SuiteCRM field mappings.",
        verbose=True,
        llm=_llm(),
    )


def create_summarizer_agent() -> Agent:
    return Agent(
        role="Enquiry Summarizer",
        goal="Write a concise 2-3 sentence internal summary for the CRM enquiry record.",
        backstory="You distill client messages into actionable internal notes for the GF team.",
        verbose=True,
        llm=_llm(),
    )
