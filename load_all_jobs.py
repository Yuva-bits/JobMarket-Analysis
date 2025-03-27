import json
import os
import logging
from job_extraction_model import JobPostExtractor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_all_jobs_from_json():
    """Load all jobs from tech_jobs_data.json and process them."""
    # Check if the JSON file exists
    if not os.path.exists("tech_jobs_data.json"):
        logger.error("tech_jobs_data.json not found. Please run test.py first.")
        return False
    
    # Load the JSON file
    with open("tech_jobs_data.json", "r") as f:
        data = json.load(f)
    
    jobs = data.get("jobs", [])
    logger.info(f"Found {len(jobs)} jobs in tech_jobs_data.json")
    
    if not jobs:
        logger.error("No jobs found in the JSON file.")
        return False
    
    # Create extractor
    extractor = JobPostExtractor()
    
    try:
        # Process each job
        job_ids = []
        for i, job in enumerate(jobs):
            logger.info(f"Processing job {i+1}/{len(jobs)}: {job.get('title', 'No title')}")
            job_id = extractor.process_job_post(job)
            if job_id:
                job_ids.append(job_id)
        
        logger.info(f"Successfully processed {len(job_ids)} out of {len(jobs)} jobs")
        return True
    except Exception as e:
        logger.error(f"Error processing jobs: {str(e)}")
        return False
    finally:
        extractor.close()

if __name__ == "__main__":
    success = load_all_jobs_from_json()
    if success:
        print("All jobs successfully loaded from JSON. Now run the Neo4j graph builder:")
        print("python build_neo4j_graph.py")
    else:
        print("Failed to load all jobs. Check the logs for details.") 