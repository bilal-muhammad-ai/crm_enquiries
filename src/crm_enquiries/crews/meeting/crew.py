"""Meeting analysis crew — transcript to CRM updates."""

import logging

from crm_enquiries.crews import compat  # noqa: F401
from crewai import Crew, Process
from crewai.project import CrewBase, agent, crew, task

from crm_enquiries.crews.meeting.agents import (
    create_crm_updater_agent,
    create_followup_planner_agent,
    create_transcript_parser_agent,
)
from crm_enquiries.crews.meeting.tasks import (
    map_crm_updates_task,
    parse_meeting_analysis,
    parse_transcript_task,
    plan_followup_task,
    rule_based_meeting_analysis,
)
from crm_enquiries.schemas.meeting import MeetingAnalysis

logger = logging.getLogger(__name__)


@CrewBase
class MeetingAnalysisCrew:
    """Analyze Fathom meeting transcripts and plan CRM updates."""

    @agent
    def transcript_parser(self):
        return create_transcript_parser_agent()

    @agent
    def crm_updater(self):
        return create_crm_updater_agent()

    @agent
    def followup_planner(self):
        return create_followup_planner_agent()

    @task
    def parse_task(self):
        return parse_transcript_task(self.transcript_parser())

    @task
    def crm_task(self):
        return map_crm_updates_task(self.crm_updater(), context=[self.parse_task()])

    @task
    def followup_task(self):
        return plan_followup_task(self.followup_planner(), context=[self.parse_task(), self.crm_task()])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.transcript_parser(), self.crm_updater(), self.followup_planner()],
            tasks=[self.parse_task(), self.crm_task(), self.followup_task()],
            process=Process.sequential,
            verbose=True,
        )


async def run_meeting_analysis(inputs: dict, use_llm: bool = True) -> MeetingAnalysis:
    summary = inputs.get("summary", "")
    transcript = inputs.get("transcript", "")

    if not use_llm:
        return rule_based_meeting_analysis(summary, transcript)

    try:
        result = await MeetingAnalysisCrew().crew().kickoff_async(inputs=inputs)
        raw = str(result.raw if hasattr(result, "raw") else result)
        return parse_meeting_analysis(raw, summary, transcript)
    except Exception as exc:
        logger.warning("MeetingAnalysisCrew failed, using rule-based analysis: %s", exc)
        return rule_based_meeting_analysis(summary, transcript)
