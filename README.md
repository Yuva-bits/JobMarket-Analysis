# Job Market Intelligence System
A comprehensive platform for job market analysis, skill gap identification, and career planning

## Overview
The Job Market Intelligence System is an advanced application that leverages Retrieval-Augmented Generation (RAG) technology to provide intelligent insights about the job market. Built on a Neo4j graph database of job listings and skills, this system helps users analyze resumes, match candidates to job descriptions, explore skill relationships, and plan career transitions.

## Key Features
- **Resume & Job Matching:** Upload a resume and paste a job description to get a detailed analysis of skill matches and gaps
- **Interactive AI Chat:** Ask questions about the job market, skills, and career paths using the RAG-powered assistant
- **Job Search by Skill:** Find relevant job positions based on specific skills or technologies
- **Career Path Planning**:** Get personalized recommendations for transitioning between different roles
- **Skill Network Visualization:** Explore an interactive network graph showing relationships between jobs and skills

## Technology Stack
- **Backend:** Python with Neo4j graph database
- **Frontend:** Streamlit for interactive user interface
- **NLP/AI:** Hugging Face models for natural language processing
- **Data Storage:** Neo4j graph database to represent job and skill relationships
- **RAG System:** Custom implementation combining graph retrieval with language model generation

# Setup and Installation
**Prerequisites**
- Python 3.9+
- Neo4j database (local or remote)
- Hugging Face API token (optional, can fall back to MockLLM)

**Environment Setup**
1. Clone the repository:
```bash
   git clone https://github.com/yourusername/job-market-intelligence.git
   cd job-market-intelligence
```
2. Install required packages:
```bash
   pip install -r requirements.txt
```
3. Configure the .env file with your credentials:
```
   NEO4J_URI=bolt://localhost:7688
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password_here
   HUGGINGFACEHUB_API_TOKEN=your_token_here
   API_URL=http://localhost:8000
```

**Data Setup**
1. Load job data from JSON:
```bash
   python load_all_jobs.py
```
2. Build the Neo4j graph:
```bash
   python build_neo4j_graph.py
```
3. Verify the Neo4j graph:
```bash
   python check_neo4j.py
```
4. Fix any database values if needed:
```bash
   python fix_database_values.py
```

**Running the Application**
1. Test the RAG system:
```bash
   python job_rag_system.py
```
2. Start the backend:
```bash
   python integrated_app.py
```
3. Launch the Streamlit frontend:
```bash
   streamlit run streamlit_frontend.py
```
## System Architecture
The system consists of several key components:
1. **Job Data Processing:** Scripts to extract and process job postings
2. **Neo4j Graph Database:** Stores jobs, skills, and their relationships
3. **RAG System:** Combines graph database retrieval with language model generation
4. **Streamlit UI:** User-friendly interface for interacting with the system

## Usage Guide
**Resume & Job Matching**
Upload a PDF resume and paste a job description to receive:
- Skills extracted from your resume
- Analysis of the job requirements
- Percentage match between your skills and job requirements
- Skills you already have and skills you need to develop
- Similar jobs from the database

**Job Search by Skill**
Enter a skill (e.g., "Python", "AWS", "Machine Learning") to find:
- Relevant jobs requiring that skill
- Detailed job information with company and location
- Similarity scores showing relevance

**Career Path Planning**
Plan transitions between roles:
- Visualize the path from your current role to target role
- Identify transferable skills
- Get recommendations for skills to develop
- See example career paths with detailed advice

**Skill Network Visualization**
Explore relationships between skills and jobs:
- Interactive network graph of jobs and skills
- Color-coded skill categories
- Size indicates demand for skills
- Hover for detailed information

## Project Structure
`job_rag_system.py`: Core RAG system implementation
`load_all_jobs.py`: Load job data from JSON
`build_neo4j_graph.py`: Build Neo4j graph from SQLite database
`fix_database_values.py`: Fix data quality issues in database
`check_neo4j.py`: Verify database contents
`streamlit_frontend.py`: Streamlit UI application
`integrated_app.py`: FastAPI backend (optional)
`resume_agent.py`: Agent for resume analysis
`jd_agent.py`: Agent for job description analysis

## Future Enhancements
- Integration with live job APIs for real-time data
- Personalized learning path recommendations
- Salary insights and negotiations assistance
- Company culture matching
- Industry trends analysis

## Author
Darshini Balamurali
Eshwara Pandiyan
Joel Thomas Joe
Kirtan Prajapati
Saiteja Rudroju
Yuvashree Senthilmurugan
