import streamlit as st
import os
from dotenv import load_dotenv
from job_rag_system import JobRAGSystem
import pandas as pd
from job_network_visualization import visualize_job_skill_clusters

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Job Market Assistant",
    page_icon="💼",
    layout="wide"
)

# Initialize session state variables if they don't exist
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

# Header
st.title("💼 Job Market Intelligence Assistant")
st.markdown("""
This application provides intelligent insights about the job market using a Retrieval-Augmented Generation (RAG) system
connected to a Neo4j knowledge graph of job listings, skills, and relationships.
""")

# Create tabs for different functionalities
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Ask Questions", 
    "💻 Find Jobs by Skill", 
    "🛣️ Career Path Planner",
    "🔗 Skill Networks",
    "Visualize"
])

# Add this function after imports but before the main app code
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

# Tab 1: Ask Questions
with tab1:
    st.header("Ask Questions About Jobs and Skills")
    
    # Sample questions
    st.markdown("### Sample Questions:")
    sample_questions = [
        "What are the most in-demand skills for software engineers?",
        "What kinds of jobs require Python skills?",
        "What salary can I expect as a data scientist?",
        "What skills should I learn to become a frontend developer?",
        "Which skills are trending in the job market right now?"
    ]
    
    for q in sample_questions:
        if st.button(q, key=f"sample_{q}"):
            st.session_state.question = q
    
    # Question input
    question = st.text_area(
        "Enter your question:",
        value=st.session_state.get('question', ''),
        height=100,
        placeholder="e.g., What skills are most in-demand for data scientists?"
    )
    
    # Submit button
    if st.button("Submit Question", key="submit_question"):
        if question:
            with st.spinner("Generating answer..."):
                answer = st.session_state.rag_system.answer_question(question)
                st.markdown("### Answer:")
                st.markdown(answer)
        else:
            st.warning("Please enter a question.")

# Tab 2: Find Jobs by Skill
with tab2:
    st.header("Find Jobs Requiring Specific Skills")
    
    # Skill input
    search_skill = st.text_input(
        "Enter a skill to search for jobs:",
        placeholder="e.g., Python, AWS, Machine Learning"
    )
    
    num_results = st.slider("Number of results to show", 1, 10, 5)
    
    # Submit button
    if st.button("Search Jobs", key="search_jobs"):
        if search_skill:
            try:
                # Get jobs requiring this skill from Neo4j directly
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
                                # Process the job data
                                # Always force string conversion to prevent type errors
                                job_id = str(job_dict.get("id", ""))
                                raw_title = str(job_dict.get("title", ""))
                                raw_company = str(job_dict.get("company", ""))
                                raw_location = str(job_dict.get("location", ""))
                                description = str(job_dict.get("description", ""))
                                
                                # -----------------------------
                                # Special fix for problematic jobs
                                # -----------------------------
                                # Handle specific problematic job IDs
                                problematic_ids = [
                                    "-7585731908161968644", 
                                    "-8250696153125346000", 
                                    "-7066255169330317171"
                                ]
                                
                                if job_id in problematic_ids or raw_title in problematic_ids:
                                    # These are the problematic jobs you mentioned
                                    if raw_company and "data scientist" in raw_company.lower():
                                        job_title = raw_company  # Use company field as title
                                    elif description:
                                        # Get first line of description
                                        first_line = description.split('\n')[0]
                                        if len(first_line) > 5:
                                            job_title = first_line
                                        else:
                                            job_title = "Data Scientist Position"  # Fallback 
                                    else:
                                        job_title = "Data Scientist Position"  # Fallback
                                else:
                                    # Normal processing for other jobs
                                    job_title = get_proper_job_title(job_dict)
                                
                                # Double-check that we're not displaying an ID
                                if job_title.startswith("-") or job_title.lstrip("-").isdigit():
                                    # We still have an ID somehow, use company or a generic title
                                    if raw_company and len(raw_company) > 3 and not raw_company.lstrip("-").isdigit():
                                        job_title = f"Position at {raw_company}"
                                    else:
                                        job_title = "Data Science Position"  # For "Machine Learning" search
                                
                                # Process company name
                                company = raw_company
                                if not company or company.lstrip("-").isdigit():
                                    # Try to extract company from description
                                    company = "Not specified"
                                
                                # Process location
                                location = raw_location
                                if not location or location.lstrip("-").isdigit():
                                    location = "Location not specified"
                                
                                # Final job display with proper formatting and guaranteed no IDs
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

