import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

def get_proper_job_title(job):
    """Get a properly formatted job title from a job object, avoiding numeric values."""
    # Check if job is None or empty
    if not job or not isinstance(job, dict):
        return "Unknown Job"
        
    # Extract all potential fields
    job_id = str(job.get("id", ""))
    title = str(job.get("title", ""))
    company = str(job.get("company", ""))
    location = str(job.get("location", ""))
    description = str(job.get("description", ""))
    
    # If title is valid, use it
    if title and not title.startswith("-") and not title.lstrip("-").isdigit() and len(title) > 5:
        return title
    
    # Look for job title patterns in company field (common issue)
    if company and ("data scientist" in company.lower() or "engineer" in company.lower()):
        return company  # Company field contains the actual job title
    
    # Check description for job title
    if description:
        # Try to extract job title from first line
        first_line = description.split('\n')[0] if '\n' in description else description.split('.')[0]
        # Check if first line looks like a job title
        job_title_keywords = ["engineer", "scientist", "developer", "analyst", "manager", "architect", "lead", "specialist"]
        if any(keyword in first_line.lower() for keyword in job_title_keywords):
            return first_line[:50] + "..." if len(first_line) > 50 else first_line
    
    # Use company field with formatting if it looks valid
    if company and not company.startswith("-") and not company.lstrip("-").isdigit():
        return f"Position at {company}"
    
    # Last resort: use location with generic title
    if location and not location.startswith("-") and not location.lstrip("-").isdigit():
        return f"Job in {location}"
    
    # Absolute last resort
    return "Job Opportunity"  # Never return numeric ID

def create_job_skill_network(limit=10):
    """Create a network visualization of jobs and skills."""
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    # Create Neo4j driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Create network graph
        G = nx.Graph()
        
        with driver.session() as session:
            # Get jobs with limit
            job_result = session.run(f"MATCH (j:Job) RETURN j LIMIT {limit}")
            jobs = [record["j"] for record in job_result]
            
            # Add job nodes with proper titles
            for job in jobs:
                job_id = job.get("id", "")
                job_title = get_proper_job_title(job)
                G.add_node(job_id, type="job", title=job_title, 
                          company=job.get("company", ""), 
                          location=job.get("location", ""))
            
            # Get skills related to these jobs
            all_skills = set()
            for job in jobs:
                job_id = job.get("id", "")
                skill_result = session.run(
                    "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE j.id = $job_id RETURN s",
                    job_id=job_id
                )
                
                skills = [record["s"] for record in skill_result]
                for skill in skills:
                    skill_id = skill.get("name", "")
                    if not skill_id.lstrip("-").isdigit():  # Skip numeric skills
                        G.add_node(skill_id, type="skill", title=skill_id)
                        G.add_edge(job_id, skill_id)
                        all_skills.add(skill_id)
            
            # If we don't have enough skills, extract some from descriptions
            if len(all_skills) < 5:
                common_skills = [
                    "python", "java", "sql", "javascript", "react", "aws", "cloud",
                    "machine learning", "ai", "data science", "analytics", "docker"
                ]
                
                for job in jobs:
                    job_id = job.get("id", "")
                    description = str(job.get("description", "")).lower()
                    
                    for skill in common_skills:
                        if skill in description:
                            G.add_node(skill, type="skill", title=skill)
                            G.add_edge(job_id, skill)
                            all_skills.add(skill)
            
            # Get companies and locations as additional nodes
            for job in jobs:
                job_id = job.get("id", "")
                company = job.get("company", "")
                location = job.get("location", "")
                
                # Add company node if it's not numeric
                if company and not str(company).lstrip("-").isdigit():
                    G.add_node(company, type="company", title=company)
                    G.add_edge(job_id, company)
                
                # Add location node if it's not numeric
                if location and not str(location).lstrip("-").isdigit():
                    G.add_node(location, type="location", title=location)
                    G.add_edge(job_id, location)
        
        return G
    
    except Exception as e:
        st.error(f"Error creating network: {str(e)}")
        return nx.Graph()  # Return empty graph
    finally:
        driver.close()

def visualize_job_skill_network(G):
    """Visualize the job skill network."""
    plt.figure(figsize=(16, 12))
    
    # Create positions using spring layout for natural spacing
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Prepare node categories
    job_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'job']
    skill_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'skill']
    company_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'company']
    location_nodes = [n for n, attr in G.nodes(data=True) if attr.get('type') == 'location']
    
    # Choose colors
    job_color = 'skyblue'
    skill_color = 'lightgreen'
    company_color = 'orange'
    location_color = 'lightcoral'
    
    # Draw the nodes
    nx.draw_networkx_nodes(G, pos, nodelist=job_nodes, node_color=job_color, 
                          node_size=700, alpha=0.8, label='Job')
    nx.draw_networkx_nodes(G, pos, nodelist=skill_nodes, node_color=skill_color, 
                          node_size=500, alpha=0.8, label='Skill')
    nx.draw_networkx_nodes(G, pos, nodelist=company_nodes, node_color=company_color, 
                          node_size=500, alpha=0.8, label='Company')
    nx.draw_networkx_nodes(G, pos, nodelist=location_nodes, node_color=location_color, 
                          node_size=500, alpha=0.8, label='Location')
    
    # Draw the edges
    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)
    
    # Draw labels for nodes, use title attribute
    node_labels = {node: G.nodes[node].get('title', str(node)) for node in G.nodes()}
    
    # Draw labels with smaller font and higher visibility
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8, 
                          font_color='black', font_weight='bold')
    
    plt.title("Job Network Analysis: Skills and Relationships", fontsize=16)
    plt.legend(scatterpoints=1, loc='upper right', fontsize=10)
    plt.axis('off')
    plt.tight_layout()
    
    return plt

def visualize_job_skill_clusters(limit=15):
    """Create and visualize job-skill network with clusters."""
    G = create_job_skill_network(limit)
    
    if len(G.nodes) > 0:
        fig = visualize_job_skill_network(G)
        return fig
    else:
        return None 