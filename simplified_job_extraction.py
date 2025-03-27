import json
import re
import sqlite3
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple regex-based skill extractor
class SimpleSkillExtractor:
    def __init__(self):
        self.tech_skills = [
            "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "php",
            "sql", "mongodb", "mysql", "react", "angular", "node.js", "django", "flask",
            "aws", "azure", "docker", "kubernetes", "git", "ai", "machine learning"
        ]
        self.pattern = re.compile(r'\b(' + '|'.join(self.tech_skills) + r')\b', re.IGNORECASE)
    
    def extract_skills(self, text):
        if not text:
            return []
        skills = []
        for match in self.pattern.finditer(text):
            skills.append({"name": match.group(0).lower(), "category": "TECHNICAL"})
        return skills

def process_jooble_data(json_file_path):
    """Process the Jooble data from the JSON file and store in SQLite"""
    try:
        # Read JSON file
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Extract jobs
        jobs = data.get("jobs", [])
        logger.info(f"Found {len(jobs)} jobs to process")
        
        # Setup SQLite database
        conn = sqlite3.connect('jooble_jobs.db')
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            description TEXT,
            url TEXT,
            salary TEXT
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            category TEXT
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_skills (
            job_id TEXT,
            skill_id INTEGER,
            PRIMARY KEY (job_id, skill_id),
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (skill_id) REFERENCES skills(id)
        )''')
        
        # Process jobs
        skill_extractor = SimpleSkillExtractor()
        processed_jobs = 0
        
        for job in jobs:
            job_id = str(job.get('id', ''))
            title = job.get('title', '')
            company = job.get('company', '')
            location = job.get('location', '')
            description = job.get('snippet', '')
            url = job.get('link', '')
            salary = job.get('salary', '')
            
            # Skip jobs without ID or title
            if not job_id or not title:
                continue
                
            # Insert job
            cursor.execute(
                "INSERT OR IGNORE INTO jobs (id, title, company, location, description, url, salary) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (job_id, title, company, location, description, url, salary)
            )
            
            # Extract and insert skills
            full_text = f"{title} {description}"
            skills = skill_extractor.extract_skills(full_text)
            
            for skill in skills:
                # Insert skill
                cursor.execute(
                    "INSERT OR IGNORE INTO skills (name, category) VALUES (?, ?)",
                    (skill["name"], skill["category"])
                )
                
                # Get skill ID
                cursor.execute("SELECT id FROM skills WHERE name = ?", (skill["name"],))
                skill_id = cursor.fetchone()[0]
                
                # Create relationship
                cursor.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)",
                    (job_id, skill_id)
                )
            
            processed_jobs += 1
            
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully processed {processed_jobs} jobs")
        return {"processed_jobs": processed_jobs, "success": True}
        
    except Exception as e:
        logger.error(f"Error processing Jooble data: {str(e)}")
        return {"processed_jobs": 0, "success": False, "error": str(e)}

if __name__ == "__main__":
    # Try to find the JSON file
    for file_name in ["tech_jobs_data.json", "test_output.json"]:
        if os.path.exists(file_name):
            logger.info(f"Processing {file_name}")
            result = process_jooble_data(file_name)
            print(f"Result: {result}")
            break
    else:
        logger.error("No Jooble data file found. Run test.py first.")
        print("No Jooble data file found. Run test.py first.")