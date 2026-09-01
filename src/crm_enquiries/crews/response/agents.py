"""Response crew agents."""

from crewai import Agent

from crm_enquiries.config import get_settings


def _llm() -> str:
    return get_settings().llm_model


def create_knowledge_retriever_agent() -> Agent:
    return Agent(
        role="Knowledge Retriever",
        goal="Find relevant Glancy Fawcett FAQ content to answer the client's enquiry accurately.",
        backstory=(
            "You are an expert on Glancy Fawcett services, showrooms, payment terms, "
            "NDA policy, and the Designed by GF bespoke product design service."
        ),
        verbose=True,
        llm=_llm(),
    )


def create_email_composer_agent() -> Agent:
    return Agent(
        role="Email Composer",
        goal=(
            "Draft warm, professional email responses in Glancy Fawcett's Client Relationship "
            "Manager voice, addressing the client's specific enquiry."
        ),
        backstory=(
            "You write elegant, concise emails for a luxury outfitter serving superyachts, "
            "residences, and private aircraft clients worldwide."
        ),
        verbose=True,
        llm=_llm(),
    )


def create_compliance_validator_agent() -> Agent:
    return Agent(
        role="Compliance Validator",
        goal=(
            "Verify every factual claim in the email draft is supported by the provided FAQ "
            "context. Flag unsupported statements."
        ),
        backstory="You are a QA reviewer ensuring all client-facing content is factually accurate.",
        verbose=True,
        llm=_llm(),
    )
