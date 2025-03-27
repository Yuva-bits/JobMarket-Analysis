from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
from job_rag_system import JobRAGSystem
import uvicorn
import logging
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Market RAG API",
    description="API for querying job market data using RAG"
)

# Initialize RAG system with proper credentials
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
huggingface_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Initialize the RAG system
rag_system = JobRAGSystem(neo4j_uri, neo4j_user, neo4j_password, huggingface_token)

# Request models
class QuestionRequest(BaseModel):
    question: str

class CareerPathRequest(BaseModel):
    current_skills: List[str]
    target_role: str

class SkillNetworkRequest(BaseModel):
    skill_name: str

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Job Market RAG API",
        "version": "1.0.0",
        "endpoints": [
            "/ask",
            "/career-path",
            "/skill-network"
        ]
    }

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Answer a question about jobs and careers using RAG."""
    try:
        answer = rag_system.answer_question(request.question)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/career-path")
async def get_career_path(request: CareerPathRequest):
    """Get a career path recommendation based on current skills and target role."""
    try:
        result = rag_system.get_skill_path(request.current_skills, request.target_role)
        
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=result.get("message", "Failed to analyze career path"))
            
        return result  # Return the result to the client
        
    except Exception as e:
        logger.error(f"Error getting career path: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/skill-network")
async def get_skill_network(request: SkillNetworkRequest):
    """Get the network of related skills and jobs for a specific skill."""
    try:
        skill_name = request.skill_name
        
        # Get jobs requiring this skill
        with rag_system.driver.session() as session:
            # Find jobs requiring this skill
            job_result = session.run("""
                MATCH (s:Skill)<-[:REQUIRES_SKILL]-(j:Job)
                WHERE toLower(s.name) CONTAINS toLower($skill_name)
                RETURN j.id as id, j.title as title, j.company as company
                LIMIT 10
            """, skill_name=skill_name)
            
            jobs = [dict(record) for record in job_result]
            
            # Find related skills (skills that appear with this one)
            skill_result = session.run("""
                MATCH (s1:Skill)<-[:REQUIRES_SKILL]-(j:Job)-[:REQUIRES_SKILL]->(s2:Skill)
                WHERE toLower(s1.name) CONTAINS toLower($skill_name) AND s1 <> s2
                RETURN s2.name as name, count(j) as job_count
                ORDER BY job_count DESC
                LIMIT 10
            """, skill_name=skill_name)
            
            related_skills = [record["name"] for record in skill_result]
        
        return {
            "skill": skill_name,
            "related_skills": related_skills,
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"Error getting skill network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources when the API is shut down."""
    rag_system.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)