# job_match_scorer_app.py
import streamlit as st
import os
import tempfile
from src.ats.main import employer_kickoff,candidate_kickoff,improve_resume_for_ats
from src.ats.utils.candidateUtils import get_resume_text,display_resume
from dotenv import load_dotenv
load_dotenv()

# Streamlit app
st.set_page_config(
    page_title="Resume Match Scorer",
    layout="centered"
)

# Sidebar - Role selection (placed above API key input)
st.sidebar.title("🧭 Select Role")
selected_role = st.sidebar.selectbox("I am a...", ["Candidate", "Employer"])

# Sidebar - API Key input
st.sidebar.title("🔑 OpenAI API Key")
api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password")
# Conditional UI based on role
if selected_role == "Employer":
    st.title("ATS Match Tool (For Employer)")
    st.info(
        "Upload a **Job Description** and multiple **Candidate Resumes** (PDF or DOCX). The system will:\n"
        "1. **Parse and match** each resume against the job description.\n"
        "2. **Score and rank** the candidates.\n"
        "3. **Send personalized emails** to each candidate – selected or rejected – based on their match score."
    )

    # Inputs
    job_description = st.text_area("📝 Paste Job Description", height=300, placeholder="Paste the full job description here")

    uploaded_resumes = st.file_uploader(
        "📎 Upload Resume Files (PDF or DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True
    )

    if st.button("🔍 Score Resumes"):
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar.")
        elif not job_description.strip():
            st.error("Please enter the Job Description.")
        elif not uploaded_resumes:
            st.error("Please upload at least one resume.")
        else:
            os.environ["OPENAI_API_KEY"]=api_key

            with st.spinner("Analyzing resumes... This may take a minute."):

                try:
                    resume_texts = []
                    id=0
                    if uploaded_resumes:
                        for file in uploaded_resumes:
                            id+=1
                            text = get_resume_text(file)
                            resume_texts.append({
                                "id":str(id),
                                "filename": file.name,
                                "content": text
                            })
                    #Crewai flow
                    agent=employer_kickoff(job_description,resume_texts)
                    st.session_state.agent = agent  # Save for later use

                    if hasattr(agent.state, "top_candidates"):
                        st.markdown("## Top Candidates Identified")

                        for c in agent.state.top_candidates:
                            st.markdown(
                                f"**Name:** {c.name}<br>"
                                f"**Score:** {c.score}<br>"
                                f"**Reason:** {c.reason}<br><hr>",
                                unsafe_allow_html=True
                            )                  

                        st.success("✅ Email sent successfully to all candidates")

                except Exception as e:
                    st.error(f"Error processing files: {e}")

