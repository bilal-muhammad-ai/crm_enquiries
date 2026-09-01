"""Response crew — KB-grounded email drafting."""

from crewai import Crew, Process
from crewai.project import CrewBase, agent, crew, task

from crm_enquiries.crews.response.agents import (
    create_compliance_validator_agent,
    create_email_composer_agent,
    create_knowledge_retriever_agent,
)
from crm_enquiries.crews.response.tasks import (
    compose_email_task,
    parse_email_draft,
    retrieve_knowledge_task,
    rule_based_draft,
    validate_email_task,
)
from crm_enquiries.schemas.email_draft import EmailDraft
from crm_enquiries.services.knowledge_base import KnowledgeBaseService


@CrewBase
class ResponseCrew:
    """Generate KB-grounded email drafts with compliance validation."""

    @agent
    def knowledge_retriever(self):
        return create_knowledge_retriever_agent()

    @agent
    def email_composer(self):
        return create_email_composer_agent()

    @agent
    def compliance_validator(self):
        return create_compliance_validator_agent()

    @task
    def retrieve_task(self):
        return retrieve_knowledge_task(self.knowledge_retriever())

    @task
    def compose_task(self):
        return compose_email_task(self.email_composer(), context=[self.retrieve_task()])

    @task
    def validate_task(self):
        return validate_email_task(self.compliance_validator(), context=[self.compose_task()])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.knowledge_retriever(), self.email_composer(), self.compliance_validator()],
            tasks=[self.retrieve_task(), self.compose_task(), self.validate_task()],
            process=Process.sequential,
            verbose=True,
        )


def run_response_crew(inputs: dict, use_llm: bool = True) -> EmailDraft:
    kb = KnowledgeBaseService()
    inputs = {
        **inputs,
        "faq_context": kb.get_context_for_enquiry(
            inputs.get("message", ""),
            inputs.get("enquiry_type", "general"),
        ),
        "intent_tags": ", ".join(inputs.get("intent_tags", [])),
    }

    if not use_llm:
        return rule_based_draft(inputs)

    try:
        result = ResponseCrew().crew().kickoff(inputs=inputs)
        raw = str(result.raw if hasattr(result, "raw") else result)
        return parse_email_draft(raw, inputs)
    except Exception:
        return rule_based_draft(inputs)
