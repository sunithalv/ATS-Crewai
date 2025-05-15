from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from src.ats.crews.rewrite_resume_crew.tools.rewrite_resume_tool import RewriteResumeTool
from src.ats.types import Resume_Final


@CrewBase
class RewriteResumeCrew:
    """Rewrite Resume Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    

    @agent
    def rewrite_resume_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["rewrite_resume_agent"],
            verbose=True,
        )

    @task
    def rewrite_resume_task(self) -> Task:
        return Task(
            config=self.tasks_config["rewrite_resume_task"],
            tools=[RewriteResumeTool()],
            output_pydantic=Resume_Final,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Rewrite Resume Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
