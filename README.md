---
title: CrewAI ATS Resume Screener Rewriter
emoji: 🐨
colorFrom: blue
colorTo: red
sdk: streamlit
sdk_version: 1.42.0
app_file: app.py
pinned: false
license: apache2.0
short_description: Resume Screener Rewriter using CrewAI flow
---

# CrewAI ATS Resume Screener & Rewriter

An AI-driven system built using CrewAI to streamline both employer-side candidate screening and candidate-side resume optimization for Applicant Tracking Systems (ATS).

## 🔧 Features

### 👔 Employer Mode
- Upload a **job description** and **multiple resumes**.
- Automatically **score resumes** based on relevance.
- **Top 3 candidates** receive personalized interview invitation emails.
- Remaining candidates receive **personalized rejection emails**.
- All emails are customized based on resume and job context.

### 👤 Candidate Mode
Two available options:
1. **ATS Resume Score Check**:
   - Enter a **job URL** to evaluate your resume.
   - Get a **personalized score** with actionable feedback.

2. **Resume Rewriting**:
   - Optional: Provide a **job URL** for targeted optimization.
   - Resume is rewritten **only if the score < 85**.
   - Supports up to **2 rewrite attempts**.
   - Returns final score and **detailed feedback**.

## 🚀 Tech Stack
- **Python 3.11**
- [CrewAI](https://github.com/joaomdmoura/crewai)
- LangChain Tools
- Gmail SMTP (secured with App Passwords)
- PyMuPDF, spaCy, NLTK
- Streamlit (for UI)
- ONNX Runtime for model inference

## 📦 Installation

```bash
git clone https://github.com/sunithalv/ATS-Crewai.git

# Install dependencies using uv
uv venv  # creates a virtual environment and activates it
uv pip install -e .
```

> Note: Python version must be >= 3.11 and < 3.12

## ▶️ Run the Application

Launch the app locally using Streamlit:

```bash
streamlit run app.py
```

> The UI will open in your browser at `http://localhost:8501`

## 📧 Gmail Integration

This project sends emails using Gmail's SMTP server. You'll need to configure your environment with the following variables:

### 🔐 Environment Setup

Create a `.env` file in the root directory with:

```
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
FIRECRAWL_API_KEY=your-firecrawl-api-key
```

> ⚠️ **Important**:  
> You must use a **Gmail App Password** if you have 2-Step Verification enabled.  
> Learn how to generate one: [Google App Passwords](https://support.google.com/accounts/answer/185833)  
>  
> Get your **Firecrawl API key** from [firecrawl.dev](https://firecrawl.dev) to enable parsing job descriptions from URLs.


### ✉️ Sending Emails

- Emails are sent using **SMTP** via `smtp.gmail.com` on port `587`.
- Each message is read from a `.txt` file where:
  - The **first line** must start with `Subject:`
  - The **remaining lines** form the email body.
- Emails are sent individually with **personalized content** for each recipient.

