import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
from neo4j import GraphDatabase
import difflib
import re
from langchain_huggingface import HuggingFaceEndpoint
import requests
from urllib.parse import urljoin

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleEmbeddings:
    """A simple text embedding model using basic frequency vectors."""
    
    def __init__(self):
        """Initialize the embeddings model."""
        logger.info("Initialized SimpleEmbeddings model")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding."""
        if text is None:
            return ""
        text = str(text).lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        return text
    
    def _text_to_vector(self, text: str, vector_size: int = 100) -> np.ndarray:
        """Convert text to a frequency vector."""
        text = self._preprocess_text(text)
        if not text:
            return np.zeros(vector_size)
        
        # Simple word/character frequency approach
        tokens = text.split()
        vector = np.zeros(vector_size)
        
        for i, token in enumerate(tokens):
            # Use absolute value of hash to ensure positive index
            idx = abs(hash(token)) % vector_size
            vector[idx] += 1 / (i + 1)  # Weigh earlier tokens more
        
        # Normalize to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        vec1 = self._text_to_vector(text1)
        vec2 = self._text_to_vector(text2)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        return float(dot_product)  # Convert numpy float to Python float


class JobRAGSystem:
    """A RAG system for retrieving and generating answers about jobs."""
    
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, api_token=None):
        """Initialize the RAG system."""
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.embeddings_model = SimpleEmbeddings()
        self.llm = self._initialize_llm(api_token)
        self.driver = self._initialize_neo4j()
        
    def _initialize_neo4j(self):
        """Initialize Neo4j connection."""
        try:
            driver = GraphDatabase.driver(self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password))
            with driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"Successfully connected to Neo4j database with {count} nodes.")
            return driver
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    def _initialize_llm(self, api_token=None):
        """Initialize the language model."""
        # Use provided token or get from environment variables
        huggingface_api_token = api_token or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        
        if huggingface_api_token:
            # Verify token by making a simple API call
            headers = {"Authorization": f"Bearer {huggingface_api_token}"}
            try:
                response = requests.get(
                    "https://api-inference.huggingface.co/models/google/flan-t5-base",
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.info("Hugging Face token verified successfully. Using Hugging Face model.")
                    # Pass parameters explicitly, not in model_kwargs
                    return HuggingFaceEndpoint(
                        endpoint_url="https://api-inference.huggingface.co/models/google/flan-t5-base",
                        huggingfacehub_api_token=huggingface_api_token,
                        max_new_tokens=250,  # Specified explicitly
                        temperature=0.7      # Specified explicitly
                    )
                else:
                    logger.error(f"Failed to verify Hugging Face API token. Status code: {response.status_code}")
                    logger.info("Falling back to MockLLM")
                    return MockLLM()
            except Exception as e:
                logger.error(f"Error verifying Hugging Face token: {str(e)}")
                logger.info("Falling back to MockLLM")
                return MockLLM()
        else:
            logger.info("No Hugging Face API token provided. Using MockLLM")
            return MockLLM()
    
    def _fetch_jobs(self):
        """Fetch all jobs from Neo4j and enhance their titles."""
        with self.driver.session() as session:
            result = session.run("MATCH (j:Job) RETURN j")
            jobs = [record["j"] for record in result]
            
            # Enhance job titles
            enhanced_jobs = []
            for job in jobs:
                job_id = job.get("id", "")
                job_title = job.get("title", "")
                job_description = job.get("description", "")
                company = job.get("company", "Unknown company")
                location = job.get("location", "Unknown location")
                
                # If title is a hash or empty, create a better title
                if not job_title or job_title.isdigit() or len(job_title) < 5:
                    if job_description:
                        first_sentence = job_description.split('.')[0]
                        if len(first_sentence) > 50:
                            enhanced_title = first_sentence[:50] + "..."
                        else:
                            enhanced_title = first_sentence
                    elif company and location:
                        enhanced_title = f"{company} position in {location}"
                    elif company:
                        enhanced_title = f"Position at {company}"
                    else:
                        enhanced_title = f"Job #{job_id}"
                    
                    # Update the job dictionary with enhanced title
                    job_dict = dict(job)
                    job_dict["enhanced_title"] = enhanced_title.strip()
                    enhanced_jobs.append(job_dict)
                else:
                    job_dict = dict(job)
                    job_dict["enhanced_title"] = job_title
                    enhanced_jobs.append(job_dict)
            
            return enhanced_jobs
    
    def _fetch_skills(self):
        """Fetch all skills from Neo4j."""
        with self.driver.session() as session:
            result = session.run("MATCH (s:Skill) RETURN s")
            skills = [record["s"] for record in result]
            return skills
            
    def search_jobs(self, query, num_results=3):
        """Search for jobs using embedding similarity."""
        jobs = self._fetch_jobs()
        similarities = []
        
        # Fix job title handling
        for job in jobs:
            job_id = job.get("id", "")
            job_title = job.get("title", "")
            job_description = job.get("description", "")
            company = job.get("company", "Unknown company")
            location = job.get("location", "Unknown location")
            
            # If job title is a numeric string (hash) or empty, create a better title
            if not job_title or job_title.isdigit() or len(job_title) < 5:
                # Construct a better title from description or company info
                if job_description:
                    # Extract the first sentence or up to 50 chars from description
                    first_sentence = job_description.split('.')[0]
                    if len(first_sentence) > 50:
                        job_title = first_sentence[:50] + "..."
                    else:
                        job_title = first_sentence
                elif company and location:
                    job_title = f"{company} position in {location}"
                elif company:
                    job_title = f"Position at {company}"
                else:
                    job_title = f"Job #{job_id}"
                
                # Clean up the title
                job_title = job_title.strip()
                if job_title.isdigit() or not job_title:
                    job_title = f"Job #{job_id} at {company if company else 'Unknown Company'}"
            
            # Create a document that combines all job information
            job_text = f"{job_title} {job_description} {company} {location}"
            similarity = self.embeddings_model.similarity(query, job_text)
            similarities.append((job, float(similarity), job_title))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [(job, sim, title) for job, sim, title in similarities[:num_results]]
    
    def search_skills(self, query, num_results=5):
        """Search for skills using embedding similarity."""
        skills = self._fetch_skills()
        similarities = []
        
        for skill in skills:
            skill_name = skill.get("name", "Unknown Skill")
            similarity = self.embeddings_model.similarity(query, skill_name)
            similarities.append((skill, float(similarity), skill_name))
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [(skill, sim, name) for skill, sim, name in similarities[:num_results]]
        
    def find_career_path(self, from_job_query, to_job_query):
        """Find a career path between two job types."""
        try:
            logger.info(f"Finding career path from '{from_job_query}' to '{to_job_query}'")
            
            # Improved search for jobs that more closely match the user's query
            from_jobs = self.search_jobs(from_job_query, num_results=3)
            to_jobs = self.search_jobs(to_job_query, num_results=3)
            
            if not from_jobs or not to_jobs:
                return "I couldn't find matching jobs for your query."
            
            # Filter for better job matches
            # Only consider jobs that have a reasonable similarity score and title match
            from_jobs = [job for job, sim, title in from_jobs 
                         if sim > 0.3 and (from_job_query.lower() in title.lower() or title.lower() in from_job_query.lower())]
            to_jobs = [job for job, sim, title in to_jobs 
                       if sim > 0.3 and (to_job_query.lower() in title.lower() or title.lower() in to_job_query.lower())]
            
            # If no good matches found after filtering, return appropriate message
            if not from_jobs or not to_jobs:
                return f"I couldn't find specific job roles matching '{from_job_query}' and '{to_job_query}'. Please try more common job titles."
            
            # Use the best matching job from each list
            from_job = from_jobs[0]
            to_job = to_jobs[0]
            
            # Get the titles for display (using first job in filtered list)
            from_title = from_job.get("title", from_job_query)
            if not from_title or from_title.isdigit() or len(from_title) < 5:
                from_title = from_job_query
            
            to_title = to_job.get("title", to_job_query)
            if not to_title or to_title.isdigit() or len(to_title) < 5:
                to_title = to_job_query
            
            logger.info(f"Matched from job: {from_title}")
            logger.info(f"Matched to job: {to_title}")
            
            # Find skills for the source job
            with self.driver.session() as session:
                result = session.run(
                    "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE j.id = $job_id RETURN s.name as skill",
                    job_id=from_job.get("id", "")
                )
                from_skills = [record["skill"] for record in result]
                logger.info(f"Skills for {from_title}: {', '.join(from_skills) if from_skills else 'none found'}")
                
                # Find skills for the target job
                result = session.run(
                    "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE j.id = $job_id RETURN s.name as skill",
                    job_id=to_job.get("id", "")
                )
                to_skills = [record["skill"] for record in result]
                logger.info(f"Skills for {to_title}: {', '.join(to_skills) if to_skills else 'none found'}")
            
            # Find common skills
            common_skills = set(from_skills).intersection(set(to_skills))
            logger.info(f"Common skills: {', '.join(common_skills) if common_skills else 'none'}")
            
            if common_skills:
                path_description = f"To transition from {from_title} to {to_title}, you can leverage these common skills: {', '.join(common_skills)}.\n"
                
                # Skills to learn
                skills_to_learn = set(to_skills) - set(from_skills)
                if skills_to_learn:
                    path_description += f"You would need to learn these additional skills: {', '.join(skills_to_learn)}."
                
                return path_description
            else:
                return f"There's no direct skill overlap between {from_title} and {to_title}. You may need to learn {', '.join(to_skills)}."
                
        except Exception as e:
            logger.error(f"Error finding career path: {str(e)}")
            return f"I found some matching positions for {from_job_query} and {to_job_query}, but couldn't create a detailed path between them."
            
    def answer_question(self, question):
        """Answer a question about jobs and skills."""
        # Search for relevant jobs
        relevant_jobs = self.search_jobs(question)
        
        # Search for relevant skills
        relevant_skills = self.search_skills(question)
        
        # Format the context
        context = "Based on the job market information:\n\n"
        
        # Add job information
        if relevant_jobs:
            context += "Relevant jobs:\n"
            for job, sim, title in relevant_jobs:
                company = job.get("company", "Unknown company")
                location = job.get("location", "Unknown location")
                description = job.get("description", "No description available")
                context += f"- {title} at {company} in {location}\n"
                context += f"  Description: {description[:200]}...\n\n"
        
        # Add skill information
        if relevant_skills:
            context += "Relevant skills:\n"
            for skill, sim, name in relevant_skills:
                context += f"- {name}\n"
        
        # Generate prompt for LLM
        prompt = f"""
        {context}
        
        Question: {question}
        Answer:
        """
        
        # Generate answer
        try:
            answer = self.llm.generate([prompt])
            
            # Extract the generated text from the response
            if hasattr(answer, "generations") and answer.generations:
                if answer.generations[0]:
                    return answer.generations[0][0].text
            
            # Fallback for MockLLM or other unexpected return types
            if isinstance(answer, str):
                return answer
            
            # Final fallback
            return f"I couldn't generate a response. Please try again with a different question."
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # Fall back to MockLLM if the Hugging Face call fails
            mock_llm = MockLLM()
            return mock_llm.generate(prompt)

    def close(self):
        """Close Neo4j connection."""
        self.driver.close()

    def get_skill_path(self, current_skills, target_role):
        """
        Find skills needed to transition to a target role based on current skills.
        
        Args:
            current_skills: List of strings representing skills the user already has
            target_role: String representing the target job role
            
        Returns:
            Dictionary containing skill analysis information
        """
        try:
            logger.info(f"Finding skill path from {current_skills} to {target_role}")
            
            # Convert to list if single string is provided
            if isinstance(current_skills, str):
                current_skills = [current_skills]
            
            # Find most similar jobs for the target role
            target_jobs = self.search_jobs(target_role, num_results=3)
            
            if not target_jobs:
                return {
                    "success": False,
                    "message": f"Couldn't find any jobs matching '{target_role}'",
                    "current_skills": current_skills,
                    "target_role": target_role,
                    "required_skills": [],
                    "already_have": [],
                    "skills_to_learn": []
                }
            
            # Get all skills from the top matching jobs
            all_required_skills = []
            for job, sim, title in target_jobs:
                with self.driver.session() as session:
                    result = session.run(
                        "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE j.id = $job_id RETURN s.name as skill",
                        job_id=job.get("id", "")
                    )
                    job_skills = [record["skill"] for record in result]
                    all_required_skills.extend(job_skills)
            
            # Remove duplicates while preserving order
            required_skills = []
            for skill in all_required_skills:
                if skill not in required_skills:
                    required_skills.append(skill)
            
            # Determine which skills the user already has and which they need to learn
            already_have = []
            skills_to_learn = []
            
            for skill in required_skills:
                # Check if any current skill is contained within the required skill (case insensitive)
                if any(current.lower() in skill.lower() or skill.lower() in current.lower() for current in current_skills):
                    already_have.append(skill)
                else:
                    skills_to_learn.append(skill)
            
            # Find most similar jobs for the current skills (for better suggestions)
            most_relevant_job = None
            if current_skills:
                current_jobs = self.search_jobs(" ".join(current_skills), num_results=1)
                if current_jobs:
                    most_relevant_job, _, title = current_jobs[0]
            
            # When creating the result, store full job objects
            target_job_objects = []
            for job, sim, title in target_jobs:
                # Store the full job object instead of just the title
                target_job_objects.append(job)
            
            # Use the full job object for current role too
            current_role_object = most_relevant_job if most_relevant_job else None
            
            # Return comprehensive result
            return {
                "success": True,
                "current_skills": current_skills,
                "target_role": target_role,
                "target_jobs": target_job_objects,  # Using full job objects
                "required_skills": required_skills,
                "already_have": already_have,
                "skills_to_learn": skills_to_learn,
                "current_role": current_role_object  # Using full job object
            }
                
        except Exception as e:
            logger.error(f"Error finding skill path: {str(e)}")
            return {
                "success": False,
                "message": f"Error analyzing skills: {str(e)}",
                "current_skills": current_skills,
                "target_role": target_role
            }


class MockLLM:
    """A mock LLM for testing purposes. Used as fallback if real LLM is not available."""
    
    def __call__(self, prompt: str) -> str:
        """Process the prompt and return a response."""
        if isinstance(prompt, list):
            prompt = prompt[0]  # Handle list input
        return self.generate(prompt)
        
    def generate(self, prompt):
        """Generate text based on the prompt."""
        logger.info("Using MockLLM to generate response")
        
        # Handle case where prompt is a list
        if isinstance(prompt, list):
            prompt = prompt[0]
            
        # Extract the question from the prompt
        question_match = re.search(r'Question: (.*?)\nAnswer:', prompt, re.DOTALL)
        question = question_match.group(1).strip() if question_match else "unknown question"
        
        if "skill" in question.lower() and "demand" in question.lower():
            return "Based on the job market data, the most in-demand skills include Python, AI, and fluent language abilities. These skills appear frequently in job postings across different sectors."
        
        elif "path" in question.lower() or "transition" in question.lower():
            return "To transition between these roles, focus on developing common skills that both positions require. Consider additional training or certifications in the target role's primary skills."
        
        elif "salary" in question.lower() or "pay" in question.lower():
            return "Salary ranges vary by position, location, and experience level. The data shows that specialized technical roles generally offer higher compensation, with entry-level positions starting at competitive rates."
        
        else:
            return "After analyzing the job market data, I found multiple relevant positions matching your query. The skills typically required for these roles include technical expertise and domain knowledge. Consider exploring positions that align with your experience and interests."


def main():
    """Run a simple RAG test."""
    # Load environment variables
    load_dotenv()
    
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    huggingface_api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    
    # Initialize the RAG system
    rag = JobRAGSystem(neo4j_uri, neo4j_user, neo4j_password, huggingface_api_token)
    
    # Print some database information
    logger.info(f"Connected to Neo4j. Database has 6 nodes.")
    
    # Display all jobs in the database
    logger.info("Fetching all jobs in the database:")
    jobs = rag._fetch_jobs()
    for job in jobs:
        job_id = job.get("id", "Unknown ID")
        company = job.get("company", "Unknown company")
        location = job.get("location", "Unknown location")
        
        # Use enhanced title if available
        title = job.get("enhanced_title") or job.get("title", "Unknown title")
        if title.isdigit() or len(title) < 5:
            title = f"Position at {company} in {location}"
        
        logger.info(f"Job: ID={job_id}, Title={title}, Company={company}, Location={location}")
        
        # Get skills for this job
        with rag.driver.session() as session:
            result = session.run(
                "MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) WHERE j.id = $job_id RETURN s.name as skill",
                job_id=job.get("id", "")
            )
            skills = [record["skill"] for record in result]
            if skills:
                logger.info(f"  Required skills: {', '.join(skills)}")
    
    # Display all skills in the database
    logger.info("\nFetching all skills in the database:")
    skills = rag._fetch_skills()
    for skill in skills:
        skill_name = skill.get("name", "Unknown skill")
        logger.info(f"Skill: {skill_name}")
    
    # Run some sample questions
    sample_questions = [
        "What skills are in high demand?",
        "Tell me about software engineering jobs",
        "How can I transition from customer service to software engineering?"
    ]
    
    for question in sample_questions:
        logger.info(f"Question: {question}")
        answer = rag.answer_question(question)
        logger.info(f"Answer: {answer}")
        logger.info("-" * 50)
    
    # Do a career path search
    logger.info("\nFinding career path:")
    path = rag.find_career_path("customer service", "software engineering")
    logger.info(f"Career path: {path}")
    
    # Close the connection
    rag.close()


if __name__ == "__main__":
    main() 