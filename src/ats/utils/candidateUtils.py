from typing import List

from src.ats.types import Candidate, CandidateScore, ScoredCandidate
import csv
from  openai import OpenAI,OpenAIError  
import docx
import pdfplumber
import json
import os
import csv
import smtplib
from email.mime.text import MIMEText
import base64
import streamlit as st

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def get_resume_text(file):
    if file.type == "application/pdf":
        return extract_text_from_pdf(file)
    elif file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        return extract_text_from_docx(file)
    else:
        return None

def extract_candidate_info(resume_text,id)-> Candidate:
    prompt = (
        f"Extract the following information from the candidate resume:\n"
        f"- Full Name\n"
        f"- Email Address\n"
        f"- A short biodata (concise 3-4 line professional summary)\n"
        f"- Total Years of Professional Experience\n"
        f"- List of Key Skills (comma-separated)\n\n"
        f"Resume:\n{resume_text}\n\n"
        f"Respond in the following JSON format:\n"
        f"""{{
            "name": "<name>",
            "email": "<email>",
            "biodata": "<biodata>",
            "years_of_experience": "<years>",
            "skills": ["<skill1>", "<skill2>", "..."],
        }}"""
    )

    #To generate specific JSON structure from openai
    candidate_schema = {
    "name": "extract_candidate_info",
    "description": "Extracts structured candidate information from a resume.",
    "parameters": Candidate.model_json_schema()
    }   
    
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume screener and recruiter."},
                {"role": "user", "content": prompt}
            ],
            functions=[candidate_schema],
            function_call={"name": "extract_candidate_info"},
        )

        #print("RESPONSE : ",response)

        # Get and parse the arguments
        function_args = response.choices[0].message.function_call.arguments
    except OpenAIError as e:
        print(f"OpenAI API call failed: {e}")
        return None

    try:
        data = json.loads(function_args)
    except json.JSONDecodeError:
        # fallback if model responds badly
        return None
    data["id"] = str(id)
    return Candidate(**data)


def combine_candidates_with_scores(
    candidates: List[Candidate], candidate_scores: List[CandidateScore]
) -> List[ScoredCandidate]:
    """
    Combine the candidates with their scores using a dictionary for efficient lookups.
    """
    # print("COMBINING CANDIDATES WITH SCORES")
    # print("SCORES:", candidate_scores)
    # print("CANDIDATES:", candidates)
    # Create a dictionary to map score IDs to their corresponding CandidateScore objects
    score_dict = {score.id: score for score in candidate_scores}

    scored_candidates = []
    for candidate in candidates:
        score = score_dict.get(candidate.id)
        if score:
            scored_candidates.append(
                ScoredCandidate(
                    id=candidate.id,
                    name=candidate.name,
                    email=candidate.email,
                    bio=candidate.bio,
                    skills=candidate.skills,
                    score=score.score,
                    reason=score.reason,
                )
            )

    with open("lead_scores.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "email", "score"])
        for candidate in scored_candidates:
            writer.writerow(
                [
                    candidate.id,
                    candidate.name,
                    candidate.email,
                    candidate.score
                ]
            )
    #print("Lead scores saved to lead_scores.csv")
    return scored_candidates

def send_email(file_path,to_email):
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines[0].lower().startswith("subject:"):
            raise ValueError(f"File {file_path} does not start with 'Subject:'")

        subject = lines[0][8:].strip()
        body = "".join(lines[1:]).strip()

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            #print(f"Email sent to {to_email}")

    except Exception as e:
        print(f"Error sending to {to_email}: {e}")


def display_resume(file_bytes: bytes, file_name: str):
    """Displays the uploaded PDF in an iframe."""
    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    pdf_display = f"""
    <iframe 
        src="data:application/pdf;base64,{base64_pdf}" 
        width="100%" 
        height="600px" 
        type="application/pdf"
    >
    </iframe>
    """
    st.markdown(f"### Preview of {file_name}")
    st.markdown(pdf_display, unsafe_allow_html=True)


