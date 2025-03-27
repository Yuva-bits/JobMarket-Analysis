#!/usr/bin/env python3
"""
Prompt Engineering Demo for Job Market RAG API

This script demonstrates how to use prompt engineering techniques to get better results
from the Job Market RAG API. It includes various prompt templates for different use cases
and shows how to structure queries effectively.
"""

import requests
import json
from typing import Dict, List, Any, Optional
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = "http://localhost:8000"

class PromptEngineeringDemo:
    """Demonstrates effective prompt engineering techniques for the Job Market RAG API."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        """Initialize the demo with the API base URL."""
        self.base_url = base_url
        logger.info(f"Initialized Prompt Engineering Demo with API at {base_url}")
    
    def check_api_status(self) -> bool:
        """Check if the API is available."""
        try:
            response = requests.get(f"{self.base_url}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API is not available: {str(e)}")
            return False
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """Send a question to the /ask endpoint."""
        url = f"{self.base_url}/ask"
        payload = {"question": question}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error asking question: {str(e)}")
            return {"error": str(e)}
    
    def get_skill_network(self, skill: str) -> Dict[str, Any]:
        """Get the network of related skills from the /skill-network endpoint."""
        url = f"{self.base_url}/skill-network"
        payload = {"skill_name": skill}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting skill network: {str(e)}")
            return {"error": str(e)}
    
    def get_career_path(self, current_skills: List[str], target_role: str) -> Dict[str, Any]:
        """Get a career path recommendation from the /career-path endpoint."""
        url = f"{self.base_url}/career-path"
        payload = {"current_skills": current_skills, "target_role": target_role}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting career path: {str(e)}")
            return {"error": str(e)}
    
    def demonstrate_skill_inquiry_prompts(self) -> None:
        """Demonstrate different ways to inquire about skills."""
        prompts = [
            # Basic prompt
            "What skills are needed for a software engineer?",
            
            # More specific prompt with role clarification
            "What technical skills are required for a senior software engineer position?",
            
            # Prompt with industry context
            "What are the most in-demand skills for software engineers in the finance industry?",
            
            # Prompt with comparative element
            "How do the required skills differ between frontend and backend developers?",
            
            # Prompt with specific technology focus
            "What skills complement Python programming in data science roles?"
        ]
        
        logger.info("=== SKILL INQUIRY PROMPT PATTERNS ===")
        for prompt in prompts:
            logger.info(f"\nPrompt: {prompt}")
            response = self.ask_question(prompt)
            logger.info(f"Response: {response.get('answer', 'No answer')}")
            time.sleep(1)  # Be nice to the API
    
    def demonstrate_job_market_prompts(self) -> None:
        """Demonstrate prompts for job market insights."""
        prompts = [
            # General market inquiry
            "What is the current job market like for software engineers?",
            
            # Salary focused inquiry
            "What is the typical salary range for DevOps engineers?",
            
            # Location-based inquiry
            "Which locations have the highest demand for machine learning engineers?",
            
            # Industry trend inquiry
            "What are the emerging job roles in artificial intelligence?",
            
            # Career transition inquiry
            "How can a Java developer transition to a cloud engineering role?"
        ]
        
        logger.info("\n=== JOB MARKET INSIGHT PROMPT PATTERNS ===")
        for prompt in prompts:
            logger.info(f"\nPrompt: {prompt}")
            response = self.ask_question(prompt)
            logger.info(f"Response: {response.get('answer', 'No answer')}")
            time.sleep(1)
    
    def demonstrate_skill_network_patterns(self) -> None:
        """Demonstrate how to use the skill network endpoint effectively."""
        skills = ["Python", "AWS", "DevOps", "Machine Learning", "React"]
        
        logger.info("\n=== SKILL NETWORK QUERY PATTERNS ===")
        for skill in skills:
            logger.info(f"\nQuerying network for skill: {skill}")
            response = self.get_skill_network(skill)
            
            # Process and display the results in a useful way
            if "error" not in response:
                related_skills = response.get("related_skills", [])
                jobs_count = len(response.get("jobs", []))
                
                logger.info(f"Found {jobs_count} jobs requiring {skill}")
                logger.info(f"Top 5 related skills: {', '.join(related_skills[:5]) if related_skills else 'None'}")
                
                # Show how to use this data for further prompting
                if related_skills:
                    prompt = f"How can learning {skill} and {related_skills[0]} together enhance my career opportunities?"
                    logger.info(f"Follow-up prompt: {prompt}")
                    follow_up = self.ask_question(prompt)
                    logger.info(f"Response: {follow_up.get('answer', 'No answer')}")
            else:
                logger.info(f"Error: {response.get('error')}")
            
            time.sleep(1)
    
    def demonstrate_career_path_patterns(self) -> None:
        """Demonstrate effective ways to use the career path endpoint."""
        scenarios = [
            {"current_skills": ["Python", "SQL"], "target_role": "Data Scientist"},
            {"current_skills": ["JavaScript", "HTML", "CSS"], "target_role": "Full Stack Developer"},
            {"current_skills": ["AWS", "Linux"], "target_role": "DevOps Engineer"},
            {"current_skills": ["Java", "Spring"], "target_role": "Cloud Engineer"},
            {"current_skills": ["Python", "TensorFlow"], "target_role": "Machine Learning Engineer"}
        ]
        
        logger.info("\n=== CAREER PATH QUERY PATTERNS ===")
        for scenario in scenarios:
            current = ", ".join(scenario["current_skills"])
            target = scenario["target_role"]
            
            logger.info(f"\nScenario: From {current} to {target}")
            response = self.get_career_path(scenario["current_skills"], scenario["target_role"])
            
            # Process and display the results
            if "error" not in response:
                missing_skills = response.get("missing_skills", [])
                
                if missing_skills:
                    logger.info(f"Missing skills: {', '.join(missing_skills)}")
                    
                    # Show how to use this for a follow-up prompt
                    skills_to_ask = ", ".join(missing_skills[:2]) if len(missing_skills) > 1 else missing_skills[0]
                    prompt = f"What's the best way to learn {skills_to_ask} for a {target} role?"
                    logger.info(f"Follow-up prompt: {prompt}")
                    follow_up = self.ask_question(prompt)
                    logger.info(f"Response: {follow_up.get('answer', 'No answer')}")
                else:
                    logger.info("No missing skills identified.")
                    prompt = f"What advanced skills would make me stand out as a {target}?"
                    logger.info(f"Alternative prompt: {prompt}")
                    follow_up = self.ask_question(prompt)
                    logger.info(f"Response: {follow_up.get('answer', 'No answer')}")
            else:
                logger.info(f"Error: {response.get('error')}")
            
            time.sleep(1)
    
    def run_full_demo(self) -> None:
        """Run the complete prompt engineering demonstration."""
        if not self.check_api_status():
            logger.error("API is not available. Please start the API server first.")
            return
        
        logger.info("Starting Prompt Engineering Demonstration")
        logger.info("=======================================")
        
        # Run all demonstrations
        self.demonstrate_skill_inquiry_prompts()
        self.demonstrate_job_market_prompts()
        self.demonstrate_skill_network_patterns()
        self.demonstrate_career_path_patterns()
        
        logger.info("\n=======================================")
        logger.info("Prompt Engineering Demonstration Complete")

if __name__ == "__main__":
    demo = PromptEngineeringDemo()
    demo.run_full_demo() 