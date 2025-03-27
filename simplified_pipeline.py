# Save as simplified_pipeline.py
import os
import logging
import subprocess
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_simplified_pipeline():
    """Run a simplified version of the Jooble to Neo4j pipeline"""
    logger.info("Starting simplified Jooble to Neo4j pipeline")
    
    # Step 1: Fetch jobs from Jooble API
    logger.info("Step 1: Fetching jobs from Jooble API")
    fetch_result = subprocess.run(["python", "test.py"], capture_output=True)
    if fetch_result.returncode != 0:
        logger.error(f"Failed to fetch jobs from Jooble: {fetch_result.stderr.decode()}")
        return False
    logger.info("Successfully fetched jobs from Jooble API")
    
    # Step 2: Process jobs with simplified extraction script
    logger.info("Step 2: Processing jobs with simplified extraction")
    process_result = subprocess.run(["python", "simplified_job_extraction.py"], capture_output=True)
    if process_result.returncode != 0:
        logger.error(f"Failed to process jobs: {process_result.stderr.decode()}")
        return False
    logger.info("Successfully processed jobs")
    
    # Step 3: Build Neo4j graph
    logger.info("Step 3: Building Neo4j graph")
    graph_result = subprocess.run(["python", "build_neo4j_graph.py"], capture_output=True)
    if graph_result.returncode != 0:
        logger.error(f"Failed to build Neo4j graph: {graph_result.stderr.decode()}")
        return False
    logger.info("Successfully built Neo4j graph")
    
    logger.info("Pipeline completed successfully!")
    return True

if __name__ == "__main__":
    success = run_simplified_pipeline()
    if success:
        print("\n===== SUCCESS: Pipeline completed successfully =====")
        print("Your Neo4j database has been populated with job data from Jooble.")
    else:
        print("\n===== ERROR: Pipeline failed =====")
        print("Check the log messages above for details.")