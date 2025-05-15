#!/usr/bin/env python
import asyncio
from typing import List,Dict

from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel,Field
from typing import Optional
from src.ats.crews.lead_response_crew.lead_response_crew import LeadResponseCrew
from src.ats.crews.lead_score_crew.lead_score_crew import LeadScoreCrew
from src.ats.crews.lead_filter_crew.lead_filter_crew import LeadFilterCrew
from src.ats.crews.web_scraper_crew.web_scraper_crew import WebScraperCrew
from src.ats.crews.resume_parser_crew.resume_parser_crew import ResumeParserCrew
from src.ats.crews.resume_score_crew.resume_score_crew import ResumeScoreCrew
from src.ats.crews.rewrite_resume_crew.rewrite_resume_crew import RewriteResumeCrew
from src.ats.types import Candidate, CandidateScore, ScoredCandidate,CandidateFilter,ResumeData,Resume_Final
from src.ats.utils.candidateUtils import combine_candidates_with_scores,extract_candidate_info,get_resume_text,send_email
import csv


class LeadScoreState(BaseModel):
    jd:str=""
    candidate_resumes:List[Dict] = []
    candidates: List[Candidate] = []
    failed_candidates: List[CandidateFilter] = []
    candidate_score: List[CandidateScore] = []
    candidate_filters:List[CandidateFilter] = []
    hydrated_candidates: List[ScoredCandidate] = []
    top_candidates: List[ScoredCandidate] = []
    scored_leads_feedback: str = ""

class CandidateScoreState(BaseModel):
    jd:str=""
    file_path:str = ""
    resume_data:ResumeData | None = None
    candidate_score: CandidateScore | None = None

class ImproveResumeState(BaseModel):
    jd:str=""
    resume_data:str = ""
    initial_score:CandidateScore | None = None
    improved_resume: Resume_Final | None = None
    is_rewrite:bool=False
    rewrite_count:int=0
    rewrite_score:CandidateScore | None = None


