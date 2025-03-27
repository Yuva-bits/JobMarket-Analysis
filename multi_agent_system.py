import os
import autogen
from autogen import ConversableAgent, GroupChat, GroupChatManager
from resume_agent import ResumeAgent
from jd_agent import JD_agent
from job_rag_system import JobRAGSystem

class RAGInterfaceAgent(ConversableAgent):
    """Agent that provides access to the RAG system's knowledge."""
    
    def __init__(self, rag_system, **kwargs):
        self.rag_system = rag_system
        system_message = """I am a knowledge retrieval specialist. I can access our job market database 
        to find relevant information about jobs, skills, career paths, and more. Ask me about specific 
        jobs, skills, or career transitions, and I'll provide accurate information from our database."""
        
        super().__init__(
            name="RAGAgent",
            system_message=system_message,
            human_input_mode="NEVER",
            **kwargs
        )
        
        # Register a function to answer job-related questions
        self.register_reply(
            [ConversableAgent, GroupChat],
            RAGInterfaceAgent._answer_job_question,
            override=True
        )
    
    def _answer_job_question(self, messages, sender, config):
        """Answer job-related questions using the RAG system."""
        # Extract the last message from the conversation
        last_message = messages[-1]["content"]
        
        # Use the RAG system to generate a response
        response = self.rag_system.answer_question(last_message)
        
        return response

class MatchAnalysisAgent(ConversableAgent):
    """Agent that specializes in analyzing matches between resumes and job descriptions."""
    
    def __init__(self, rag_system, **kwargs):
        self.rag_system = rag_system
        system_message = """I am a match analysis specialist. I can compare a candidate's skills and experience 
        with job requirements to identify matches and gaps. I provide insights on how well a candidate fits a 
        job and what skills they might need to develop."""
        
        super().__init__(
            name="MatchAnalyzer",
            system_message=system_message,
            human_input_mode="NEVER",
            **kwargs
        )
        
        # Register a function to analyze matches
        self.register_reply(
            [ConversableAgent, GroupChat],
            MatchAnalysisAgent._analyze_match,
            override=True
        )
    
    def _analyze_match(self, messages, sender, config):
        """Analyze the match between a resume and job description."""
        # In a real implementation, this would extract resume skills and job requirements
        # from the conversation and use the RAG system to analyze the match
        
        # For simplicity, we'll just check if the last message asks for match analysis
        last_message = messages[-1]["content"].lower()
        
        if "match" in last_message or "compare" in last_message or "analyze" in last_message:
            # Extract context (simplified for example)
            resume_skills = []
            job_requirements = []
            
            for msg in messages:
                content = msg.get("content", "").lower()
                if "resume skills:" in content:
                    skills_text = content.split("resume skills:")[1].strip()
                    resume_skills = [s.strip() for s in skills_text.split(",")]
                
                if "job requirements:" in content:
                    reqs_text = content.split("job requirements:")[1].strip()
                    job_requirements = [r.strip() for r in reqs_text.split(",")]
            
            # Use the RAG system to analyze the match if we have both resume and job info
            if resume_skills and job_requirements:
                # In a real implementation, use skill_gap analysis from RAG
                match_percentage = len(set(resume_skills) & set(job_requirements)) / len(job_requirements) * 100 if job_requirements else 0
                return f"""
                Match Analysis Results:
                - Match Percentage: {match_percentage:.1f}%
                - Skills Present: {', '.join(set(resume_skills) & set(job_requirements))}
                - Skills Missing: {', '.join(set(job_requirements) - set(resume_skills))}
                """
            else:
                return "I need both resume skills and job requirements to perform a match analysis."
        
        # If not asking for match analysis, let another agent handle it
        return None

class CareerAdvisorAgent(ConversableAgent):
    """Agent that provides career advice and recommendations."""
    
    def __init__(self, rag_system, **kwargs):
        self.rag_system = rag_system
        system_message = """I am a career advisor. Based on a candidate's skills, experience, and job requirements, 
        I can provide tailored recommendations for career development, skill acquisition, and job application strategies."""
        
        super().__init__(
            name="CareerAdvisor",
            system_message=system_message,
            human_input_mode="NEVER",
            **kwargs
        )
    
    # This agent uses the default reply mechanism since it primarily synthesizes information from other agents

def create_multi_agent_system(rag_system, config_list=None):
    """Create a multi-agent system with specialized agents for resume and job matching."""
    # Use default config if none provided
    if config_list is None:
        config_list = autogen.config_list_from_json("model_config.json")
    
    # Create specialized agents
    resume_analyzer = ResumeAgent("resume_analyzer")
    jd_analyzer = JD_agent("job description")
    rag_interface = RAGInterfaceAgent(rag_system, llm_config={"config_list": config_list})
    match_analyzer = MatchAnalysisAgent(rag_system, llm_config={"config_list": config_list})
    career_advisor = CareerAdvisorAgent(rag_system, llm_config={"config_list": config_list})
    
    # Create a group chat
    group_chat = GroupChat(
        agents=[resume_analyzer, jd_analyzer, rag_interface, match_analyzer, career_advisor],
        messages=[],
        max_round=12
    )
    
    # Create a manager to orchestrate the conversation
    manager = GroupChatManager(groupchat=group_chat, llm_config={"config_list": config_list})
    
    return manager

def analyze_resume_and_job(manager, resume_text, job_description):
    """Use the multi-agent system to analyze a resume and job description."""
    # Formulate the initial prompt
    prompt = f"""
    We need to analyze a resume and job description to provide insights and recommendations.
    
    RESUME TEXT:
    {resume_text[:1500]}...
    
    JOB DESCRIPTION:
    {job_description[:1500]}...
    
    Please work together to:
    1. Extract skills and experience from the resume
    2. Identify requirements and qualifications from the job description
    3. Analyze how well the candidate matches the job
    4. Provide recommendations for the candidate
    
    ResumeAnalyzer should start by extracting key information from the resume.
    """
    
    # Run the multi-agent conversation
    result = manager.initiate_chat(
        message=prompt,
        clear_history=True
    )
    
    return result