elif selected_role == "Candidate":

    # --- Title and Mode Selector ---
    st.title("🎯 Resume Assistant: Score or Improve Your Resume")
    st.info(
        "This tool offers two powerful features:\n"
        "1. **Score your resume against a job description** to see how well it fits.\n"
        "2. **Review and rewrite your resume** to improve your ATS (Applicant Tracking System) compatibility.\n\n"
        "➡️ Select your goal below to get started."
    )

    # --- Mode Selector ---
    mode = st.radio(
        "What would you like to do?",
        options=["Score Resume Against Job Description", "Rewrite Resume for ATS Compatibility"],
        index=0
    )
    # --- Page Logic Based on Mode ---
    if mode == "Score Resume Against Job Description":
        st.subheader("🧪 Resume Match Scorer (For Candidates)")

        job_url = st.text_input("Job Posting URL", placeholder="Enter the full URL here")
        uploaded_resume = st.file_uploader(
            "📎 Upload Your Resume (PDF or DOCX)",
            type=["pdf", "docx"],
        )

        if st.button("🔍 Score Resume"):
            if not api_key:
                st.error("Please enter your OpenAI API key in the sidebar.")
            elif not job_url.strip():
                st.error("Please enter the URL to parse.")
            elif not uploaded_resume:
                st.error("Please upload your resume.")
            else:
                os.environ["OPENAI_API_KEY"] = api_key

                with st.spinner("Analyzing your resume... This may take a minute."):
                    try:
                        with tempfile.TemporaryDirectory() as temp_dir:
                            temp_file_path = os.path.join(temp_dir, uploaded_resume.name)
                            with open(temp_file_path, "wb") as f:
                                f.write(uploaded_resume.getvalue())

                            agent = candidate_kickoff(job_url, temp_file_path)
                            st.session_state.agent = agent

                        if hasattr(agent.state, "candidate_score"):
                            st.title("Resume Scoring Summary")

                            st.subheader("📊 Candidate Score")
                            st.metric(label="ATS Score", value=f"{agent.state.candidate_score.score} / 100")

                            with st.expander("📋 Detailed Evaluation Reasoning", expanded=True):
                                st.write(agent.state.candidate_score.reason)

                            if agent.state.candidate_score.score >= 80:
                                st.success("Strong match — highly recommended for interview.")
                            elif agent.state.candidate_score.score >= 60:
                                st.warning("Moderate match — candidate shows potential, but has some gaps.")
                            else:
                                st.error("Low match — candidate lacks key qualifications for this role.")

                    except Exception as e:
                        st.error(f"Error processing files: {e}")

    elif mode == "Rewrite Resume for ATS Compatibility":
        st.subheader("🛠️ Resume Rewriter for ATS Compatibility")
        uploaded_resume = st.file_uploader("📎 Upload Your Resume (PDF or DOCX)", type=["pdf", "docx"])
        # Optional job description URL
        job_url = st.text_input("🔗 Optional: Enter Job Description URL (for tailored rewriting)")

        if st.button("🧠 Improve Resume"):
            if not api_key:
                st.error("Please enter your OpenAI API key in the sidebar.")
            elif not uploaded_resume:
                st.error("Please upload your resume.")
            else:
                os.environ["OPENAI_API_KEY"] = api_key

                with st.spinner("Rewriting your resume... Please wait."):
                    try:
                        resume_data = get_resume_text(uploaded_resume)
                        agent = improve_resume_for_ats(resume_data,job_url)
                        if hasattr(agent.state, "initial_score") and agent.state.initial_score is not None:
                            st.subheader("📊 Current Resume Score")
                            st.metric(label="ATS Score", value=f"{agent.state.initial_score.score} / 100")

                            with st.expander("📋 Detailed Evaluation Reasoning", expanded=True):
                                st.write(agent.state.initial_score.reason)

                        if hasattr(agent.state, "improved_resume") and agent.state.improved_resume is not None:
                            st.subheader("📊 Improved Resume Score")
                            st.metric(label="ATS Score", value=f"{agent.state.improved_resume.score} / 100")
                            resume_score= int(agent.state.improved_resume.score)
                            if resume_score<85:
                                feedback="""We've made the maximum improvements to your resume.
                                "While it's still scoring below the target of 85, this version reflects the most optimized 
                                version based on your input. For further enhancement, 
                                consider tailoring specific experiences or achievements more closely to the job role."""
                            else:
                                feedback="Here's a revised version of your resume with better ATS optimization:"
                            st.success(feedback)
                            st.markdown(agent.state.improved_resume.resume_data)
                            with st.expander("📋 Detailed Evaluation Feedback", expanded=True):
                                st.write(agent.state.improved_resume.feedback)
                            improved_resume=agent.state.improved_resume.resume_data
                            st.download_button(
                                label="⬇️ Download Improved Resume",
                                data=improved_resume.encode("utf-8"),
                                file_name="Resume_New.md",
                                mime="text/markdown"
                            )
                        else:
                            st.success("Your resume is already highly optimized for Applicant Tracking Systems (ATS), with a strong compatibility score")

                    except Exception as e:
                        st.error(f"Error improving resume: {e}")