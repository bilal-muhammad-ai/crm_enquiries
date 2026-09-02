"""Analysis crew — classify and enrich enquiries."""

import logging

from crm_enquiries.crews import compat  # noqa: F401
from crewai import Crew, Process
from crewai.project import CrewBase, agent, crew, task

from crm_enquiries.crews.analysis.agents import (
    create_classifier_agent,
    create_crm_mapper_agent,
    create_summarizer_agent,
)
from crm_enquiries.crews.analysis.tasks import (
    classify_enquiry_task,
    map_crm_fields_task,
    parse_analysis_output,
    rule_based_analysis,
    summarize_enquiry_task,
)
from crm_enquiries.schemas.analysis import EnquiryAnalysis

logger = logging.getLogger(__name__)


@CrewBase
class AnalysisCrew:
    """Classify urgency, map CRM fields, and summarize enquiries."""

    @agent
    def classifier(self):
        return create_classifier_agent()

    @agent
    def crm_mapper(self):
        return create_crm_mapper_agent()

    @agent
    def summarizer(self):
        return create_summarizer_agent()

    @task
    def classify_task(self):
        return classify_enquiry_task(self.classifier())

    @task
    def map_crm_task(self):
        return map_crm_fields_task(self.crm_mapper(), context=[self.classify_task()])

    @task
    def summarize_task(self):
        return summarize_enquiry_task(self.summarizer(), context=[self.classify_task(), self.map_crm_task()])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.classifier(), self.crm_mapper(), self.summarizer()],
            tasks=[self.classify_task(), self.map_crm_task(), self.summarize_task()],
            process=Process.sequential,
            verbose=True,
        )


async def run_analysis(inputs: dict, use_llm: bool = True) -> EnquiryAnalysis:
    enquiry_type = inputs.get("enquiry_type", "general")
    message = inputs.get("message", "")

    if not use_llm:
        return rule_based_analysis(enquiry_type, message)

    try:
        result = await AnalysisCrew().crew().kickoff_async(inputs=inputs)
        raw = str(result.raw if hasattr(result, "raw") else result)
        return parse_analysis_output(raw, enquiry_type)
    except Exception as exc:
        logger.warning("AnalysisCrew failed, using rule-based analysis: %s", exc)
        return rule_based_analysis(enquiry_type, message)
