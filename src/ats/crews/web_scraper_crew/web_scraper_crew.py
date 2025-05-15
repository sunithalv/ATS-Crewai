from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
#from src.ats.crews.web_scraper_crew.tools.webscraper_tool import WebscraperTool
from crewai_tools import ScrapeWebsiteTool
import os


@CrewBase
class WebScraperCrew:
    """Lead Filter Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def web_scraper_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["web_scraper_agent"],  
            tools=[ScrapeWebsiteTool(
                    args={
                    'pageOptions': {
                    'onlyMainContent': True,
                    'includeHtml': False
                    },
                    'timeout': 60000  # 60 seconds
                    }
                    )],
            verbose=True,
        )

    @task
    def web_scraper_task(self) -> Task:
        return Task(
            config=self.tasks_config["web_scraper_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Web Scraper Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
