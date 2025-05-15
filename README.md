# CrewAI ATS Resume Screener & Rewriter
This is an intelligent Applicant Tracking System (ATS) Resume Screener & Rewriter built using CrewAI and LangChain tool integrations. It serves two primary user roles: Candidate and Employer.

## Features
### For Candidates
#### Resume Scoring
- Provide your resume and a job posting URL.
- The system analyzes and scores your resume based on ATS alignment with the job.
#### Resume Rewriting
- Upload a resume, and optionally provide a job posting URL.
- The system identifies gaps and rewrites your resume to improve the ATS score.
- Attempts rewriting up to 2 times for optimal improvement.

### For Employers
#### Candidate Evaluation
- Upload a job description as plain text.
- Upload multiple candidate resumes (PDF, DOCX, TXT).
- The system analyzes and ranks the top 3 best-fit candidates based on the job description.
- Automated Email Notifications
- Sends personalized emails to all candidates:
- Acceptance: Invitation for interview scheduling (top 3).
- Rejection: Polite rejection message (others).

## Tech Stack
Built with Python using uv and the following major libraries:

🤖 crewai[tools] — Agent orchestration

🧱 langchain-tools, crewai-tools — Tool abstraction for job and resume parsing

📧 google-auth-oauthlib, google-api-python-client — Gmail API integration for personalized emails

📊 pyvis — Visualizing the agent execution graph

⚡ onnxruntime — For fast LLM inference where applicable

📄 python-docx, docx2txt, pymupdf — Resume document parsing

🧠 spacy, nltk — NLP for keyword extraction and semantic comparison

🌐 firecrawl-py — Job post scraping from URLs

🌍 streamlit — Frontend interface for candidate and employer interaction

⚙️ asyncio, numpy — Utility libraries for async tasks and data processing

📂 Installation
bash
Copy
Edit
# Install uv if not already installed
pip install uv

# Install dependencies
uv pip install -r pyproject.toml
Or, if using requirements.txt:

bash
Copy
Edit
pip install -r requirements.txt
🛠️ Usage
Run the Streamlit App
bash
Copy
Edit
streamlit run app.py
Modes of Operation
Select your role: Candidate or Employer

Follow on-screen instructions to upload documents and optionally provide URLs

View results and email status in the dashboard


📎 File Types Supported
PDF

DOCX


📈 Output
For Candidates:
Score Report

Rewritten Resume

Comparison Overview

For Employers:
Top 3 Candidate Names

Email Dispatch Report

Ranking Table

🧪 Retry Mechanism
Resume rewriting has a 2-attempt max to ensure optimal rewriting without excessive API calls.
