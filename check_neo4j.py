from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Neo4j connection details
neo4j_uri = "bolt://localhost:7688"
neo4j_user = "neo4j"
neo4j_password = "password"

# Create a Neo4j driver
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

def check_neo4j_data():
    """Check the data in the Neo4j database."""
    try:
        with driver.session() as session:
            # Check the number of nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            print(f"Total nodes in the database: {count}")
            
            # Check skills
            result = session.run("MATCH (s:Skill) RETURN s")
            print("\nSkills in database:")
            for record in result:
                skill = record["s"]
                print(f"- ID: {skill.id}, Labels: {list(skill.labels)}")
                for key, value in skill.items():
                    print(f"  {key}: {value}")
            
            # Check jobs
            result = session.run("MATCH (j:Job) RETURN j")
            print("\nJobs in database:")
            for record in result:
                job = record["j"]
                print(f"- ID: {job.id}, Labels: {list(job.labels)}")
                for key, value in job.items():
                    print(f"  {key}: {value}")
            
            # Check relationships
            result = session.run("""
                MATCH (j:Job)-[r]->(s:Skill)
                RETURN j.title as job, type(r) as relation, s.name as skill
            """)
            print("\nRelationships between Jobs and Skills:")
            for record in result:
                print(f"- {record['job']} -{record['relation']}-> {record['skill']}")
    
    except Exception as e:
        print(f"Error connecting to Neo4j: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    check_neo4j_data() 