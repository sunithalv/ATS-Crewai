from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type,Optional,Union
import re
import spacy

nlp = spacy.load("en_core_web_sm")


class ResumeInput(BaseModel):
    resume_data: Union[str, dict] = Field(..., description="Raw text of the resume or dictionary containing resume data")
    job_description: Optional[Union[str, dict]] = Field(default=None, description="Job description text or dictionary containing job description")

class RewriteResumeTool(BaseTool):
    name: str = "ATS Resume Rewriter"
    description: str = (
        "Analyzes and rewrites a resume to align with a job description by integrating missing keywords "
        "into relevant sections while preserving formatting."
    )
    args_schema: Type[BaseModel] = ResumeInput

    def _extract_keywords(self, jd_text: str) -> set:
        doc = nlp(jd_text)
        return {
            token.lemma_.lower()
            for token in doc
            if token.pos_ in {"NOUN", "PROPN", "ADJ", "VERB"} and not token.is_stop
        }

    def _check_missing_keywords(self, resume_text: str, jd_keywords: set) -> set:
        resume_doc = nlp(resume_text.lower())
        resume_tokens = {token.lemma_ for token in resume_doc if not token.is_stop}
        return jd_keywords - resume_tokens

    def _insert_keywords_contextually(self, resume: str, missing_keywords: set) -> str:
        sections = self._split_sections(resume)
        injected_keywords = set()
        rewritten_sections = []

        for header, content in sections:
            section_lower = header.lower()

            if section_lower in {"summary", "objective", "professional summary"}:
                enriched = self._enrich_section(content, missing_keywords, injected_keywords)
            elif section_lower in {"skills"}:
                enriched = self._add_to_comma_list(content, missing_keywords, injected_keywords)
            elif section_lower in {"experience", "work experience"}:
                enriched = self._enrich_section(content, missing_keywords, injected_keywords)
            else:
                enriched = content

            rewritten_sections.append(f"{header}\n{enriched}")

        rewritten_resume = "\n\n".join(rewritten_sections)
        return rewritten_resume.strip()

    def _split_sections(self, resume_text: str) -> list:
        # Match lines that look like section headers (title case, max ~40 chars)
        pattern = re.compile(r"^(?:[A-Z][A-Za-z\s]{2,40})$", re.MULTILINE)
        matches = list(pattern.finditer(resume_text))
        sections = []

        for i in range(len(matches)):
            start = matches[i].end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(resume_text)
            header = matches[i].group().strip()
            content = resume_text[start:end].strip()
            sections.append((header, content))

        return sections or [("Resume", resume_text)]


    def _enrich_section(self, text: str, keywords: set, used_keywords: set) -> str:
        doc = nlp(text)
        sentences = [sent.text for sent in doc.sents]
        enriched = []

        for sentence in sentences:
            enriched.append(sentence)

        # Add new sentence if keyword is not used
        new_sentences = []
        for keyword in keywords - used_keywords:
            new_sentences.append(f"Demonstrates strong proficiency in {keyword}.")
            used_keywords.add(keyword)

        if new_sentences:
            enriched.append(" ".join(new_sentences))

        return " ".join(enriched)

    def _add_to_comma_list(self, text: str, keywords: set, used_keywords: set) -> str:
        skills = [s.strip() for s in re.split(r"[,\n]", text) if s.strip()]
        for kw in keywords:
            if kw not in [s.lower() for s in skills]:
                skills.append(kw)
                used_keywords.add(kw)
        return ", ".join(skills)

    def _run(self, resume_data: Union[str, dict], job_description: Optional[Union[str, dict]] = None) -> dict:
        try:
            # Extract resume text
            resume_text = resume_data.get('description') if isinstance(resume_data, dict) else resume_data

            if not resume_text or not isinstance(resume_text, str):
                return {"resume_data": "", "feedback": "❌ Error: Invalid resume data format"}

            # Extract job description text
            jd_text = None
            if job_description:
                jd_text = job_description.get('description') if isinstance(job_description, dict) else job_description
                if not jd_text or not isinstance(jd_text, str):
                    return {"resume_data": "", "feedback": "❌ Error: Invalid job description format"}

            # If job description is provided
            if jd_text:
                jd_keywords = self._extract_keywords(jd_text)
                missing_keywords = self._check_missing_keywords(resume_text, jd_keywords)
                rewritten_resume = self._insert_keywords_contextually(resume_text, missing_keywords)

                feedback = (
                    f"✅ Resume rewritten based on provided job description.\n"
                    f"📝 Missing Keywords Identified: {', '.join(sorted(missing_keywords)) or 'None'}\n"
                    f"🔧 Keywords were integrated contextually into relevant sections (e.g., Summary, Skills, Experience).\n"
                    f"🎯 ATS Optimization Complete."
                )

            else:
                # Fallback to general enrichment (for now, return original)
                rewritten_resume = resume_text  # You can optionally enhance for generic ATS optimization.
                feedback = (
                    "ℹ️ No job description provided. Resume kept unchanged.\n"
                    "Consider tailoring your resume for each role to improve ATS compatibility."
                )

            return {
                "resume_data": rewritten_resume,
                "feedback": feedback
            }

        except Exception as e:
            return {
                "resume_data": "",
                "feedback": f"❌ Error preparing resume data: {str(e)}"
            }
