#!/usr/bin/env python3
"""
Jooble Jobs to Neo4j Pipeline

This script fetches jobs from the Jooble API, processes them with simplified_job_extraction.py,
and loads the data into a Neo4j database.

Usage:
    python jooble_to_neo4j.py

Requirements:
    - Jooble API key (available from Jooble for developers)
    - Neo4j database connection details in .env file
"""

import os
import json
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jooble_to_neo4j.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def run_pipeline():
    """Run the complete pipeline: fetch from Jooble -> process -> load into Neo4j"""
    logger.info("Starting Jooble to Neo4j pipeline")
    
    # Step 1: Fetch jobs from Jooble API
    logger.info("Step 1: Fetching jobs from Jooble API")
    try:
        import test as jooble_fetcher
        logger.info("Running Jooble API fetch script")
        # This will create tech_jobs_data.json
        jooble_fetcher_result = os.system("python test.py")
        if jooble_fetcher_result != 0:
            logger.error("Failed to fetch jobs from Jooble API")
            return False
        logger.info("Successfully fetched jobs from Jooble API")
    except ImportError:
        logger.error("Could not import test.py for Jooble API fetch")
        return False
    
    # Step 2: Process jobs with simplified_job_extraction.py
    logger.info("Step 2: Processing jobs with simplified extraction model")
    try:
        import simplified_job_extraction
        
        # Check if the database already exists
        if not os.path.exists("jooble_jobs.db"):
            # Process the data
            logger.info("Processing job data with simplified extraction model")
            result = simplified_job_extraction.process_jooble_data("tech_jobs_data.json")
            logger.info(f"Processing result: {result}")
            
            if not result.get("success", False):
                logger.error("Failed to process jobs with simplified extraction model")
                return False
        else:
            logger.info("Jobs database already exists, checking if it has data")
            # Verify the database has data
            import sqlite3
            conn = sqlite3.connect('jooble_jobs.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='jobs'")
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                cursor.execute("SELECT COUNT(*) FROM jobs")
                job_count = cursor.fetchone()[0]
                logger.info(f"Database has {job_count} jobs")
                if job_count == 0:
                    logger.error("Database exists but has no jobs")
                    return False
            else:
                logger.error("Database exists but has no jobs table")
                return False
            
            conn.close()
        
        logger.info("Successfully processed jobs with simplified extraction model")
    except ImportError as e:
        logger.error(f"Could not import simplified_job_extraction.py: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error processing jobs: {str(e)}")
        return False
    
    # Step 3: Build Neo4j graph from SQLite database
    logger.info("Step 3: Building Neo4j graph from SQLite database")
    try:
        import build_neo4j_graph
        logger.info("Running Neo4j graph builder")
        build_neo4j_graph.build_graph()
        logger.info("Successfully built Neo4j graph")
    except ImportError:
        logger.error("Could not import build_neo4j_graph.py")
        return False
    except Exception as e:
        logger.error(f"Error building Neo4j graph: {str(e)}")
        return False
    
    logger.info("Pipeline completed successfully!")
    return True

if __name__ == "__main__":
    success = run_pipeline()
    
    if success:
        print("\n========== PIPELINE COMPLETED SUCCESSFULLY ==========")
        print("Jobs have been fetched from Jooble API, processed, and loaded into Neo4j")
        print("\nYou can now use the RAG system with the job_rag_system.py script")
        print("or run queries directly against the Neo4j database.")
    else:
        print("\n========== PIPELINE FAILED ==========")
        print("Check jooble_to_neo4j.log for details on the error.")