#Employer flow
class LeadScoreFlow(Flow[LeadScoreState]):
    @start()
    def load_leads(self):
        id=0
        candidates=[]
        for resume_file in self.state.candidate_resumes:
            # Step 1: Extract structured candidate info
            id+=1
            candidate_info = extract_candidate_info(resume_file["content"],resume_file["id"])
            candidates.append(candidate_info)
        with open("candidates_info.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "email", "bio","years_of_exp","skills"])
            for candidate in candidates:
                writer.writerow(
                    [
                        candidate.id,
                        candidate.name,
                        candidate.email,
                        candidate.bio,
                        candidate.years_of_exp,
                        candidate.skills
                    ]
                )
        #print("Candidates info saved to candidates_info.csv")   
        # Update the state with the loaded candidates
        self.state.candidates = candidates
    
    @listen(load_leads)
    async def filter_leads(self):
        #print("First level filtering of leads")
        tasks = []

        async def filter_candidate(candidate: Candidate):
            result = await (
                LeadFilterCrew()
                .crew()
                .kickoff_async(
                    inputs={
                        "candidate_id": candidate.id,
                        "name": candidate.name,
                        "bio": candidate.bio,
                        "years_of_exp": candidate.years_of_exp,
                        "skills": candidate.skills,
                        "job_description": self.state.jd,
                    }
                )
            )
    
            self.state.candidate_filters.append(result.pydantic)

        for candidate in self.state.candidates:
            #print("Scoring candidate:", candidate.name)
            task = asyncio.create_task(filter_candidate(candidate))
            tasks.append(task)

        candidate_filters = await asyncio.gather(*tasks)
        #print("Finished filtering leads: ", len(candidate_filters))
        with open("filtered_candidates.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "result", "reason"])
            for candidate in self.state.candidate_filters:
                writer.writerow(
                    [
                        candidate.id,
                        candidate.result,
                        candidate.reason,
                    ]
                )
        #print("Filtered Candidates info saved to filtered_candidates.csv")   

        #Filter failed candidates as a seperate list 
        self.state.failed_candidates = [
            cand
            for cand in self.state.candidate_filters
            if cand.result == "Fail"
        ]

        # Create a lookup dictionary from candidates using their ID
        id_to_email = {candidate.id: candidate.email for candidate in self.state.candidates}
        # Set the email in failed_candidates by matching ID for email sending purpose
        for candidate in self.state.failed_candidates:
            candidate_id = candidate.id
            candidate.email = id_to_email.get(candidate_id)
        

        #set of passed IDs
        passed_ids = {
            cf.id
            for cf in self.state.candidate_filters
            if cf.result == "Pass"
        }
        
        #Filter candidates list based on passed ids
        self.state.candidates = [
            cand
            for cand in self.state.candidates
            if cand.id in passed_ids
        ]

    @listen(or_(filter_leads, "scored_leads_feedback"))
    async def score_leads(self):
        #print("Scoring leads")
        #Create a lookup dictionary from resumes
        resume_lookup = {resume["id"]: resume["content"] for resume in self.state.candidate_resumes}
        # Update each candidate's bio using the lookup
        for candidate in self.state.candidates:
            if candidate.id in resume_lookup:
                candidate.bio = resume_lookup[candidate.id]

        tasks = []

        async def score_single_candidate(candidate: Candidate):
            result = await (
                LeadScoreCrew()
                .crew()
                .kickoff_async(
                    inputs={
                        "candidate_id": candidate.id,
                        "name": candidate.name,
                        "bio": candidate.bio,
                        "job_description": self.state.jd,
                        "additional_instructions": self.state.scored_leads_feedback,
                    }
                )
            )

            self.state.candidate_score.append(result.pydantic)

        for candidate in self.state.candidates:
            #print("Scoring candidate:", candidate.name)
            task = asyncio.create_task(score_single_candidate(candidate))
            tasks.append(task)

        candidate_scores = await asyncio.gather(*tasks)
        #print("Finished scoring leads")
        with open("scored_candidates.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "score", "reason"])
            for candidate in self.state.candidate_score:
                writer.writerow(
                    [
                        candidate.id,
                        candidate.score,
                        candidate.reason,
                    ]
                )
        #print("Scored Candidates info saved to scored_candidates.csv")   

    @router(score_leads)
    def human_in_the_loop(self):
        #print("Finding the top 3 candidates for human to review")

        # Combine candidates with their scores using the helper function
        self.state.hydrated_candidates = combine_candidates_with_scores(
            self.state.candidates, self.state.candidate_score
        )

        # Sort the scored candidates by their score in descending order
        sorted_candidates = sorted(
            self.state.hydrated_candidates, key=lambda c: c.score, reverse=True
        )
        self.state.hydrated_candidates = sorted_candidates

        # Select the top 3 candidates
        self.state.top_candidates = sorted_candidates[:3]

        # Present options to the user
        # print("\nPlease choose an option:")
        # print("1. Quit")
        # print("2. Redo lead scoring with additional feedback")
        # print("3. Proceed with writing emails to all leads")
        
        #Commenting for execution without interruption
        #choice = input("Enter the number of your choice: ")
        choice="3"

        if choice == "1":
            #print("Exiting the program.")
            exit()
        elif choice == "2":
            feedback = input(
                "\nPlease provide additional feedback on what you're looking for in candidates:\n"
            )
            self.state.scored_leads_feedback = feedback
            #print("\nRe-running lead scoring with your feedback...")
            return "scored_leads_feedback"
        elif choice == "3":
            #print("\nProceeding to write emails to all leads.")
            return "generate_emails"
        else:
            #print("\nInvalid choice. Please try again.")
            return "human_in_the_loop"

    @listen("generate_emails")
    async def write_and_save_emails(self):
        import re
        from pathlib import Path

        #print("Writing and saving emails for all leads.")

        # Determine the top 3 candidates to proceed with
        top_candidate_ids = {
            candidate.id for candidate in self.state.hydrated_candidates[:3]
        }

        tasks = []

        # Create the directory 'email_responses' if it doesn't exist
        output_dir = Path(__file__).parent / "email_responses"
        #print("output_dir:", output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        async def write_email(candidate):
            # Check if the candidate is among the top 3
            proceed_with_candidate = candidate.id in top_candidate_ids

            # Kick off the LeadResponseCrew for each candidate
            result = await (
                LeadResponseCrew()
                .crew()
                .kickoff_async(
                    inputs={
                        "candidate_id": candidate.id,
                        "name": candidate.name,
                        "reason": candidate.reason,
                        "proceed_with_candidate": proceed_with_candidate,
                    }
                )
            )

            # Sanitize the candidate's name to create a valid filename
            safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "", candidate.name)
            filename = f"{safe_name}.txt"
            #print("Filename:", filename)

            # Write the email content to a text file
            file_path = output_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.raw)
            
            #Send the corresponding email to each candidate
            send_email(file_path,candidate.email)

            # Return a message indicating the email was saved
            return f"Email sent for {candidate.name} as {filename} to {candidate.email}"
        
        #Create a composite list for all candidates 
        candidate_list = self.state.hydrated_candidates + self.state.failed_candidates

        # Create tasks for all candidates
        for candidate in candidate_list:
            task = asyncio.create_task(write_email(candidate))
            tasks.append(task)

        # Run all email-writing tasks concurrently and collect results
        email_results = await asyncio.gather(*tasks)

        # After all emails have been generated and saved
        #print("\nAll emails have been written and saved to 'email_responses' folder.")
        # for message in email_results:
        #     print(message)
    def reset(self):
        self.agents = []
        self.tasks = []
        self.memory = None


# Candidate flow
class CandidateScoreFlow(Flow[CandidateScoreState]):
    @start()
    def extract_job_descrpn(self):
        result = WebScraperCrew().crew().kickoff(
                    inputs={
                        "job_description": self.state.jd,
                    }
                )
        # Extract the actual string
        job_description = str(result)
        #print("Extracted website content:", job_description)
        #print(self.state.file_path)

        # Save result to state
        self.state.jd = job_description
            
    @listen(extract_job_descrpn)
    def parse_resume(self):
        #Extract data from resume
        result =ResumeParserCrew().crew().kickoff(
                    inputs={
                        "file_path": self.state.file_path
                    }
                )
        self.state.resume_data=result.pydantic
        #print(self.state.resume_data)
    
    @listen(parse_resume)
    def score_resume(self):
        result = ResumeScoreCrew().crew().kickoff(
            inputs={
                    "name": self.state.resume_data.name,
                    "email": self.state.resume_data.email,
                    "mobile_number": self.state.resume_data.mobile_number,
                    "skills": self.state.resume_data.skills,
                    "education": self.state.resume_data.education,
                    "objective": self.state.resume_data.objective,
                    "experience_years": self.state.resume_data.experience_years,
                    "experience_details": self.state.resume_data.experience_details,
                    "projects": self.state.resume_data.projects,
                    "certifications": self.state.resume_data.certifications,
                    "linkedin": self.state.resume_data.linkedin,
                    "github": self.state.resume_data.github,
                    "job_description": self.state.jd,
                }
            )
        
    
        self.state.candidate_score = result.pydantic
    def reset(self):
        self.agents = []
        self.tasks = []
        self.memory = None


# Improve resume flow
class ImproveResumeFlow(Flow[ImproveResumeState]):
    @start()
    def extract_job_descrpn(self):
        if self.state.jd:
            result = WebScraperCrew().crew().kickoff(
                        inputs={
                            "job_description": self.state.jd,
                        }
                    )
            # Extract the actual string
            job_description = str(result)
        else:
            job_description=""
        #print("Extracted website content:", job_description)

        # Save result to state
        self.state.jd = job_description
    
    @listen(or_("extract_job_descrpn", "rewrite_resume"))
    def score_resume(self):
        if self.state.is_rewrite:
            resume_data=self.state.improved_resume.resume_data
        else:
            resume_data=self.state.resume_data
            
        result = LeadScoreCrew().crew().kickoff(
                inputs={
                    "candidate_id": "1",
                    "name": "",
                    "bio": resume_data,
                    "job_description": self.state.jd,
                    "additional_instructions": "",
                }
            )   
        if self.state.is_rewrite:
            self.state.rewrite_score= result.pydantic
            self.state.improved_resume.score=self.state.rewrite_score.score
            #print("REWRITE SCORE IS ",self.state.improved_resume.score)
        else:
            self.state.initial_score= result.pydantic
            #print("INITIAL SCORE IS ",self.state.initial_score.score)
    @router("score_resume")
    def rewrite_condition_check(self):
        if self.state.is_rewrite:
            resume_score=self.state.rewrite_score.score
        else:
            resume_score=self.state.initial_score.score
        #print("REWRITE COUNT ",self.state.rewrite_count)
        if int(resume_score) < 85 and self.state.rewrite_count<=2:
            return "improve_resume"
    
    @listen("improve_resume")
    def rewrite_resume(self):
        #Rewrite resume
        #print("IN REWRITE RESUME job description is : ",self.state.jd)
        result =RewriteResumeCrew().crew().kickoff(
                    inputs={
                        "resume_data": self.state.resume_data,
                        "job_description": self.state.jd,
                    }
                )
        self.state.improved_resume=result.pydantic
        self.state.is_rewrite=True
        self.state.rewrite_count+=1
    
    def reset(self):
        self.agents = []
        self.tasks = []
        self.memory = None

def employer_kickoff(jd,candidate_resumes):
    """
    Run the flow.
    """
    lead_score_flow = LeadScoreFlow()
    lead_score_flow.reset()
    lead_score_flow.kickoff(inputs={"jd":jd,"candidate_resumes":candidate_resumes})
    plot()
    return lead_score_flow

def candidate_kickoff(jd,file_path):
    """
    Run the flow.
    """
    cand_score_flow = CandidateScoreFlow()
    cand_score_flow.reset()
    cand_score_flow.kickoff(inputs={"jd":jd,"file_path":file_path})
    cand_plot()
    return cand_score_flow

def improve_resume_for_ats(resume_data,jd):
    """
    Run the flow.
    """
    improve_resume_flow = ImproveResumeFlow()
    improve_resume_flow.reset()
    improve_resume_flow.kickoff(inputs={"jd":jd,"resume_data":resume_data})
    improve_resume_plot()
    return improve_resume_flow


def plot():
    """
    Plot the flow.
    """
    lead_score_flow = LeadScoreFlow()
    lead_score_flow.plot()

def cand_plot():
    """
    Plot the flow.
    """
    cand_score_flow = CandidateScoreFlow()
    cand_score_flow.plot()

def improve_resume_plot():
    """
    Plot the flow.
    """
    improve_resume_flow = ImproveResumeFlow()
    improve_resume_flow.plot()



