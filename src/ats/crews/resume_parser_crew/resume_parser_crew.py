from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from src.ats.crews.resume_parser_crew.tools.resume_parser_tool import ResumeParserTool
from src.ats.types import ResumeData


@CrewBase
class ResumeParserCrew:
    """Resume Parser Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    

    @agent
    def resume_parser_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["resume_parser_agent"],
            verbose=True,
        )

    @task
    def resume_parser_task(self) -> Task:
        return Task(
            config=self.tasks_config["resume_parser_task"],
            tools=[ResumeParserTool()],
            output_pydantic=ResumeData
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Resume Parser Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
