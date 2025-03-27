import autogen
from autogen.agentchat import ConversableAgent
import os

class JD_agent: 
    def __init__(self, jd):
        self.jd = jd
        self.jd_agent = self.create_jd_agent()

    def create_jd_agent(self):
        """Create an agent specialized in jd analysis."""
        config_list = autogen.config_list_from_json("model_config.json")
        return ConversableAgent(
            name="JDAnalyzer",
            system_message="""You are a specialized Job Description(JD) analysis agent. You understand about: 
            Job Market Knowledge Graph Ontology
Below is a comprehensive ontology for creating a knowledge graph from job postings, focusing on the IT sector. This ontology defines the key entities (nodes) and relationships (edges) that will form the backbone of your graph.
Core Entities (Nodes)
1. Job Role

Attributes:

title (string): The specific job title
level (string): Junior, Mid, Senior, Lead, etc.
category (string): Software Development, Data Science, DevOps, etc.
creation_date (date): When the job was posted
salary_range (range): Compensation information if available



2. Skill

Attributes:

name (string): Name of the skill
type (string): Technical, Soft, Domain, etc.
category (string): Programming Language, Framework, Tool, etc.
popularity (float): Frequency in job postings (calculated metric)
emergence_date (date): When this skill first appeared in significant numbers



3. Company

Attributes:

name (string): Company name
industry (string): Primary industry
size (string): Startup, SMB, Enterprise, etc.
location (string): Primary location



4. Education

Attributes:

degree_type (string): Bachelor's, Master's, PhD, Certificate, etc.
field (string): Computer Science, Mathematics, etc.
institution_type (string): University, Bootcamp, Self-taught, etc.



5. Certification

Attributes:

name (string): Name of certification
issuer (string): Issuing organization
validity_period (duration): How long it remains valid



6. Location

Attributes:

name (string): City/Region name
country (string): Country
remote_friendly (boolean): Whether remote work is common for this location



Core Relationships (Edges)
Between Job Role and Skill

REQUIRES (Job Role → Skill)

Attributes:

importance (string): Must-have, Critical, etc.
experience_years (number): Years of experience required
proficiency_level (string): Beginner, Intermediate, Expert




PREFERS (Job Role → Skill)

Attributes:

context (string): Why it's preferred
advantage_level (string): Slight advantage, Significant advantage, etc.




MENTIONS (Job Role → Skill)

Attributes:

context (string): How it was mentioned
frequency (number): How often it appears in the posting





Between Skills

COMPLEMENTS (Skill → Skill)

Attributes:

strength (float): How strongly they complement each other
frequency (number): How often they appear together




PREREQUISITE_FOR (Skill → Skill)

Attributes:

necessity_level (string): Recommended, Required, etc.




ALTERNATIVE_TO (Skill → Skill)

Attributes:

similarity_score (float): How similar their functions are
context (string): In what contexts they're alternatives





Between Job Role and Company

OFFERED_BY (Job Role → Company)

Attributes:

department (string): Department within the company
team_size (number): Size of the team





Between Job Role and Education

REQUIRES_EDUCATION (Job Role → Education)

Attributes:

importance (string): Required, Preferred, etc.
relevant_fields (list): Specific fields mentioned





Between Job Role and Certification

REQUIRES_CERTIFICATION (Job Role → Certification)

Attributes:

importance (string): Required, Preferred, etc.





Between Job Role and Location

LOCATED_IN (Job Role → Location)

Attributes:

remote_option (string): On-site, Hybrid, Remote, etc.





Derived Relationships (Can be inferred)

CAREER_PATH_TO (Job Role → Job Role)

Attributes:

progression_likelihood (float): Calculated probability of progression
typical_transition_time (duration): Average time to move between roles




TRENDING_IN (Skill → Location)

Attributes:

growth_rate (float): Rate of increased demand
time_period (string): Period over which trend is calculated





Implementation Notes

Relationship Extraction Priority:

Focus first on extracting the Job Role → Skill relationships (REQUIRES, PREFERS, MENTIONS)
These form the core of your knowledge graph and provide immediate value


Entity Resolution:

Implement normalization for skill names (e.g., "React.js" vs "ReactJS")
Use company name resolution to handle variations and subsidiaries


Temporal Aspects:

Include timestamps on relationships to track changes over time
This enables temporal analysis of skill demand evolution


Confidence Scores:

Add a confidence attribute to extracted relationships
Particularly important for LLM-based extraction to indicate certainty



This ontology provides a flexible framework that captures the complex relationships in job postings while remaining adaptable to different extraction techniques. It supports the construction of a GraphRAG system that can provide high-accuracy insights, detailed explainability, and robust governance.


            Your tasks include:
            1. Understanding JD content
            2. Extracting key information like skills, experience, education etc required by company 
            3. Categorize information on Skill, Knowledge,attitude, Evidence, Evaluation bases which candidate can add in resume
            Please analyze the provided content and respond with structured insights.""",
            llm_config={"config_list": config_list},
            human_input_mode="NEVER"
        )
    
    def analyze_jd(self): 
        """Analyze jd using the agent."""
        analysis_prompt = f"""
        Please analyze the following resume content and provide insights:
        
        {self.jd}
        
        Please provide:
        1. Categorize information on Knowledge, skill, attitude required by candidate 
        2. Evaluation bases which candidate can add in resume
        """
        
        response = self.jd_agent.generate_reply(
            messages=[{"content": analysis_prompt, "role": "user"}]
        )
        return response