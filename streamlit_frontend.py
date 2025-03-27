import streamlit as st
import requests
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from job_rag_system import JobRAGSystem  # Import directly
import os
# Add import for visualization if needed
from job_network_visualization import visualize_job_skill_clusters
import tempfile
import uuid
import re
import fitz
import networkx as nx
import plotly.graph_objects as go
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Initialize JobRAGSystem directly (just like in job_rag_app.py)
if 'rag_system' not in st.session_state:
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    huggingface_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    # Initialize the RAG system
    st.session_state.rag_system = JobRAGSystem(
        neo4j_uri, neo4j_user, neo4j_password, huggingface_token
    )

# Page setup
st.set_page_config(
    page_title="Job Market Assistant",
    page_icon="💼",
    layout="wide"
)

# Header
st.title("💼 Job Market Intelligence Assistant")
st.markdown("""
This application provides intelligent insights about the job market using a Retrieval-Augmented Generation (RAG) system
connected to a Neo4j knowledge graph of job listings, skills, and relationships.
""")

# Create tabs for different functionalities - adding all tabs from job_rag_app.py
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Resume & Job Match", 
    "💬 Chat with RAG",
    "💻 Find Jobs by Skill", 
    "🛣️ Career Path Planner",
    "🔗 Skill Networks"
])

# Helper function from job_rag_app.py
def get_proper_job_title(job):
    """Get a properly formatted job title from a job object, avoiding numeric values."""
    # Check if job is None or empty
    if not job:
        return "Unknown Job"
        
    # Extract all potential fields
    job_id = str(job.get("id", ""))
    title = str(job.get("title", ""))
    company = str(job.get("company", ""))
    location = str(job.get("location", ""))
    description = str(job.get("description", ""))
    
    # First check: Is this an ID we need to replace?
    if title.startswith("-") and title.isdigit() or title.lstrip("-").isdigit():
        # This is definitely an ID, not a title
        title = ""  # Clear it so we can build a proper title
    
    # Look for job title patterns in company field (common issue)
    if "data scientist" in company.lower() or "engineer" in company.lower():
        return company  # Company field contains the actual job title
    
    # If title is valid, use it
    if title and not title.startswith("-") and not title.lstrip("-").isdigit() and len(title) > 5:
        return title
    
    # Check description for job title
    if description:
        # Try to extract job title from first line
        first_line = description.split('\n')[0] if '\n' in description else description.split('.')[0]
        # Check if first line looks like a job title
        job_title_keywords = ["engineer", "scientist", "developer", "analyst", "manager", "architect", "lead", "specialist"]
        if any(keyword in first_line.lower() for keyword in job_title_keywords):
            return first_line
    
    # Use company field with formatting if it looks valid
    if company and not company.startswith("-") and not company.lstrip("-").isdigit():
        if "data" in company.lower() or "engineer" in company.lower() or "scientist" in company.lower():
            return company
        else:
            return f"Position at {company}"
    
    # Last resort: use location with generic title
    if location and not location.startswith("-") and not location.lstrip("-").isdigit():
        return f"Job in {location}"
    
    # If all else fails, use description snippet
    if description:
        return description[:50] + "..." if len(description) > 50 else description
    
    # Absolute last resort
    return "Job Opportunity"  # Never return numeric ID

# Add this function near your other utility functions
def extract_skills_from_resume(resume_text):
    """Extract skills from resume with better categorization."""
    # Common tech skills to look for
    tech_skills = [
        # Programming languages
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Go", "Rust",
        # Web technologies
        "HTML", "CSS", "React", "Angular", "Vue", "Node.js", "Express", "Django", "Flask", "Spring", "Bootstrap",
        # Data technologies
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "Oracle", "SQL Server", "NoSQL", "Redis", "Cassandra",
        # Data science & ML
        "Machine Learning", "Deep Learning", "AI", "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy",
        # Cloud & DevOps
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "CI/CD", "Terraform", "Ansible", "DevOps",
        # General tools
        "Git", "GitHub", "Jira", "Confluence", "Agile", "Scrum", "REST API", "GraphQL"
    ]
    
    skills_found = []
    
    # First look for skills sections
    skills_section = re.search(r'(?i)(skills?|technical\s+skills|technologies)(?:[:\s]*)(.*?)(?:\n\n|\n[A-Z]|\Z)', resume_text, re.DOTALL)
    if skills_section:
        skills_text = skills_section.group(2)
        # Split by common delimiters and clean
        skills_list = re.split(r'[,•\n\|\-]', skills_text)
        skills_list = [s.strip() for s in skills_list if s.strip()]
        skills_found.extend(skills_list)
    
    # Also check for skills mentioned in experience sections
    for skill in tech_skills:
        if re.search(r'\b' + re.escape(skill) + r'\b', resume_text, re.IGNORECASE):
            if skill not in skills_found:
                skills_found.append(skill)
    
    return skills_found

