import os
import json
import logging
from dotenv import load_dotenv
from neo4j import GraphDatabase
import re

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get Neo4j connection details
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

def check_original_json():
    """Check the original JSON file for proper values."""
    try:
        with open("tech_jobs_data.json", "r") as f:
            data = json.load(f)
        
        jobs = data.get("jobs", [])
        logger.info(f"Found {len(jobs)} jobs in JSON file")
        
        # Check the first job as an example
        if jobs:
            job = jobs[0]
            logger.info(f"Sample job from JSON:")
            logger.info(f"  Title: {job.get('title', 'None')}")
            logger.info(f"  Company: {job.get('company', 'None')}")
            logger.info(f"  Location: {job.get('location', 'None')}")
            
            # Check if there's a description with skills
            description = job.get('description', '')
            if description:
                skill_words = re.findall(r'\b(?:python|javascript|java|react|sql|data|cloud)\b', 
                                      description.lower())
                if skill_words:
                    logger.info(f"  Detected skills in description: {', '.join(skill_words)}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking JSON file: {str(e)}")
        return False

def check_neo4j_values():
    """Check Neo4j database values."""
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            # Check job nodes
            result = session.run("MATCH (j:Job) RETURN j LIMIT 5")
            jobs = [record["j"] for record in result]
            
            logger.info(f"Sample jobs from Neo4j:")
            for job in jobs:
                logger.info(f"  ID: {job.get('id', 'None')}")
                logger.info(f"  Title: {job.get('title', 'None')}")
                logger.info(f"  Company: {job.get('company', 'None')}")
                logger.info(f"  Location: {job.get('location', 'None')}")
            
            # Check skill nodes
            result = session.run("MATCH (s:Skill) RETURN s LIMIT 5")
            skills = [record["s"] for record in result]
            
            logger.info(f"Sample skills from Neo4j:")
            for skill in skills:
                logger.info(f"  Name: {skill.get('name', 'None')}")
            
            # Check job-skill relationships
            result = session.run("""
                MATCH (j:Job)-[r:REQUIRES_SKILL]->(s:Skill)
                RETURN j.title as job, s.name as skill
                LIMIT 10
            """)
            
            logger.info(f"Sample job-skill relationships:")
            for record in result:
                logger.info(f"  Job: {record['job']} -> Skill: {record['skill']}")
        
        return True
    except Exception as e:
        logger.error(f"Error checking Neo4j values: {str(e)}")
        return False

def fix_numeric_values():
    """Fix numeric values in the Neo4j database by using text from the JSON file."""
    try:
        # First, load the original data from JSON
        with open("tech_jobs_data.json", "r") as f:
            data = json.load(f)
        
        jobs_data = {str(job["id"]): job for job in data.get("jobs", [])}
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            # Get all job nodes
            result = session.run("MATCH (j:Job) RETURN j")
            jobs = [record["j"] for record in result]
            
            fixed_count = 0
            for job in jobs:
                job_id = job.get("id", "")
                # Try to find the job in the original data
                if str(job_id) in jobs_data:
                    original_job = jobs_data[str(job_id)]
                    
                    # Update job properties with original values
                    session.run("""
                        MATCH (j:Job {id: $id})
                        SET j.title = $title,
                            j.company = $company,
                            j.location = $location,
                            j.description = $description
                    """, {
                        "id": job_id,
                        "title": original_job.get("title", ""),
                        "company": original_job.get("company", ""),
                        "location": original_job.get("location", ""),
                        "description": original_job.get("description", "")
                    })
                    fixed_count += 1
            
            logger.info(f"Fixed {fixed_count} job nodes with data from original JSON")
            
            # Extract skills from job descriptions
            skills_extracted = set()
            for job_id, job in jobs_data.items():
                description = job.get("description", "")
                if description:
                    # Simple skill extraction pattern - add more keywords as needed
                    skill_words = re.findall(r'\b(?:python|javascript|java|react|sql|data science|cloud|aws|azure|devops|machine learning|ai|docker|kubernetes|html|css|node|express|django|flask|spring|angular|vue|tensorflow|pytorch|nlp|analytics|tableau|power bi|excel|statistics|agile|scrum|project management|communication|leadership)\b', 
                                         description.lower())
                    for skill in skill_words:
                        skills_extracted.add(skill)
            
            # Create skill nodes with proper text names
            for skill in skills_extracted:
                session.run("""
                    MERGE (s:Skill {name: $name})
                """, {"name": skill})
            
            logger.info(f"Created {len(skills_extracted)} skill nodes with proper text names")
            
            # Link jobs to skills based on description content
            relationship_count = 0
            for job_id, job in jobs_data.items():
                description = job.get("description", "")
                if description:
                    description_lower = description.lower()
                    for skill in skills_extracted:
                        if skill.lower() in description_lower:
                            session.run("""
                                MATCH (j:Job {id: $job_id})
                                MATCH (s:Skill {name: $skill_name})
                                MERGE (j)-[:REQUIRES_SKILL]->(s)
                            """, {
                                "job_id": job_id,
                                "skill_name": skill
                            })
                            relationship_count += 1
            
            logger.info(f"Created {relationship_count} job-skill relationships")
            
        return True
    except Exception as e:
        logger.error(f"Error fixing Neo4j values: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database check and fix process...")
    
    # Step 1: Check JSON file
    logger.info("\n=== Checking Original JSON File ===")
    check_original_json()
    
    # Step 2: Check Neo4j database
    logger.info("\n=== Checking Neo4j Database ===")
    check_neo4j_values()
    
    # Step 3: Fix numeric values
    logger.info("\n=== Fixing Numeric Values ===")
    success = fix_numeric_values()
    
    if success:
        logger.info("\n✅ Database values have been fixed successfully!")
        logger.info("Now you can run the RAG system with proper values:")
        logger.info("python job_rag_system.py")
    else:
        logger.error("\n❌ Failed to fix database values. Check the logs for details.") 