from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from src.ats.types import CandidateScore


@CrewBase
class ResumeScoreCrew:
    """Resume Score Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def resume_score_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_score_agent"],
            #verbose=True,
        )

    @task
    def resume_score_task(self) -> Task:
        return Task(
            config=self.tasks_config["resume_score_task"],
            output_pydantic=CandidateScore,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Resume Score Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            #verbose=True,
        )