# Tab 1: Resume and Job Match
with tab1:
    st.header("Resume and Job Description Matcher")
    st.markdown("Upload your resume and paste a job description to see how well you match the requirements.")
    
    # Upload resume
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf", key="resume_uploader")
    
    # Job description
    job_description = st.text_area(
        "Paste the job description:",
        height=200,
        placeholder="Paste the job description here...",
        key="job_description_area"
    )
    
    # Submit form - ONLY ONE BUTTON
    if st.button("Analyze Match", key="analyze_match_button"):
        if uploaded_file and job_description:
            with st.spinner("Analyzing your resume and the job description..."):
                try:
                    # Save the uploaded file temporarily
                    temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.pdf")
                    with open(temp_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Extract text from the PDF
                    resume_text = ""
                    try:
                        pdf_document = fitz.open(temp_file_path)
                        for page_num in range(pdf_document.page_count):
                            page = pdf_document.load_page(page_num)
                            resume_text += page.get_text()
                        pdf_document.close()
                    except Exception as e:
                        st.error(f"Error extracting text from PDF: {str(e)}")
                        resume_text = "Error extracting text"
                    
                    # Extract skills using the better function
                    resume_info = {"skills": extract_skills_from_resume(resume_text)}
                    
                    # Use RAG to get job insights
                    job_insights = st.session_state.rag_system.answer_question(
                        f"""Analyze this job description and provide a detailed breakdown of:
                        1. Required technical skills
                        2. Required soft skills
                        3. Experience level needed
                        4. Key responsibilities
                        
                        Job Description: {job_description[:1500]}
                        
                        Format your answer with clear sections and bullet points for readability."""
                    )
                    
                    # Use RAG to match skills
                    if resume_info["skills"]:
                        # Get skill gap analysis
                        skill_analysis = st.session_state.rag_system.get_skill_path(
                            current_skills=resume_info["skills"],
                            target_role=job_description[:200]  # Use beginning of JD as target role
                        )
                        
                        # Display the results
                        st.success("Analysis complete!")
                        
                        # Create columns for the display
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Resume Analysis")
                            st.markdown("#### Extracted Skills")
                            if resume_info["skills"]:
                                for skill in resume_info["skills"]:
                                    st.markdown(f"- {skill}")
                            else:
                                st.info("No skills extracted from resume. Consider adding a clear Skills section.")
                        
                        with col2:
                            st.subheader("Job Description Analysis")
                            # Check if the job insights is the default answer from MockLLM
                            if "After analyzing the job market data" in job_insights:
                                # Generate a better analysis manually
                                st.markdown("#### Key Requirements:")
                                
                                # Extract potential requirements from the job description
                                tech_skills = []
                                common_tech_skills = ["python", "java", "javascript", "react", "node", "sql", "aws", 
                                                     "azure", "docker", "kubernetes", "machine learning", "ai",
                                                     "devops", "ci/cd", "html", "css", "mongodb", "nosql"]
                                
                                for skill in common_tech_skills:
                                    if skill.lower() in job_description.lower():
                                        tech_skills.append(skill)
                                
                                if tech_skills:
                                    st.markdown("**Technical Skills:**")
                                    for skill in tech_skills:
                                        st.markdown(f"- {skill.title()}")
                                else:
                                    # Extract some phrases that might represent requirements
                                    requirement_patterns = [
                                        r"required skills[:\s]*(.*?)(?:\n\n|\Z)",
                                        r"qualifications[:\s]*(.*?)(?:\n\n|\Z)",
                                        r"requirements[:\s]*(.*?)(?:\n\n|\Z)"
                                    ]
                                    
                                    requirements_text = ""
                                    for pattern in requirement_patterns:
                                        match = re.search(pattern, job_description, re.IGNORECASE | re.DOTALL)
                                        if match:
                                            requirements_text += match.group(1) + "\n"
                                    
                                    if requirements_text:
                                        requirements = re.split(r'[•\-\*\n]', requirements_text)
                                        requirements = [r.strip() for r in requirements if r.strip()]
                                        for req in requirements[:5]:  # Show top 5 requirements
                                            if len(req) > 5:  # Only show non-trivial requirements
                                                st.markdown(f"- {req}")
                                    else:
                                        st.markdown("Please review the job description for specific requirements.")
                                
                                # Add some general comments
                                st.markdown("\n**Experience Level:**")
                                if "senior" in job_description.lower() or "lead" in job_description.lower():
                                    st.markdown("- Senior-level position requiring significant experience")
                                elif "junior" in job_description.lower() or "entry" in job_description.lower():
                                    st.markdown("- Junior/Entry-level position suitable for early career professionals")
                                else:
                                    st.markdown("- Mid-level position requiring relevant experience")
                            else:
                                # If we got good insights from the RAG system, display them
                                st.markdown(job_insights)
                        
                        # Show matching analysis
                        st.subheader("Match Analysis")
                        
                        if skill_analysis.get("success", False):
                            # Calculate match percentage
                            required_skills = skill_analysis.get("required_skills", [])
                            already_have = skill_analysis.get("already_have", [])
                            skills_to_learn = skill_analysis.get("skills_to_learn", [])
                            
                            if required_skills:
                                match_percentage = len(already_have) / len(required_skills) * 100
                                
                                # Create a progress bar for skill match
                                st.markdown(f"### Skill Match: {match_percentage:.1f}%")
                                st.progress(match_percentage / 100)
                                
                                # Create tabs for skills categories
                                skills_tab1, skills_tab2, skills_tab3 = st.tabs([
                                    "✅ Skills You Have", 
                                    "🎯 Skills to Learn", 
                                    "📋 All Required Skills"
                                ])
                                
                                with skills_tab1:
                                    if already_have:
                                        for skill in already_have:
                                            st.markdown(f"- **{skill}**")
                                    else:
                                        st.info("None of your current skills directly match the requirements.")
                                
                                with skills_tab2:
                                    if skills_to_learn:
                                        for skill in skills_to_learn:
                                            st.markdown(f"- **{skill}**")
                                    else:
                                        st.success("You already have all the required skills!")
                                
                                with skills_tab3:
                                    if required_skills:
                                        for skill in required_skills:
                                            st.markdown(f"- **{skill}**")
                                    else:
                                        st.info("No specific skills found for this role.")
                        else:
                            st.error("Could not perform skill gap analysis. The system may not have enough information about this job role.")
                        
                        # Related jobs with proper formatting
                        st.subheader("Similar Jobs in Our Database")
                        # Search for similar jobs
                        similar_jobs = st.session_state.rag_system.search_jobs(job_description, num_results=3)
                        if similar_jobs:
                            for job, sim, title in similar_jobs:
                                # Get proper job title
                                job_id = str(job.get("id", ""))
                                raw_title = str(job.get("title", ""))
                                company = str(job.get("company", "Unknown company"))
                                location = str(job.get("location", "Unknown location"))
                                description = str(job.get("description", ""))
                                
                                # Fix job title if it's a numeric ID
                                if not raw_title or raw_title.isdigit() or raw_title.startswith("-"):
                                    # Try to extract job title from description
                                    if description:
                                        first_line = description.split('\n')[0] if '\n' in description else description.split('.')[0]
                                        if len(first_line) > 5 and len(first_line) < 100:
                                            display_title = first_line
                                        else:
                                            # Extract job title keywords from description
                                            title_keywords = ["engineer", "developer", "manager", "analyst", "scientist", 
                                                             "specialist", "consultant", "lead", "architect", "designer"]
                                            for keyword in title_keywords:
                                                if keyword in description.lower():
                                                    display_title = f"{keyword.title()} Position"
                                                    break
                                            else:
                                                display_title = "Professional Position"
                                    else:
                                        # If no description, create a generic title based on company
                                        display_title = f"Position at {company}" if company else "Professional Opportunity"
                                else:
                                    display_title = raw_title
                                
                                # Display job with proper title
                                st.markdown(f"### {display_title}")
                                st.markdown(f"**Company:** {company} | **Location:** {location} | **Similarity:** {sim:.2f}")
                                with st.expander("Show details"):
                                    if description:
                                        st.write(description[:1000] + ("..." if len(description) > 1000 else ""))
                                    else:
                                        st.write("No detailed description available.")
                        else:
                            st.info("No similar jobs found in our database.")
                        
                        # Recommendations
                        st.subheader("Recommendations")
                        if skills_to_learn:
                            st.markdown("Based on your resume and the job requirements, focus on developing these skills:")
                            for i, skill in enumerate(skills_to_learn[:5]):
                                st.markdown(f"{i+1}. **{skill}**")
                                
                            # Add personalized recommendation based on resume
                            st.markdown("\n**Tailored Recommendations:**")
                            java_skills = any(s.lower() in "java spring springboot" for s in resume_info["skills"])
                            python_skills = any("python" in s.lower() for s in resume_info["skills"])
                            js_skills = any(s.lower() in "javascript node.js react" for s in resume_info["skills"])
                            
                            if java_skills and "python" in str(skills_to_learn).lower():
                                st.markdown("- Since you already know Java, learning Python should be straightforward. Focus on Python libraries relevant to this role.")
                            
                            if python_skills and any("machine learning" in s.lower() or "ai" in s.lower() for s in skills_to_learn):
                                st.markdown("- With your Python background, consider taking an online course in machine learning or AI to enhance your profile.")
                            
                            if js_skills and any("react" in s.lower() or "angular" in s.lower() for s in skills_to_learn):
                                st.markdown("- Your JavaScript experience provides a solid foundation. Focus on learning modern frameworks mentioned in the job description.")
                        else:
                            st.success("Your skills match well with this job! Consider highlighting your relevant experience in your application.")
                            
                            # Provide additional advice
                            st.markdown("\n**Application Tips:**")
                            st.markdown("- Tailor your resume to emphasize the matching skills")
                            st.markdown("- Prepare examples of your experience with these technologies for interviews")
                            st.markdown("- Research the company and prepare specific questions that show your interest")
                except Exception as e:
                    st.error(f"Error analyzing resume and job description: {str(e)}")
                    st.info("Try uploading a different PDF or check that your PDF is properly formatted.")
        else:
            # Show warnings for missing inputs
            if not uploaded_file:
                st.warning("Please upload your resume.")
            if not job_description:
                st.warning("Please enter a job description.")

# Tab 2: Chat with RAG
with tab2:
    st.header("Chat with Job Market Intelligence")
    st.markdown("Ask questions about the job market, skills, career paths, and more.")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    prompt = st.chat_input("Ask a question about jobs or skills")
    
    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Direct interaction with RAG system
            try:
                # Use the RAG system directly instead of API
                assistant_response = st.session_state.rag_system.answer_question(prompt)
                
                # Display the response
                message_placeholder.markdown(assistant_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            except Exception as e:
                message_placeholder.error(f"Error: {str(e)}")

# Tab 3: Find Jobs by Skill (from job_rag_app.py) 
with tab3:
    st.header("Find Jobs Requiring Specific Skills")
    
    # Skill input
    search_skill = st.text_input(
        "Enter a skill to search for jobs:",
        placeholder="e.g., Python, AWS, Machine Learning",
        key="skill_search_input"
    )
    
    num_results = st.slider("Number of results to show", 1, 10, 5, key="num_results_slider")
    
    # Submit button - WITH UNIQUE KEY
    if st.button("Search Jobs", key="search_jobs_button"):
        if search_skill:
            try:
                # Use RAG system directly
                with st.session_state.rag_system.driver.session() as session:
                    # First check if skill exists
                    skill_result = session.run(
                        "MATCH (s:Skill) WHERE toLower(s.name) CONTAINS toLower($skill) RETURN s",
                        skill=search_skill
                    )
                    skills = [record["s"] for record in skill_result]
                    
                    if skills:
                        # Find jobs requiring these skills
                        jobs_with_skills = []
                        for skill in skills:
                            job_result = session.run(
                                "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE s.name = $skill_name RETURN j, s.name as skill",
                                skill_name=skill.get("name", "")
                            )
                            for record in job_result:
                                job = record["j"]
                                skill_name = record["skill"]
                                # Calculate a simple score based on exact match
                                score = 1.0 if search_skill.lower() == skill_name.lower() else 0.8
                                jobs_with_skills.append((dict(job), score))
                        
                        # If no direct relationship found, search by text similarity
                        if not jobs_with_skills:
                            # Get all jobs and calculate similarity score
                            all_jobs_result = session.run("MATCH (j:Job) RETURN j")
                            all_jobs = [record["j"] for record in all_jobs_result]
                            
                            for job in all_jobs:
                                job_text = f"{job.get('title', '')} {job.get('description', '')}"
                                # Simple word match score
                                if search_skill.lower() in job_text.lower():
                                    score = 0.7  # Lower score for text match vs skill match
                                    jobs_with_skills.append((dict(job), score))
                        
                        # Sort by score and limit to requested number
                        jobs_with_skills.sort(key=lambda x: x[1], reverse=True)
                        top_jobs = jobs_with_skills[:num_results]
                        
                        # Display results
                        st.write(f"#### Top {min(num_results, len(top_jobs))} Jobs Requiring {search_skill}:")
                        
                        if top_jobs:
                            for job_dict, score in top_jobs:
                                # Process job data using the helper function
                                job_title = get_proper_job_title(job_dict)
                                company = job_dict.get("company", "Not specified")
                                location = job_dict.get("location", "Location not specified") 
                                description = job_dict.get("description", "")
                                
                                # Display job with proper formatting
                                st.markdown(f"### {job_title}")
                                st.markdown(f"**Relevance:** {score:.2f}")
                                
                                # Display details
                                with st.expander("Show details"):
                                    st.write(f"**Company:** {company}")
                                    st.write(f"**Location:** {location}")
                                    if description:
                                        st.write(f"**Description:** {description[:300]}...")
                                        if len(description) > 300:
                                            with st.expander("Show full description"):
                                                st.write(description)
                                    else:
                                        st.write("**Description:** No description available")
                        else:
                            st.write(f"No jobs found requiring {search_skill}.")
                    else:
                        st.write(f"No skills found matching '{search_skill}'.")
            except Exception as e:
                st.error(f"Error retrieving job data: {str(e)}")
                st.write("Please try a different skill or refresh the page.")
        else:
            st.warning("Please enter a skill to search for.")

# Tab 4: Career Path Planner
with tab4:
    st.header("Career Path Planner")
    st.markdown("Plan your career transition by identifying what skills you need to learn for your target role.")
    
    # Career path section
    st.subheader("Find Career Path")
    col1, col2 = st.columns(2)
    
    with col1:
        from_role = st.text_input("Current Role:", placeholder="e.g., Customer Service Representative", key="from_role_input")
    
    with col2:
        to_role = st.text_input("Target Role:", placeholder="e.g., Data Scientist", key="to_role_input")
    
    # UNIQUE KEY for button
    if st.button("Find Career Path", key="find_career_path_button") and from_role and to_role:
        with st.spinner(f"Finding career path..."):
            # Dictionary of common career transitions
            career_transitions = {
                # Data careers
                ("data analyst", "data scientist"): """
                ### Data Analyst to Data Scientist Career Path
                
                **Common skills you can leverage:**
                - SQL and database knowledge
                - Data cleaning and preparation
                - Data visualization
                - Basic statistical analysis
                - Python or R programming
                
                **Skills you need to develop:**
                - Advanced statistics and mathematics (linear algebra, calculus)
                - Machine learning algorithms and implementation
                - Deep learning frameworks (TensorFlow, PyTorch)
                - Feature engineering techniques
                - Experiment design and causal inference
                - Big data technologies (Spark, Hadoop)
                - Model deployment and MLOps
                """,
                
                ("business analyst", "data scientist"): """
                ### Business Analyst to Data Scientist Career Path
                
                **Common skills you can leverage:**
                - Business domain knowledge
                - Requirements gathering
                - Data analysis
                - SQL basics
                - Presentation skills
                
                **Skills you need to develop:**
                - Programming in Python or R
                - Statistics and probability
                - Machine learning algorithms
                - Data manipulation libraries (pandas, numpy)
                - Big data technologies
                - Cloud platforms (AWS, Azure, GCP)
                - Version control and collaborative coding
                """,
                
                ("software engineer", "data scientist"): """
                ### Software Engineer to Data Scientist Career Path
                
                **Common skills you can leverage:**
                - Programming skills
                - Algorithm knowledge
                - System design
                - Version control
                - Problem-solving skills
                
                **Skills you need to develop:**
                - Statistical analysis
                - Data visualization
                - Machine learning and AI 
                - Domain-specific knowledge
                - Experiment design
                - Scientific thinking
                - Research methodology
                """,
                
                # Software development careers
                ("frontend developer", "fullstack developer"): """
                ### Frontend Developer to Fullstack Developer Career Path
                
                **Common skills you can leverage:**
                - HTML, CSS, JavaScript
                - Frontend frameworks (React, Angular, Vue)
                - UI/UX understanding
                - Frontend testing
                - Version control
                
                **Skills you need to develop:**
                - Backend languages (Node.js, Python, Java, etc.)
                - Database design and management (SQL and NoSQL)
                - API development
                - Server configuration
                - Security best practices
                - DevOps basics
                """,
                
                ("backend developer", "fullstack developer"): """
                ### Backend Developer to Fullstack Developer Career Path
                
                **Common skills you can leverage:**
                - Server-side programming
                - Database knowledge
                - API development
                - Authentication and authorization
                - Performance optimization
                
                **Skills you need to develop:**
                - HTML, CSS fundamentals
                - JavaScript and modern frameworks
                - Frontend state management
                - Responsive design
                - Browser compatibility issues
                - UI/UX basics
                """,
                
                ("junior developer", "senior developer"): """
                ### Junior Developer to Senior Developer Career Path
                
                **Common skills you can leverage:**
                - Programming fundamentals
                - Basic debugging skills
                - Version control usage
                - Team collaboration
                
                **Skills you need to develop:**
                - System design and architecture
                - Design patterns
                - Technical leadership
                - Mentoring and code review
                - Project estimation and planning
                - Advanced debugging
                - Performance optimization 
                - Security best practices
                """,
                
                # Management careers
                ("developer", "team lead"): """
                ### Developer to Team Lead Career Path
                
                **Common skills you can leverage:**
                - Technical expertise
                - Problem-solving abilities
                - Project understanding
                - Code quality focus
                
                **Skills you need to develop:**
                - People management
                - Project management
                - Delegation skills
                - Conflict resolution
                - Coaching and mentoring
                - Strategic thinking
                - Stakeholder communication
                - Performance evaluation
                """,
                
                ("team lead", "engineering manager"): """
                ### Team Lead to Engineering Manager Career Path
                
                **Common skills you can leverage:**
                - Team leadership
                - Technical guidance
                - Sprint planning
                - Performance feedback
                - Code review
                
                **Skills you need to develop:**
                - Resource planning and budgeting
                - Cross-team coordination
                - Hiring and team building
                - Strategic roadmap planning
                - Process improvement
                - Department-level reporting
                - Career development frameworks
                - Executive communication
                """,
                
                # DevOps and Cloud careers
                ("system administrator", "devops engineer"): """
                ### System Administrator to DevOps Engineer Career Path
                
                **Common skills you can leverage:**
                - System configuration
                - Network knowledge
                - Troubleshooting skills
                - Security basics
                - Server management
                
                **Skills you need to develop:**
                - Infrastructure as Code (Terraform, CloudFormation)
                - CI/CD pipelines
                - Containerization (Docker, Kubernetes)
                - Cloud platforms (AWS, Azure, GCP)
                - Scripting and automation
                - Monitoring and observability
                - Version control (Git)
                """,
                
                ("developer", "devops engineer"): """
                ### Developer to DevOps Engineer Career Path
                
                **Common skills you can leverage:**
                - Programming knowledge
                - Debugging skills
                - Version control
                - Basic scripting
                - Build processes
                
                **Skills you need to develop:**
                - Linux/Unix administration
                - Cloud architecture
                - Container orchestration
                - Infrastructure automation
                - Network security
                - Log management
                - Monitoring solutions
                - High availability strategies
                """,
                
                # Other common transitions
                ("qa engineer", "developer"): """
                ### QA Engineer to Developer Career Path
                
                **Common skills you can leverage:**
                - Test automation
                - Bug reporting
                - Quality mindset
                - Understanding of requirements
                - Basic programming
                
                **Skills you need to develop:**
                - Advanced programming concepts
                - Data structures and algorithms
                - Design patterns
                - Framework knowledge
                - Database skills
                - Production-level code writing
                - Code optimization
                """,
                
                ("designer", "ux developer"): """
                ### Designer to UX Developer Career Path
                
                **Common skills you can leverage:**
                - Design principles
                - User-centric thinking
                - Wireframing
                - Visual composition
                - User research
                
                **Skills you need to develop:**
                - HTML, CSS, JavaScript
                - Responsive design implementation
                - Design system development
                - Accessibility standards
                - Frontend frameworks
                - Animation and interactive elements
                - Prototyping in code
                """
            }
            
            # Normalize input to lowercase for matching
            from_role_lower = from_role.lower()
            to_role_lower = to_role.lower()
            
            # Try to find an exact match first
            transition_key = (from_role_lower, to_role_lower)
            path_found = False
            
            if transition_key in career_transitions:
                st.markdown(career_transitions[transition_key])
                path_found = True
            else:
                # Try fuzzy matching - check if any key pairs contain our input
                for (key_from, key_to), path_info in career_transitions.items():
                    if (key_from in from_role_lower or from_role_lower in key_from) and \
                       (key_to in to_role_lower or to_role_lower in key_to):
                        st.markdown(f"### {from_role} to {to_role} Career Path")
                        st.markdown(path_info)
                        path_found = True
                        break
            
            # If no predefined path is found, try the RAG system
            if not path_found:
                # First try the RAG system
                try:
                    path = st.session_state.rag_system.find_career_path(from_role, to_role)
                    
                    # Check if the RAG system failed to find a path
                    if "I couldn't find specific job roles" in path or "couldn't find matching jobs" in path:
                        # Generate a generic path as fallback
                        st.markdown(f"""
                        ### {from_role} to {to_role} Career Path
                        
                        While I don't have specific information about this career transition in my database, here are some general recommendations:
                        
                        **Steps to consider:**
                        
                        1. **Research both roles thoroughly**
                           - Understand the day-to-day responsibilities of a {to_role}
                           - Research the technical and soft skills required
                           - Connect with people who have made similar transitions
                        
                        2. **Identify your transferable skills**
                           - Communication and collaboration
                           - Problem-solving abilities
                           - Industry or domain knowledge
                           - Project management experience
                        
                        3. **Develop a learning plan**
                           - Take relevant courses or certifications
                           - Build projects to demonstrate your capabilities
                           - Consider formal education if necessary
                        
                        4. **Gain practical experience**
                           - Look for opportunities in your current role to practice new skills
                           - Volunteer for projects related to your target role
                           - Consider internships or part-time opportunities
                        
                        5. **Network strategically**
                           - Attend industry events and meetups
                           - Connect with professionals in your target role
                           - Join online communities related to {to_role.lower()} roles
                        """)
                    else:
                        # Display the path from RAG system
                        st.markdown("### Career Transition Path")
                        st.markdown(path)
                except Exception as e:
                    st.error(f"Error finding career path: {str(e)}")
                    st.markdown(f"""
                    ### Generic {from_role} to {to_role} Transition
                    
                    I encountered an error while trying to create a specific path for you. Here are some general career transition tips:
                    
                    1. **Research** the target role thoroughly
                    2. **Identify** skill gaps between your current and target roles
                    3. **Create** a learning plan to acquire new skills
                    4. **Build** a portfolio showcasing relevant projects
                    5. **Network** with professionals in your target field
                    """)
                    
    # Show available jobs in the database for debugging
    with st.expander("Debug: See available job titles in database"):
        if st.button("Load Sample Job Titles", key="load_job_titles"):
            try:
                with st.session_state.rag_system.driver.session() as session:
                    result = session.run("MATCH (j:Job) RETURN j.title AS title LIMIT 50")
                    job_titles = [record["title"] for record in result if record["title"]]
                    
                    if job_titles:
                        st.write("Available job titles in the database:")
                        for title in job_titles:
                            st.write(f"- {title}")
                    else:
                        st.warning("No job titles found in the database or titles are empty/null.")
            except Exception as e:
                st.error(f"Error retrieving job titles: {str(e)}")
    
    # Skill gap analysis section
    st.header("Skill Gap Analysis")
    st.markdown("Analyze the skills you need to develop for your target role.")
    
    # Get current skills
    current_skills_text = st.text_area(
        "Enter your current skills (one per line):",
        placeholder="Python\nSQL\nData Analysis\nExcel",
        key="current_skills_textarea"
    )
    
    # Target role for skill gap analysis
    skill_gap_role = st.text_input(
        "Target Role for Skill Gap Analysis:",
        placeholder="e.g., Data Scientist, Software Engineer",
        key="skill_gap_role_input"
    )
    
    # UNIQUE KEY for button
    if st.button("Analyze Skill Gaps", key="analyze_skill_gaps_button") and current_skills_text and skill_gap_role:
        with st.spinner(f"Analyzing skills needed for {skill_gap_role}..."):
            # Parse skills (one per line, removing empty lines)
            current_skills = [skill.strip() for skill in current_skills_text.split('\n') if skill.strip()]
            
            # Use RAG system directly
            skill_analysis = st.session_state.rag_system.get_skill_path(current_skills, skill_gap_role)
            
            if skill_analysis.get("success", False):
                st.markdown("### Skill Gap Analysis")
                
                # Create columns for better visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Target Jobs:")
                    for job in skill_analysis.get("target_jobs", []):
                        proper_title = get_proper_job_title(job)
                        st.markdown(f"- {proper_title}")
                
                with col2:
                    if skill_analysis.get("current_role"):
                        st.markdown(f"#### Closest Match to Your Skills:")
                        current_role = skill_analysis.get("current_role")
                        proper_title = get_proper_job_title(current_role)
                        st.markdown(proper_title)
                
                # Skills visualization
                st.markdown("### Skills Breakdown")
                
                # Create tabs for different skill categories
                skills_tab1, skills_tab2, skills_tab3 = st.tabs([
                    "🎯 Skills to Learn", 
                    "✅ Skills You Already Have", 
                    "📋 All Required Skills"
                ])
                
                with skills_tab1:
                    skills_to_learn = skill_analysis.get("skills_to_learn", [])
                    if skills_to_learn:
                        for skill in skills_to_learn:
                            st.markdown(f"- **{skill}**")
                    else:
                        st.info("You already have all the required skills!")
                
                with skills_tab2:
                    already_have = skill_analysis.get("already_have", [])
                    if already_have:
                        for skill in already_have:
                            st.markdown(f"- **{skill}**")
                    else:
                        st.info("None of your current skills directly match the requirements.")
                
                with skills_tab3:
                    required_skills = skill_analysis.get("required_skills", [])
                    if required_skills:
                        for skill in required_skills:
                            st.markdown(f"- **{skill}**")
                    else:
                        st.info("No specific skills found for this role.")
                
                # Progress visualization
                if required_skills:
                    progress = len(already_have) / len(required_skills)
                    st.markdown("### Your Progress")
                    st.progress(progress)
                    st.markdown(f"You have **{len(already_have)}** out of **{len(required_skills)}** required skills ({int(progress * 100)}%)")
                    
                    # Recommendation for next steps
                    st.markdown("### Recommended Next Steps")
                    if skills_to_learn:
                        st.markdown("Focus on learning these high-priority skills:")
                        for skill in skills_to_learn[:3]:
                            st.markdown(f"1. **{skill}**")
            else:
                st.error(skill_analysis.get("message", "Failed to analyze skills"))

# Tab 5: Interactive Job Network Visualization
with tab5:
    st.header("Interactive Job Network Visualization")
    st.markdown("Explore the relationships between jobs, skills, and entities in an interactive network visualization.")
    
    # Create a function to build the network from Neo4j data
    def build_network_from_neo4j():
        """Build a network graph from Neo4j data"""
        try:
            # Initialize empty graph
            G = nx.Graph()
            
            # Get nodes and relationships from Neo4j
            with st.session_state.rag_system.driver.session() as session:
                # Get jobs
                job_result = session.run("MATCH (j:Job) RETURN j.id as id, j.title as name, j.company as company")
                jobs = [(record["id"], record["name"], record["company"]) for record in job_result]
                
                # Get skills
                skill_result = session.run("MATCH (s:Skill) RETURN s.name as name")
                skills = [record["name"] for record in skill_result]
                
                # Get job-skill relationships
                rel_result = session.run("""
                    MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill)
                    RETURN j.id as job_id, s.name as skill_name
                """)
                relationships = [(record["job_id"], record["skill_name"]) for record in rel_result]
            
            # Add job nodes
            for job_id, job_name, company in jobs:
                if job_name and not isinstance(job_name, (int, float)):
                    # Clean up job name if needed
                    display_name = job_name
                    if display_name.isdigit() or (display_name.startswith('-') and display_name[1:].isdigit()):
                        display_name = f"Job {job_id}"
                else:
                    display_name = f"Job {job_id}"
                
                G.add_node(
                    f"job_{job_id}",
                    name=display_name,
                    node_type="job",
                    company=company or "Unknown"
                )
            
            # Add skill nodes with categories
            skill_categories = {
                "python": "programming_language",
                "java": "programming_language",
                "javascript": "programming_language",
                "c++": "programming_language",
                "c#": "programming_language",
                "ruby": "programming_language",
                "php": "programming_language",
                "html": "web_development",
                "css": "web_development",
                "react": "web_development",
                "angular": "web_development",
                "vue": "web_development",
                "node.js": "web_development",
                "django": "web_development",
                "flask": "web_development",
                "data science": "data_science",
                "machine learning": "data_science",
                "artificial intelligence": "ai_llm",
                "ai": "ai_llm",
                "llm": "ai_llm",
                "sql": "database",
                "mysql": "database",
                "postgresql": "database",
                "mongodb": "database",
                "oracle": "database",
                "aws": "cloud_devops",
                "azure": "cloud_devops",
                "gcp": "cloud_devops",
                "docker": "cloud_devops",
                "kubernetes": "cloud_devops",
                "devops": "cloud_devops",
                "ci/cd": "cloud_devops",
                "git": "cloud_devops",
                "agile": "project_management",
                "scrum": "project_management",
                "jira": "project_management",
                "leadership": "soft_skill",
                "communication": "soft_skill",
                "teamwork": "soft_skill",
                "problem solving": "soft_skill"
            }
            
            for skill in skills:
                # Determine skill category
                skill_lower = skill.lower()
                category = "other"
                for key, cat in skill_categories.items():
                    if key in skill_lower:
                        category = cat
                        break
                
                G.add_node(
                    f"skill_{skill}",
                    name=skill,
                    node_type="skill",
                    category=category
                )
            
            # Add relationships
            for job_id, skill_name in relationships:
                G.add_edge(f"job_{job_id}", f"skill_{skill_name}")
            
            return G
        except Exception as e:
            st.error(f"Error building network: {str(e)}")
            return None
    
    # Function to create the visualization
    def create_job_network_visualization(G):
        # Get color mappings
        node_type_colors = {
            "job": "#6495ED",      # Cornflower Blue
            "skill": "#66CDAA",    # Medium Aquamarine
        }
        
        # Skill category colors
        category_colors = {
            "programming_language": "#4169E1",  # Royal Blue
            "web_development": "#20B2AA",       # Light Sea Green
            "data_science": "#9370DB",          # Medium Purple
            "database": "#3CB371",              # Medium Sea Green
            "cloud_devops": "#4682B4",          # Steel Blue
            "ai_llm": "#8A2BE2",                # Blue Violet
            "project_management": "#DAA520",    # Goldenrod
            "soft_skill": "#7B68EE",            # Medium Slate Blue
            "other": "#A9A9A9"                  # Dark Gray
        }
        
        # Create layout
        pos = nx.spring_layout(G, seed=42)
        
        # Prepare node data
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []
        node_symbols = []
        
        # Define node type symbols
        symbols = {
            "job": "circle",
            "skill": "diamond"
        }
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Node attributes
            node_type = G.nodes[node].get("node_type", "")
            node_name = G.nodes[node].get("name", "")
            category = G.nodes[node].get("category", "")
            company = G.nodes[node].get("company", "")
            
            # Add node color based on type and category
            if node_type == "job":
                node_color.append(node_type_colors.get("job"))
                node_size.append(20)  # Jobs are larger
            elif node_type == "skill":
                node_color.append(category_colors.get(category, category_colors["other"]))
                # Size based on degree centrality
                degree = G.degree(node)
                node_size.append(10 + (degree * 2))
            else:
                node_color.append("#CCCCCC")  # Default gray
                node_size.append(10)  # Default size
            
            # Add node symbol based on type
            node_symbols.append(symbols.get(node_type, "circle"))
            
            # Create node text
            if node_type == "job":
                hover_text = f"<b>Job:</b> {node_name}<br><b>Company:</b> {company or 'N/A'}<br><b>Connections:</b> {G.degree(node)}"
            elif node_type == "skill":
                hover_text = f"<b>Skill:</b> {node_name}<br><b>Category:</b> {category or 'N/A'}<br><b>Used in:</b> {G.degree(node)} jobs"
            else:
                hover_text = f"{node_name} (Unknown type)"
            
            node_text.append(hover_text)
        
        # Prepare edge data
        edge_x = []
        edge_y = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            # Add line trace points
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        # Create edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color="#CCCCCC"),
            mode="lines",
            hoverinfo="none",
            showlegend=False
        )
        
        # Create node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode="markers",
            hoverinfo="text",
            marker=dict(
                color=node_color,
                size=node_size,
                symbol=node_symbols,
                line=dict(width=1, color="#FFFFFF")
            ),
            text=node_text,
            hovertemplate="%{text}<extra></extra>"
        )
        
        # Create figure
        fig = go.Figure(data=[edge_trace, node_trace])
        
        # Add legend for node types and categories
        legend_traces = []
        
        # Add node type legend
        for node_type, color in node_type_colors.items():
            legend_trace = go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=color, symbol=symbols.get(node_type, "circle")),
                name=f"{node_type.capitalize()}",
                hoverinfo="none",
                showlegend=True
            )
            legend_traces.append(legend_trace)
        
        # Add skill category legend
        for category, color in category_colors.items():
            if category == "other":
                continue  # Skip 'other' category in legend
            
            # Format category name for display
            category_name = category.replace("_", " ").title()
            
            legend_trace = go.Scatter(
                x=[None], y=[None],
                mode="markers",
                marker=dict(size=10, color=color, symbol="diamond"),
                name=f"{category_name}",
                hoverinfo="none",
                showlegend=True
            )
            legend_traces.append(legend_trace)
        
        # Add legend traces to figure
        for trace in legend_traces:
            fig.add_trace(trace)
        
        # Update layout
        fig.update_layout(
            title=dict(
                text="Job and Skill Network Visualization",
                font=dict(size=20)
            ),
            showlegend=True,
            legend=dict(
                title=dict(text="Node Types"),
                font=dict(size=10),
                itemsizing="constant"
            ),
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#FFFFFF",
            height=700
        )
        
        return fig
    
    # Network building can take time, offer an option to build it
    if st.button("Generate Network Visualization", key="generate_network_button"):
        with st.spinner("Building network from database..."):
            try:
                # Build network from Neo4j data
                G = build_network_from_neo4j()
                
                if G and G.number_of_nodes() > 0:
                    st.success(f"Network built successfully with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
                    
                    # Create and display the visualization
                    fig = create_job_network_visualization(G)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display network statistics
                    with st.expander("Network Statistics"):
                        # Basic statistics
                        st.write(f"**Nodes:** {G.number_of_nodes()}")
                        st.write(f"**Edges:** {G.number_of_edges()}")
                        
                        # Node type counts
                        node_types = defaultdict(int)
                        for node in G.nodes():
                            node_type = G.nodes[node].get("node_type", "unknown")
                            node_types[node_type] += 1
                        
                        st.write("**Node Types:**")
                        for node_type, count in node_types.items():
                            st.write(f"- {node_type}: {count}")
                        
                        # Skill categories
                        if node_types["skill"] > 0:
                            skill_categories = defaultdict(int)
                            for node in G.nodes():
                                if G.nodes[node].get("node_type") == "skill":
                                    category = G.nodes[node].get("category", "unknown")
                                    skill_categories[category] += 1
                            
                            st.write("**Skill Categories:**")
                            for category, count in sorted(skill_categories.items(), key=lambda x: x[1], reverse=True):
                                st.write(f"- {category.replace('_', ' ').title()}: {count}")
                        
                        # Top skills (by connections)
                        skill_connections = []
                        for node in G.nodes():
                            if G.nodes[node].get("node_type") == "skill":
                                skill_connections.append((
                                    G.nodes[node].get("name", ""),
                                    G.degree(node)
                                ))
                        
                        if skill_connections:
                            st.write("**Top Skills (by connections):**")
                            for skill, connections in sorted(skill_connections, key=lambda x: x[1], reverse=True)[:10]:
                                st.write(f"- {skill}: {connections} jobs")
                    
                    # Skill distribution chart
                    with st.expander("Skill Distribution Chart"):
                        # Count skill occurrences
                        skill_counts = {}
                        skill_categories = {}
                        
                        for node in G.nodes():
                            if G.nodes[node].get("node_type") == "skill":
                                skill_name = G.nodes[node].get("name", "")
                                category = G.nodes[node].get("category", "other")
                                degree = G.degree(node)  # Number of connections
                                
                                skill_counts[skill_name] = degree
                                skill_categories[skill_name] = category
                        
                        if skill_counts:
                            # Create DataFrame
                            df = pd.DataFrame({
                                "Skill": list(skill_counts.keys()),
                                "Count": list(skill_counts.values()),
                                "Category": [skill_categories[skill] for skill in skill_counts.keys()]
                            })
                            
                            # Sort by count and get top skills
                            df = df.sort_values("Count", ascending=False).head(20)
                            
                            # Create bar chart
                            st.subheader("Top 20 Skills by Frequency in Job Postings")
                            st.bar_chart(df.set_index("Skill")["Count"])
                else:
                    st.warning("No nodes found in the database or failed to build network.")
            
            except Exception as e:
                st.error(f"Error generating visualization: {str(e)}")
    
    # Additional explanation about the visualization
    st.markdown("""
    ### Understanding the Network Visualization
    
    This interactive visualization shows the relationships between jobs and skills in our database:
    
    - **Blue circles** represent job positions
    - **Colored diamonds** represent skills, with colors indicating different skill categories
    - **Lines** show which skills are required for which jobs
    
    The size of a skill node indicates how many jobs require that skill - larger nodes are more in-demand skills.
    
    **Tips for interaction:**
    - Hover over nodes to see details
    - Click and drag to move the network
    - Zoom with your mouse wheel
    - Click on items in the legend to hide/show different categories
    """)

# Footer with information
st.markdown("---")
st.markdown("""
**About this application:** This app uses a Retrieval-Augmented Generation (RAG) system powered by:
- Neo4j graph database for job and skill relationships
- SimpleEmbeddings for semantic search
- HuggingFace or MockLLM for natural language generation
""")

# Ensure connection is closed when the app is done
def on_shutdown():
    if 'rag_system' in st.session_state:
        st.session_state.rag_system.close()

# Register the on_shutdown function
import atexit
atexit.register(on_shutdown) 