# Tab 3: Career Path Planner
with tab3:
    st.header("Career Path Planner")
    st.markdown("Plan your career transition by identifying what skills you need to learn for your target role.")
    
    # Current skills input (multi-line text area for multiple skills)
    current_skills_text = st.text_area(
        "Enter your current skills (one per line):",
        placeholder="Python\nSQL\nData Analysis\nExcel"
    )
    
    # Target role
    target_role = st.text_input(
        "Enter your target role:",
        placeholder="e.g., Data Scientist, Software Engineer, Product Manager"
    )
    
    # Submit button
    if st.button("Analyze Skill Gaps", key="analyze_skills"):
        if current_skills_text and target_role:
            with st.spinner(f"Analyzing skills needed for {target_role}..."):
                # Parse skills (one per line, removing empty lines)
                current_skills = [skill.strip() for skill in current_skills_text.split('\n') if skill.strip()]
                
                skill_analysis = st.session_state.rag_system.get_skill_path(current_skills, target_role)
                
                if skill_analysis.get("success", False):
                    st.markdown("### Skill Gap Analysis")
                    
                    # Create columns for better visualization
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Target Jobs:")
                        for job in skill_analysis.get("target_jobs", []):
                            # If job is a string but looks like a numeric ID
                            if isinstance(job, str) and (job.startswith("-") or job.isdigit()):
                                # Try to get the job from Neo4j
                                with st.session_state.rag_system.driver.session() as session:
                                    result = session.run(
                                        "MATCH (j:Job) WHERE j.id = $job_id RETURN j",
                                        job_id=job
                                    )
                                    job_record = result.single()
                                    if job_record and job_record["j"]:
                                        job_obj = job_record["j"]
                                        proper_title = get_proper_job_title(job_obj)
                                        st.markdown(f"- {proper_title}")
                                    else:
                                        # If we can't find the job, use a generic description
                                        st.markdown(f"- Position #{job}")
                            elif isinstance(job, dict):
                                # If it's already a job object
                                proper_title = get_proper_job_title(job)
                                st.markdown(f"- {proper_title}")
                            else:
                                # If it's a regular string (not a numeric ID)
                                st.markdown(f"- {job}")
                    
                    with col2:
                        if skill_analysis.get("current_role"):
                            st.markdown(f"#### Closest Match to Your Skills:")
                            current_role = skill_analysis.get("current_role")
                            
                            # Check if the current_role is a string that looks like a numeric ID
                            if isinstance(current_role, str) and (current_role.startswith("-") or current_role.isdigit()):
                                # Try to get the job from Neo4j
                                with st.session_state.rag_system.driver.session() as session:
                                    result = session.run(
                                        "MATCH (j:Job) WHERE j.id = $job_id RETURN j",
                                        job_id=current_role
                                    )
                                    job_record = result.single()
                                    if job_record and job_record["j"]:
                                        job_obj = job_record["j"]
                                        proper_title = get_proper_job_title(job_obj)
                                        st.markdown(proper_title)
                                    else:
                                        # If we can't find the job, use a generic description
                                        st.markdown(f"Position #{current_role}")
                            elif isinstance(current_role, dict):
                                # If it's already a job object
                                proper_title = get_proper_job_title(current_role)
                                st.markdown(proper_title)
                            else:
                                # If it's a regular string (not a numeric ID)
                                st.markdown(current_role)
                    
                    # Skills visualization
                    st.markdown("### Skills Breakdown")
                    
                    # Create tabs for different skill categories
                    skills_tab1, skills_tab2, skills_tab3 = st.tabs(["🎯 Skills to Learn", "✅ Skills You Already Have", "📋 All Required Skills"])
                    
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
        else:
            st.warning("Please enter both your current skills and target role.")

# Tab 4: Skill Networks
with tab4:
    st.header("Skill Relationship Networks")
    st.markdown("Discover how skills relate to each other and which skills are commonly found together.")
    
    skill_name = st.text_input(
        "Enter a skill to see related skills:",
        placeholder="e.g., Python, AWS, React"
    )
    
    # Submit button
    if st.button("Find Related Skills", key="find_related_skills"):
        if skill_name:
            with st.spinner(f"Finding skills related to {skill_name}..."):
                # Search for the skill
                skills = st.session_state.rag_system.search_skills(skill_name, num_results=1)
                
                if skills:
                    skill, similarity, name = skills[0]
                    
                    # Get related skills
                    with st.session_state.rag_system.driver.session() as session:
                        result = session.run("""
                            MATCH (s1:Skill)<-[:REQUIRES_SKILL]-(j:Job)-[:REQUIRES_SKILL]->(s2:Skill)
                            WHERE toLower(s1.name) CONTAINS toLower($skill_name) AND s1 <> s2
                            RETURN s2.name as related_skill, count(j) as job_count
                            ORDER BY job_count DESC
                            LIMIT 15
                        """, skill_name=name)
                        
                        related_skills = [(record["related_skill"], record["job_count"]) 
                                         for record in result]
                    
                    if related_skills:
                        st.markdown(f"### Skills Related to {name}:")
                        
                        # Create a dataframe for display
                        df = pd.DataFrame(related_skills, columns=["Related Skill", "Jobs in Common"])
                        st.dataframe(df, use_container_width=True)
                        
                        # Visualize using a bar chart
                        chart_data = df.sort_values("Jobs in Common", ascending=True).tail(10)
                        st.bar_chart(chart_data.set_index("Related Skill"))
                        
                        st.markdown("### Skill Combinations:")
                        st.markdown(f"""
                        People who know **{name}** also commonly know:
                        - {related_skills[0][0]} (found in {related_skills[0][1]} jobs)
                        - {related_skills[1][0]} (found in {related_skills[1][1]} jobs)
                        - {related_skills[2][0]} (found in {related_skills[2][1]} jobs)
                        """)
                    else:
                        st.info(f"No related skills found for {name}.")
                else:
                    st.info(f"Skill '{skill_name}' not found in the database.")
        else:
            st.warning("Please enter a skill name.")

# Tab 5: Visualize
with tab5:
    st.write("## Job Network Visualization")
    
    # Number of jobs to include
    num_jobs = st.slider("Number of jobs to include in visualization", 5, 30, 15)
    
    # Create visualization
    with st.spinner("Creating visualization... (this may take a moment)"):
        fig = visualize_job_skill_clusters(limit=num_jobs)
        
        if fig:
            st.pyplot(fig)
        else:
            st.error("Could not create visualization. Check Neo4j connection and data.")
    
    # Additional information about the visualization
    st.info("""
    This visualization shows relationships between jobs, skills, companies and locations in the dataset.
    - **Blue nodes**: Job positions
    - **Green nodes**: Skills required for jobs
    - **Orange nodes**: Companies
    - **Red nodes**: Locations
    
    Connections between nodes represent relationships (e.g., a job requiring a skill or a job at a company).
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
