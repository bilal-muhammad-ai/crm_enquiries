"""Meeting analysis crew agents."""

from crewai import Agent

from crm_enquiries.config import get_settings


def _llm() -> str:
    return get_settings().llm_model


def create_transcript_parser_agent() -> Agent:
    return Agent(
        role="Transcript Parser",
        goal="Extract key topics, client preferences, design requirements, budget signals, and timeline from meeting transcripts.",
        backstory="You analyze luxury outfitting brief calls for Glancy Fawcett.",
        verbose=True,
        llm=_llm(),
    )


def create_crm_updater_agent() -> Agent:
    return Agent(
        role="CRM Updater",
        goal="Map meeting insights to SuiteCRM enquiry status and notes fields.",
        backstory="You maintain accurate CRM records for the GF sales team.",
        verbose=True,
        llm=_llm(),
    )


def create_followup_planner_agent() -> Agent:
    return Agent(
        role="Follow-up Planner",
        goal="Recommend next steps such as sending presentations, scheduling showroom visits, or NDAs.",
        backstory="You plan client relationship follow-ups for luxury project enquiries.",
        verbose=True,
        llm=_llm(),
    )
