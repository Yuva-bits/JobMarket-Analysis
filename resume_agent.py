from autogen.agentchat import ConversableAgent
import fitz  # pymupdf
import os
import autogen

class ResumeAgent:
    def __init__(self, pdf_path):
        """Initialize the ResumeAnalyzer with the PDF path and extract text."""
        self.pdf_path = pdf_path
        self.resume_text = self.extract_pdf_text()
        self.analyzer_agent = self.create_resume_analyzer_agent()

    def extract_pdf_text(self):
        """Extract text from PDF document."""
        try:
            pdf_document = fitz.open(self.pdf_path)
            text = ""
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text += page.get_text()
            pdf_document.close()
            return text
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"

    def create_resume_analyzer_agent(self):
        """Create an agent specialized in resume analysis."""
        config_list = autogen.config_list_from_json("model_config.json")
        return ConversableAgent(
            name="ResumeAnalyzer",
            system_message="""You are a specialized resume analysis agent. Your tasks include:
            1. Understanding resume content
            2. Extracting key information like skills, experience, and education
            3. Providing insights about the candidate's profile
            Please analyze the provided resume content and respond with structured insights.""",
            llm_config={"config_list": config_list},
            human_input_mode="NEVER"
        )

    def analyze_resume(self):
        """Analyze resume using the agent."""
        analysis_prompt = f"""
        Please analyze the following resume content and provide insights:
        
        {self.resume_text}
        
        Please provide:
        1. Key skills identified
        2. Work experience summary
        3. Educational background
        4. Notable achievements
        5. Areas of expertise
        """
        
        response = self.analyzer_agent.generate_reply(
            messages=[{"content": analysis_prompt, "role": "user"}]
        )
        return response