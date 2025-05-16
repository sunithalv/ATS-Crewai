from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import os
from typing import Type
import re
import docx2txt
import fitz  # PyMuPDF

class ResumeParserInput(BaseModel):
    file_path: str = Field(
        ..., 
        description="Path to the resume file (PDF/DOCX) to be parsed."
    )

class ResumeParserTool(BaseTool):
    name: str = "Custom Resume Parser"
    description: str = (
        "Parses resumes from a file path (PDF/DOCX) and returns structured markdown-formatted data "
        "including name, email, phone, skills, education, experience, and social links."
    )
    args_schema: Type[BaseModel] = ResumeParserInput

    def _extract_text(self, file_path: str) -> str:
        if file_path.lower().endswith('.pdf'):
            doc = fitz.open(file_path)
            return "\n".join([page.get_text() for page in doc])
        elif file_path.lower().endswith('.docx'):
            return docx2txt.process(file_path)
        else:
            raise ValueError("Unsupported file type. Only PDF and DOCX are supported.")

    def _extract_field(self, text: str) -> dict:
        data = {}

        # Basic fields using regex
        data["email"] = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        #print("TEXT : ",text)
        # Phone number extraction 
        phone_pattern = re.compile(r"""
            (?:\+?\d{1,3}[-.\s]?)?              # Optional country code
            \(?\d{3}\)?[-.\s]?                   # Area code with optional parentheses
            \d{3}[-.\s]?                         # First 3 digits
            \d{4}                                # Last 4 digits
        """, re.VERBOSE)
        
        phone_match = phone_pattern.search(text)
        data["mobile_number"] = phone_match if phone_match else None
        

        data["linkedin"] = re.search(r"(https?://)?(www\.)?linkedin\.com/[^\s]+", text)
        data["github"] = re.search(r"(https?://)?(www\.)?github\.com/\S+", text)

        # Extract name: heuristic (first non-empty line with more than one word)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        data["name"] = lines[0] if lines and len(lines[0].split()) <= 5 else "Not found"

        # Extract sections using keywords
        lower_text = text.lower()

        def split_experience_entries(experience_text):
            job_entries = []

            # Remove bullet characters and normalize spacing
            cleaned = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u00b7\u2027\u25CF\u25CB\u25A0\u25A1\u25AA\u25AB\uF0B7]", "-", experience_text)
            cleaned = re.sub(r"\s{2,}", " ", cleaned)  # Collapse multiple spaces
            cleaned = cleaned.replace('\n', ' ').strip()

            # Match job entries like: Role | Company | Dates
            job_pattern = re.compile(r'([^\|]+?\|\s*[^\|]+?\|\s*[^|]+?)(?=\s+[^\|]+?\s+\|\s+[^\|]+?\s+\||\Z)', re.DOTALL)

            matches = job_pattern.findall(cleaned)
            for match in matches:
                job_entries.append(match.strip())

            return job_entries
        
        def split_skills(text):
            return [s.strip() for s in re.split(r'[,\n]', text) if s.strip()]
        
        def split_education_entries(text):
            return [line.strip() for line in text.split('\n') if line.strip()]

        def split_project_entries(text):
            return [line.strip() for line in text.split('\n\n') if line.strip()]

        def split_certifications(text):
            return [line.strip() for line in text.split('\n') if line.strip()]
        
        # def extract_section(possible_keywords):
        #     if isinstance(possible_keywords, str):
        #         possible_keywords = [possible_keywords]

        #     for keyword in possible_keywords:
        #         idx = lower_text.find(keyword.lower())
        #         if idx != -1:
        #             end_idx = lower_text.find('\n\n', idx)
        #             return text[idx:end_idx].strip() if end_idx != -1 else text[idx:].strip()
        #     return "Not found"
        
        def extract_experience(text):       
            experience_pattern = r"""
                (?:(?:\bwith|\bpossess|\bover|\baround)?\s*)      # Common prefixes
                (\d+(?:\.\d+)?)                                    # Number (e.g., 3 or 2.5)
                \s*                                                # Optional space
                (?:\+?\s*\d+)?                                     # Optional range like 3-5
                \s*                                                # Optional space
                (?:years?|yrs?)                                    # Variations of "years"
                (?:\s+of\s+(?:total\s+)??experience)?              # Optional "of experience"
            """
            match = re.search(experience_pattern, text, re.IGNORECASE | re.VERBOSE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, AttributeError):
                    return None
            return None
        
        def extract_section(text, section_keywords, all_headers):
            if isinstance(section_keywords, str):
                section_keywords = [section_keywords]

            # Create a combined regex pattern for headers (used to detect section boundaries)
            headers_pattern = '|'.join([re.escape(h) for h in all_headers])

            for keyword in section_keywords:
                # Regex to find the keyword as a header
                pattern = re.compile(rf'({keyword})\s*\n', flags=re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    start_idx = match.start()

                    # Match only when a known header appears alone or nearly alone on a line
                    next_header_pattern = re.compile(
                        rf'\n\s*({headers_pattern})\s*[:\-]?\s*\n',
                        flags=re.IGNORECASE
                    )
                    next_match = next_header_pattern.search(text, pos=match.end())
                    end_idx = next_match.start() if next_match else len(text)

                    return text[start_idx:end_idx].strip()

            return "Not found"
        
        # Common headers (all potential headers to detect section boundaries)
        all_headers = ["Experience", "Education", "Skills", "Certifications", "Projects", "Summary", "Objective", "Achievements"]

        objective_text = extract_section(
            text,
            section_keywords=["Objective", "Career Objective", "Professional Summary", "Summary"],
            all_headers=all_headers
        )
        data["objective"] = objective_text if objective_text != "Not found" else None

        skills_text = extract_section(
            text,
            section_keywords=["Skills", "Technical Skills", "Core Competencies"],
            all_headers=all_headers
        )
        data["skills"] = split_skills(skills_text)

        education_text = extract_section(
            text,
            section_keywords=["Education", "Academic Background", "Educational Qualifications"],
            all_headers=all_headers
        )
        data["education"] = split_education_entries(education_text)

        data["experience_years"] = extract_experience(text)

        experience_text = extract_section(text,
            section_keywords=["Experience", "Professional Experience", "Work Experience"],
            all_headers=all_headers
        )
        if experience_text.lower().startswith(("professional experience", "work experience", "experience")):
            experience_text = experience_text.split('\n', 1)[-1].strip()
        data["experience_details"] = split_experience_entries(experience_text)

        projects_text = extract_section(
            text,
            section_keywords=["Projects", "Key Projects", "Academic Projects"],
            all_headers=all_headers
        )
        data["projects"] = split_project_entries(projects_text)
        
        certs_text = extract_section(
            text,
            section_keywords=["Certifications", "Licenses", "Certificates"],
            all_headers=all_headers
        )
        data["certifications"] = split_certifications(certs_text)

        # Post-process regex matches
        for k in ["email", "mobile_number", "linkedin", "github"]:
            if data[k]:
                data[k] = data[k].group()
            else:
                data[k] = "Not found"

        return data

    def _run(self, file_path: str) -> str:
        try:
            if not os.path.isfile(file_path):
                return f"❌ Error: File does not exist at {file_path}"

            text = self._extract_text(file_path)
            extracted = self._extract_field(text)

            result = [f"**{k.replace('_', ' ').title()}**: {v}" for k, v in extracted.items()]
            return "\n".join(result)

        except Exception as e:
            return f"❌ An error occurred during parsing: {str(e)}"
