import os
from fastapi import FastAPI, UploadFile, File, Form, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import tempfile
import uuid
import logging
from typing import List, Optional, Dict, Any
import fitz  # PyMuPDF for PDF text extraction
from dotenv import load_dotenv
import re

# Import RAG system
from job_rag_system import JobRAGSystem
# Import agents - Fixed import statements
from resume_agent import ResumeAgent
from jd_agent import JD_agent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use system temp directory
TEMP_DIR = tempfile.gettempdir()

app = FastAPI(title="Job Market Intelligence API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get Neo4j connection details from environment
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
huggingface_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Initialize the RAG system (globally for all requests)
rag_system = JobRAGSystem(
    neo4j_uri=neo4j_uri,
    neo4j_user=neo4j_user,
    neo4j_password=neo4j_password,
    api_token=huggingface_token
)

# Define request models
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []

class JobSearchRequest(BaseModel):
    skill: str
    limit: int = 5

class SkillGapRequest(BaseModel):
    current_skills: List[str]
    target_role: str

# Utility functions
def extract_pdf_text(pdf_path):
    """Extract text from PDF document."""
    try:
        pdf_document = fitz.open(pdf_path)
        text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        pdf_document.close()
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF: {str(e)}")
        return f"Error extracting PDF: {str(e)}"

def extract_resume_info(resume_text):
    """Extract key information from resume text using improved regex patterns."""
    resume_info = {
        "name": "",
        "email": "",
        "phone": "",
        "education": [],
        "skills": [],
        "experience": [],
        "projects": [],
        "certificates": [],
        "languages": []
    }
    
    # Try to extract name (usually prominent at the top)
    name_pattern = r'^([A-Z][a-z]+ [A-Z][a-z]+)'
    name_match = re.search(name_pattern, resume_text.strip())
    if name_match:
        resume_info["name"] = name_match.group(1)
    
    # Extract email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, resume_text)
    if email_match:
        resume_info["email"] = email_match.group(0)
    
    # Extract phone
    phone_pattern = r'(\+\d{1,3}[-\.\s]??)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
    phone_match = re.search(phone_pattern, resume_text)
    if phone_match:
        resume_info["phone"] = phone_match.group(0)
    
    # Extract skills (look for common skill section headers and grab text after)
    skills_pattern = r'(?:SKILLS|TECHNICAL SKILLS|CORE COMPETENCIES)[:\s]*(.+?)(?:\n\n|\Z)'
    skills_match = re.search(skills_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    if skills_match:
        skills_text = skills_match.group(1)
        # Split by bullets, commas, or line breaks
        skills = re.split(r'[•,\n]+', skills_text)
        resume_info["skills"] = [skill.strip() for skill in skills if skill.strip()]
    
    # Additional extractions (education, experience, etc.) from main.py...
    # (Keeping it shorter for this implementation)
    
    return resume_info

def process_job_resume_match(resume_info, jd_text):
    """Enhanced matching that uses the RAG system capabilities."""
    # Extract skills from resume
    candidate_skills = resume_info.get("skills", [])
    
    # Use RAG system to find skill gaps
    if candidate_skills:
        # Use RAG system to analyze skill gaps
        skill_analysis = rag_system.get_skill_path(
            current_skills=candidate_skills,
            target_role=jd_text[:200]  # Use the first part of JD as target role
        )
        
        # Get relevant jobs from the job description text
        relevant_jobs = rag_system.search_jobs(jd_text, num_results=3)
        job_matches = []
        for job, sim, title in relevant_jobs:
            job_matches.append({
                "title": title,
                "company": job.get("company", "Unknown"),
                "similarity": sim,
                "description": job.get("description", "")[:200] + "..." if job.get("description") else ""
            })
        
        # Format the analysis
        matching_analysis = {
            "skill_match": {
                "skills_you_have": skill_analysis.get("already_have", []),
                "skills_to_learn": skill_analysis.get("skills_to_learn", []),
                "match_percentage": len(skill_analysis.get("already_have", [])) / max(1, len(skill_analysis.get("required_skills", []))) * 100
            },
            "similar_jobs": job_matches,
            "recommendations": "Focus on developing these skills: " + 
                              ", ".join(skill_analysis.get("skills_to_learn", [])[:3])
        }
        
        return matching_analysis
    else:
        # Fallback if no skills found
        return {
            "error": "Could not extract skills from resume",
            "recommendations": "Please ensure your resume clearly lists your skills."
        }

# Define endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Job Market Intelligence API"}

@app.post("/upload-resume-jd")
async def upload_resume_jd(file: UploadFile = File(...), job_description: str = Form(...)):
    # Generate a unique filename
    file_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{file_id}.pdf")

    # Save the file temporarily
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Log the received job description
    if not job_description or not file_id:
        return {"error": "No content received"}

    # Extract text from resume
    resume_text = extract_pdf_text(file_path)
    
    # Basic analysis - extract information from resume
    resume_info = extract_resume_info(resume_text)
    
    # Create ResumeAgent for deeper analysis
    resume_agent = ResumeAgent(file_path)
    resume_analysis = resume_agent.analyze_resume()
    
    # Create JD Agent for job description analysis
    jd_agent = JD_agent(job_description)
    jd_analysis = jd_agent.analyze_jd()
    
    # Use RAG system to enhance matching
    rag_matching = process_job_resume_match(resume_info, job_description)
    
    # Generate tailored resume using real resume information + RAG insights
    # Answer questions about the job using the RAG system
    job_insights = rag_system.answer_question(
        f"What are the key requirements and skills needed for the following job? {job_description[:500]}"
    )
    
    # Clean up the temporary file
    try:
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Error removing temp file: {str(e)}")

    return {
        "resume_id": file_id,
        "message": "Resume and Job Description processed successfully",
        "resume_analysis": resume_analysis,
        "jd_analysis": jd_analysis,
        "rag_matching": rag_matching,
        "job_insights": job_insights
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that uses RAG system to provide intelligent responses."""
    message = request.message
    
    # Use the RAG system to generate a response
    response = rag_system.answer_question(message)
    
    return {
        "response": response
    }

@app.post("/search/jobs")
async def search_jobs(request: JobSearchRequest):
    """Search for jobs using the RAG system."""
    # Search for jobs using the RAG system
    jobs = rag_system.search_jobs(request.skill, num_results=request.limit)
    
    # Format the results
    results = []
    for job, sim, title in jobs:
        results.append({
            "id": job.get("id", ""),
            "title": title,
            "company": job.get("company", "Unknown company"),
            "location": job.get("location", "Unknown location"),
            "similarity": sim,
            "description": job.get("description", "")[:200] + "..." if job.get("description") else ""
        })
    
    return {"results": results}

@app.post("/analyze/skill-gap")
async def analyze_skill_gap(request: SkillGapRequest):
    """Analyze skill gap between current skills and target role."""
    # Use RAG system to analyze skill gap
    analysis = rag_system.get_skill_path(
        current_skills=request.current_skills,
        target_role=request.target_role
    )
    
    return analysis

@app.post("/career-path")
async def find_career_path(from_role: str = Form(...), to_role: str = Form(...)):
    """Find a career path between two roles."""
    # Use RAG system to find career path
    path = rag_system.find_career_path(from_role, to_role)
    
    return {"path": path}

# Shutdown event to ensure connections are closed
@app.on_event("shutdown")
def shutdown_event():
    """Close connections when shutting down."""
    if rag_system:
        rag_system.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 