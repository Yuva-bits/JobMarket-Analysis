import http.client
import json
import time
import os
import subprocess
import sys

def fetch_jooble_jobs(keywords, location=""):
    host = 'jooble.org'
    key = '6aca5242-9a2e-4b00-9a81-420bc53f3888'
    
    connection = http.client.HTTPConnection(host)
    headers = {"Content-type": "application/json"}
    
    # Create query with keywords and location
    body = json.dumps({
        "keywords": keywords,
        "location": location
    })
    
    print(f"\nFetching jobs for: {keywords} in {location if location else 'any location'}")
    connection.request('POST', '/api/' + key, body, headers)
    response = connection.getresponse()
    print(f"Response: {response.status} {response.reason}")
    
    response_data = response.read().decode('utf-8')
    return response_data

# Define technical keywords to search for
tech_keywords = [
    "software engineer",
    "developer",
    "data scientist",
    "full stack",
    "devops",
    "cloud engineer",
    "machine learning"
]

# Define locations to search in
locations = ["", "Remote", "Switzerland"]  # Empty string means any location

# Delete existing database to start fresh
db_path = "jooble_jobs.db"
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")
    except OSError as e:
        print(f"Could not remove existing database: {str(e)}")
        print("Please close any applications that might be using the database file.")
        exit(1)

# Fetch and process jobs for each keyword and location
all_jobs = []
for keyword in tech_keywords:
    for location in locations:
        try:
            # Fetch jobs
            response_data = fetch_jooble_jobs(keyword, location)
            
            # Parse the response
            job_data = json.loads(response_data)
            
            # Get jobs from the response
            jobs = job_data.get("jobs", [])
            print(f"Found {len(jobs)} jobs for '{keyword}' in '{location if location else 'any location'}'")
            
            # Add to our collection
            all_jobs.extend(jobs)
            
            # Avoid rate limiting
            if keyword != tech_keywords[-1] or location != locations[-1]:
                print("Waiting 2 seconds before next request...")
                time.sleep(2)
        except Exception as e:
            print(f"Error fetching jobs for '{keyword}' in '{location}': {str(e)}")

# Remove duplicates (same job might appear in multiple searches)
unique_jobs = {}
for job in all_jobs:
    job_id = job.get("id", "")
    if job_id and job_id not in unique_jobs:
        unique_jobs[job_id] = job

print(f"\nTotal unique jobs fetched: {len(unique_jobs)}")

# Create a combined dataset
combined_data = {"jobs": list(unique_jobs.values())}

# Save the combined data to a file
with open("tech_jobs_data.json", "w") as f:
    json.dump(combined_data, f, indent=2)
    print("Response saved to tech_jobs_data.json")

def run_script(script_name, description):
    """Run a Python script and print its output"""
    print(f"\n{'='*80}")
    print(f"Running {description}: {script_name}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.STDOUT,
                               text=True)
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"\nWarning: {script_name} exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"\nError running {script_name}: {str(e)}")
        return False

# Try to process with our job extraction model
try:
    # Step 1: Process jobs with ML model
    print("\nStep 1: Processing jobs with ML model...")
    success_extraction = run_script("job_extraction_model.py", "Job Extraction Model")
    
    if success_extraction:
        print("\nJob data has been extracted and stored in the database (jooble_jobs.db)")
        
        # Step 2: Build Neo4j graph
        print("\nStep 2: Building Neo4j graph...")
        success_graph = run_script("build_neo4j_graph.py", "Neo4j Graph Builder")
        
        if success_graph:
            print("\nNeo4j graph has been built successfully")
            
            # Step 3: Check Neo4j data
            print("\nStep 3: Checking Neo4j data...")
            success_check = run_script("check_neo4j.py", "Neo4j Data Check")
            
            if success_check:
                print("\nNeo4j data verification completed successfully")
            else:
                print("\nWarning: Neo4j data verification had issues")
            
            # Step 4: Run RAG system
            print("\nStep 4: Testing RAG system...")
            success_rag = run_script("job_rag_system.py", "Job RAG System")
            
            if success_rag:
                print("\nRAG system test completed successfully")
            else:
                print("\nWarning: RAG system test completed with issues")
        else:
            print("\nWarning: Neo4j graph building had issues")
    else:
        print("\nWarning: Job extraction had issues")
    
    print("\nTo view job details and skills, run: python view_job_relationships.py")
    print("To visualize the job network, run: python visualize_job_network.py")
except ImportError:
    print("\nWarning: job_extraction_model module not found.")
    print("To process this data with the ML model, run: python job_extraction_model.py")
    print("The raw job data has been saved to tech_jobs_data.json")