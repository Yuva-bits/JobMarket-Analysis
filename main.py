from fastapi import FastAPI, UploadFile, File, Form, Body
from pydantic import BaseModel
import shutil
import os
import uuid
import logging
import fitz  # PyMuPDF for PDF text extraction
import tempfile
from typing import List, Optional, Dict, Any
import re  # For regular expressions

app = FastAPI()

# Logging configuration to print to console
logging.basicConfig(level=logging.INFO)

# Use system temp directory instead of hardcoded /tmp
TEMP_DIR = tempfile.gettempdir()

# Define request models
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []

def extract_pdf_text(pdf_path):
    """Extract text from PDF document."""
    try:
        pdf_document = fitz.open(pdf_path)
        text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        pdf_document.close()
        return text
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

def extract_resume_info(resume_text):
    """Extract key information from resume text using improved regex patterns."""
    resume_info = {
        "name": "",
        "email": "",
        "phone": "",
        "education": [],
        "skills": [],
        "experience": [],
        "projects": [],
        "certificates": [],
        "languages": []
    }
    
    # Try to extract name (usually prominent at the top)
    name_pattern = r'^([A-Z][a-z]+ [A-Z][a-z]+)'
    name_match = re.search(name_pattern, resume_text.strip())
    if name_match:
        resume_info["name"] = name_match.group(1)
    
    # Extract email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, resume_text)
    if email_match:
        resume_info["email"] = email_match.group(0)
    
    # Extract phone
    phone_pattern = r'(\+\d{1,3}[-\.\s]??)?\(?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{4}'
    phone_match = re.search(phone_pattern, resume_text)
    if phone_match:
        resume_info["phone"] = phone_match.group(0)
    
    # Extract skills (look for common skill section headers and grab text after)
    skills_pattern = r'(?:SKILLS|TECHNICAL SKILLS|CORE COMPETENCIES)[:\s]*(.+?)(?:\n\n|\Z)'
    skills_match = re.search(skills_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    if skills_match:
        skills_text = skills_match.group(1)
        # Split by bullets, commas, or line breaks
        skills = re.split(r'[•,\n]+', skills_text)
        resume_info["skills"] = [skill.strip() for skill in skills if skill.strip()]
    
    # Extract education with improved pattern
    education_section_pattern = r'(?:EDUCATION|ACADEMIC BACKGROUND)[:\s]*(.+?)(?:\n\n(?:PROJECTS|SKILLS|EXPERIENCE|CERTIFICATES)|\Z)'
    education_match = re.search(education_section_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    
    if education_match:
        education_text = education_match.group(1)
        
        # Extract individual education entries with proper formatting
        # Look for patterns like "Degree Program, Institution, Date Range"
        degree_entries = []
        
        # First try to extract by common degree keywords
        degree_keywords = ["Bachelor", "Master", "PhD", "B.S.", "M.S.", "M.B.A.", "B.A.", "M.A.", "B.Tech", "M.Tech"]
        
        current_entry = ""
        for line in education_text.split('\n'):
            if any(keyword in line for keyword in degree_keywords) or re.search(r'\b\d{4}\s*-\s*\d{4}|\b\d{4}\s*-\s*Present', line, re.IGNORECASE):
                if current_entry:
                    degree_entries.append(current_entry.strip())
                current_entry = line
            elif current_entry and line.strip():
                current_entry += " " + line
        
        if current_entry:  # Add the last entry
            degree_entries.append(current_entry.strip())
        
        # If the above didn't work, try a more general approach to split by dates
        if not degree_entries:
            date_pattern = r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)?\s*\d{4}\s*-\s*(?:Present|\d{4})'
            segments = re.split(date_pattern, education_text)
            if len(segments) > 1:
                dates = re.findall(date_pattern, education_text)
                for i, segment in enumerate(segments[:-1]):  # Exclude the last segment which might not have a date
                    if segment.strip() and i < len(dates):
                        degree_entries.append(f"{segment.strip()} {dates[i]}")
        
        # Clean up entries
        cleaned_entries = []
        for entry in degree_entries:
            # Clean up whitespace and special characters
            entry = re.sub(r'\s+', ' ', entry).strip()
            entry = entry.replace('■', '•')
            
            # Structure the entry in a consistent format
            parts = re.split(r'\s{2,}|\t', entry)
            if len(parts) > 1:
                formatted_entry = ' | '.join(parts)
            else:
                formatted_entry = entry
                
            cleaned_entries.append(formatted_entry)
        
        resume_info["education"] = cleaned_entries
    
    # Extract projects with improved pattern
    projects_section_pattern = r'(?:PROJECTS?)[:\s]*(.+?)(?:\n\n(?:EDUCATION|SKILLS|EXPERIENCE|CERTIFICATES)|\Z)'
    projects_match = re.search(projects_section_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    
    if projects_match:
        projects_text = projects_match.group(1)
        
        # Look for project titles and descriptions
        project_entries = []
        current_project = ""
        
        # Split the text by lines
        lines = projects_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check if this is a new project (often has a date or technology stack)
            if re.search(r'\b\d{4}\b|University|College|Technologies?:|React|Python|Java|Node\.js|MongoDB', line):
                if current_project:
                    project_entries.append(current_project.strip())
                current_project = line
            elif current_project and line:
                current_project += " " + line
            
            i += 1
        
        if current_project:  # Add the last project
            project_entries.append(current_project.strip())
        
        # Clean up project entries
        cleaned_projects = []
        for project in project_entries:
            # Clean up whitespace and special characters
            project = re.sub(r'\s+', ' ', project).strip()
            project = project.replace('■', '•')
            
            # Format project entries
            parts = project.split('•')
            if len(parts) > 1:
                title = parts[0].strip()
                details = [p.strip() for p in parts[1:] if p.strip()]
                formatted_project = f"{title}\n" + "\n".join([f"• {detail}" for detail in details])
            else:
                formatted_project = project
                
            cleaned_projects.append(formatted_project)
        
        resume_info["projects"] = cleaned_projects
    
    # Extract certificates
    certificates_pattern = r'(?:CERTIFICATES?|CERTIFICATIONS?)[:\s]*(.+?)(?:\n\n(?:EDUCATION|SKILLS|EXPERIENCE|PROJECTS)|\Z)'
    certificates_match = re.search(certificates_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    
    if certificates_match:
        certificates_text = certificates_match.group(1)
        
        # Split by newlines or bullets
        certificate_entries = re.split(r'[\n•■]+', certificates_text)
        resume_info["certificates"] = [cert.strip() for cert in certificate_entries if cert.strip()]
    
    # Extract experience (look for work experience sections)
    experience_pattern = r'(?:EXPERIENCE|WORK EXPERIENCE|PROFESSIONAL EXPERIENCE)[:\s]*(.+?)(?:\n\n(?:EDUCATION|SKILLS|PROJECTS|CERTIFICATES)|\Z)'
    experience_match = re.search(experience_pattern, resume_text, re.DOTALL | re.IGNORECASE)
    
    if experience_match:
        experience_text = experience_match.group(1)
        
        # Break up by positions - look for dates, companies, or titles
        experience_entries = []
        current_exp = ""
        
        for line in experience_text.split('\n'):
            # Check if this line could be the start of a new experience entry
            if re.search(r'\b\d{4}\b|University|College|Technologies?:|Inc\.|LLC|Ltd\.', line):
                if current_exp:
                    experience_entries.append(current_exp.strip())
                current_exp = line
            elif current_exp and line.strip():
                current_exp += " " + line
        
        if current_exp:  # Add the last entry
            experience_entries.append(current_exp.strip())
        
        # Clean up entries
        resume_info["experience"] = [exp.strip() for exp in experience_entries if exp.strip()]
    
    return resume_info

def analyze_resume(resume_text):
    """Extract information from the resume."""
    return extract_resume_info(resume_text)

def analyze_jd(jd_text, resume_info):
    """Enhanced job description analysis that incorporates the actual resume information."""
    # Simple keyword-based analysis for job description
    keywords = {
        'python': 0, 'java': 0, 'javascript': 0, 'react': 0, 'node': 0, 
        'aws': 0, 'cloud': 0, 'devops': 0, 'docker': 0, 'kubernetes': 0,
        'data': 0, 'analysis': 0, 'machine learning': 0, 'ml': 0, 'ai': 0,
        'frontend': 0, 'backend': 0, 'fullstack': 0, 'full-stack': 0,
        'agile': 0, 'scrum': 0, 'leadership': 0, 'team': 0, 'management': 0,
        'sql': 0, 'database': 0, 'nosql': 0, 'mongodb': 0, 'postgresql': 0,
        'automation': 0, 'ci/cd': 0, 'testing': 0, 'qa': 0
    }
    
    # Count mentions of keywords in job description
    jd_lower = jd_text.lower()
    for keyword in keywords:
        keywords[keyword] = jd_lower.count(keyword)
    
    # Determine job focus areas based on keyword counts
    is_backend = any(k > 0 for k in [keywords['python'], keywords['java'], keywords['backend']])
    is_frontend = any(k > 0 for k in [keywords['javascript'], keywords['react'], keywords['frontend']])
    is_fullstack = is_backend and is_frontend or keywords['fullstack'] > 0 or keywords['full-stack'] > 0
    is_data = any(k > 0 for k in [keywords['data'], keywords['analysis'], keywords['machine learning'], keywords['ml']])
    is_devops = any(k > 0 for k in [keywords['devops'], keywords['aws'], keywords['cloud'], keywords['docker']])
    is_leadership = any(k > 0 for k in [keywords['leadership'], keywords['management'], keywords['team']])
    
    # Extract candidate info from resume (use defaults if we couldn't extract)
    candidate_name = resume_info.get("name", "John Doe")
    candidate_email = resume_info.get("email", "john.doe@example.com")
    candidate_phone = resume_info.get("phone", "(555) 123-4567")
    
    # Filter and prioritize candidate skills based on job description
    candidate_skills = resume_info.get("skills", ["Python", "JavaScript", "Communication"])
    prioritized_skills = []
    other_skills = []
    
    # Categorize skills based on job requirements
    for skill in candidate_skills:
        skill_lower = skill.lower()
        if any(keyword in skill_lower for keyword in keywords if keywords[keyword] > 0):
            prioritized_skills.append(skill)
        else:
            other_skills.append(skill)
    
    # Combine prioritized skills first, then others
    ordered_skills = prioritized_skills + other_skills
    
    # Process education entries from the resume for better formatting
    education_entries = resume_info.get("education", ["Bachelor's Degree in Computer Science"])
    
    # Format experience entries from the resume
    experience_entries = resume_info.get("experience", 
        ["Software Engineer with experience in Python development",
         "Data analysis and visualization using modern tools"])
    
    # Format project entries from the resume
    project_entries = resume_info.get("projects", 
        ["Project: Development of web applications using modern frameworks"])
    
    # Begin building the tailored resume with a summary of what was extracted
    extracted_info = """
# EXTRACTION SUMMARY

The following information was extracted from your resume:

"""
    if candidate_name != "John Doe":
        extracted_info += f"- **Name:** {candidate_name}\n"
    else:
        extracted_info += "- **Name:** Could not extract\n"
        
    if candidate_email != "john.doe@example.com":
        extracted_info += f"- **Email:** {candidate_email}\n"
    else:
        extracted_info += "- **Email:** Could not extract\n"
        
    if candidate_phone != "(555) 123-4567":
        extracted_info += f"- **Phone:** {candidate_phone}\n"
    else:
        extracted_info += "- **Phone:** Could not extract\n"
    
    # List extracted skills
    extracted_info += "\n**Skills extracted:**\n"
    if candidate_skills:
        for skill in candidate_skills:
            extracted_info += f"- {skill}\n"
    else:
        extracted_info += "- No skills could be extracted\n"
    
    # List extracted education
    extracted_info += "\n**Education extracted:**\n"
    if education_entries and education_entries[0] != "Bachelor's Degree in Computer Science":
        for edu in education_entries:
            extracted_info += f"- {edu}\n"
    else:
        extracted_info += "- No education details could be extracted\n"
    
    # List extracted experience
    extracted_info += "\n**Experience entries extracted:**\n"
    if experience_entries and experience_entries[0] != "Software Engineer with experience in Python development":
        for exp in experience_entries:
            # Truncate long experience entries for readability
            exp_truncated = exp[:100] + "..." if len(exp) > 100 else exp
            extracted_info += f"- {exp_truncated}\n"
    else:
        extracted_info += "- No experience details could be extracted\n"
    
    # List extracted projects
    extracted_info += "\n**Projects extracted:**\n"
    if project_entries and project_entries[0] != "Project: Development of web applications using modern frameworks":
        for proj in project_entries:
            # Truncate long project descriptions for readability
            proj_truncated = proj[:100] + "..." if len(proj) > 100 else proj
            extracted_info += f"- {proj_truncated}\n"
    else:
        extracted_info += "- No project details could be extracted\n"
    
    # List key job requirements found
    extracted_info += "\n**Key job requirements identified:**\n"
    top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:8]  # Top 8 keywords
    for keyword, count in top_keywords:
        if count > 0:
            extracted_info += f"- {keyword.title()} (mentioned {count} times)\n"
    
    extracted_info += "\n---\n\n"

    # Now build the actual tailored resume - completely separate from the extraction summary
    tailored_resume = f"""
# TAILORED RESUME

## {candidate_name}
**Email:** {candidate_email} | **Phone:** {candidate_phone}

---

## PROFESSIONAL SUMMARY
Results-driven {"full stack" if is_fullstack else "software"} engineer with experience in {"data analysis and insights" if is_data else "software development"}. {"Specializing in data science and machine learning" if is_data else "Specializing in " + ("cloud infrastructure and DevOps" if is_devops else "web application development")}. Focused on delivering high-quality solutions that meet business requirements.

---

## SKILLS

**Programming & Technical:**
"""
    # Add skills, highlighting those that match the job description (limited to 5 skills with checkmarks)
    skill_count = 0
    added_skills = set()
    
    # First add prioritized skills
    for skill in prioritized_skills:
        if skill_count < 5 and skill not in added_skills:
            tailored_resume += f"- **{skill}** ✓\n"
            added_skills.add(skill)
            skill_count += 1
    
    # Then add other skills to fill out the list
    for skill in other_skills:
        if skill_count < 8 and skill not in added_skills:
            tailored_resume += f"- {skill}\n"
            added_skills.add(skill)
            skill_count += 1
    
    # Add soft skills section if leadership is mentioned
    if is_leadership:
        tailored_resume += """
**Leadership & Soft Skills:**
- Team Management
- Project Coordination
- Cross-functional Collaboration
- Strategic Planning
"""
    
    # Education section - professionally formatted
    tailored_resume += """
## EDUCATION
"""
    
    # Format education entries properly
    if education_entries and education_entries[0] != "Bachelor's Degree in Computer Science":
        for edu in education_entries:
            # Split the entry into components if possible
            components = re.split(r'\s*\|\s*', edu)
            
            if len(components) >= 2:
                # If properly formatted with pipe separators
                degree = components[0]
                institution = components[1] if len(components) > 1 else ""
                date_location = components[2] if len(components) > 2 else ""
                
                tailored_resume += f"### {degree}\n"
                if institution:
                    tailored_resume += f"**{institution}**"
                    if date_location:
                        tailored_resume += f" | {date_location}\n"
                    else:
                        tailored_resume += "\n"
            else:
                # Try to parse the education string
                parts = edu.split(' | ' if ' | ' in edu else ' - ' if ' - ' in edu else None)
                
                if parts and len(parts) > 1:
                    degree_part = parts[0]
                    rest = ' | '.join(parts[1:])
                    
                    tailored_resume += f"### {degree_part}\n"
                    tailored_resume += f"**{rest}**\n"
                else:
                    # If we can't parse it clearly, just output as is
                    tailored_resume += f"### {edu}\n"
            
            # Add a small space between education entries
            tailored_resume += "\n"
    else:
        tailored_resume += "*No education details available.*\n"
    
    # Experience section using actual resume data
    tailored_resume += """
## WORK EXPERIENCE
"""
    
    # Clean and format experience entries, preventing duplication
    processed_experience_entries = []
    for exp in experience_entries:
        if exp != "Software Engineer with experience in Python development" and exp != "Data analysis and visualization using modern tools":
            # Clean up and normalize experience entry
            exp_clean = re.sub(r'\s+', ' ', exp).strip()
            
            # Extract the job title or first line
            lines = exp_clean.split('\n')
            job_title = lines[0] if lines else exp_clean
            
            # Only add if not already processed (avoid duplicates)
            if job_title not in [pe.split('\n')[0] for pe in processed_experience_entries]:
                processed_experience_entries.append(exp_clean)
    
    # Add formatted experience entries
    if processed_experience_entries:
        for exp_index, exp_clean in enumerate(processed_experience_entries):
            # Try to extract job title
            lines = exp_clean.split('\n')
            job_title = lines[0] if lines else exp_clean
            
            tailored_resume += f"\n### {job_title}\n"
            
            # Add bullet points focused on the job's requirements
            bullet_points_added = 0
            
            # Add matching experience bullet points
            exp_lower = exp_clean.lower()
            if is_backend and any(kw in exp_lower for kw in ['backend', 'python', 'java', 'api', 'server']):
                tailored_resume += "- Developed backend systems and APIs to support business requirements\n"
                bullet_points_added += 1
                
            if is_frontend and any(kw in exp_lower for kw in ['frontend', 'ui', 'user interface', 'javascript', 'react']):
                tailored_resume += "- Created responsive user interfaces and optimized frontend performance\n"
                bullet_points_added += 1
                
            if is_data and any(kw in exp_lower for kw in ['data', 'analysis', 'analytics', 'insight']):
                tailored_resume += "- Analyzed complex datasets and created data-driven insights\n"
                bullet_points_added += 1
                
            if is_devops and any(kw in exp_lower for kw in ['devops', 'cloud', 'aws', 'infrastructure']):
                tailored_resume += "- Implemented cloud infrastructure and automated deployment pipelines\n"
                bullet_points_added += 1
                
            if is_leadership and any(kw in exp_lower for kw in ['lead', 'manage', 'team', 'direct']):
                tailored_resume += "- Led teams and coordinated project deliverables to meet business objectives\n"
                bullet_points_added += 1
            
            # If none of the specific areas matched, add a generic bullet point
            if bullet_points_added == 0:
                tailored_resume += "- Applied technical expertise to successfully deliver business solutions\n"
    else:
        tailored_resume += "\n*No detailed work experience available.*\n"
    
    # Projects section - professionally formatted
    tailored_resume += """
## PROJECTS
"""
    
    # Format project entries
    if project_entries and project_entries[0] != "Project: Development of web applications using modern frameworks":
        for project in project_entries:
            # Split the project entry by newlines to separate title from bullet points
            project_lines = project.split('\n')
            
            if len(project_lines) > 0:
                # First line is typically the project title and technologies
                project_title = project_lines[0]
                
                # Try to extract the project name and technology stack
                title_parts = project_title.split(' | ')
                if len(title_parts) > 1:
                    project_name = title_parts[0]
                    tech_stack = title_parts[1]
                    tailored_resume += f"### {project_name}\n"
                    tailored_resume += f"**Technologies:** {tech_stack}\n\n"
                else:
                    # Check if there's a technology list after the project name
                    tech_match = re.search(r'(.*?)\s*(\||–|-)\s*(React|Node\.js|Python|Java|MongoDB|TensorFlow|.*?)\s*$', project_title)
                    if tech_match:
                        project_name = tech_match.group(1).strip()
                        tech_stack = tech_match.group(3).strip()
                        tailored_resume += f"### {project_name}\n"
                        tailored_resume += f"**Technologies:** {tech_stack}\n\n"
                    else:
                        tailored_resume += f"### {project_title}\n\n"
                
                # Add bullet points for project details
                for i in range(1, len(project_lines)):
                    line = project_lines[i].strip()
                    if line:
                        if line.startswith('•') or line.startswith('-'):
                            tailored_resume += f"{line}\n"
                        else:
                            tailored_resume += f"- {line}\n"
            else:
                # If we couldn't parse the project, just add it as is
                tailored_resume += f"### {project}\n\n"
            
            # Add spacing between projects
            tailored_resume += "\n"
    else:
        tailored_resume += "*No project details available.*\n"
    
    # Format certificates section if available
    certificates = resume_info.get("certificates", [])
    if certificates:
        tailored_resume += """
## CERTIFICATIONS
"""
        for cert in certificates:
            cert_clean = cert.strip()
            if cert_clean:
                # Check if certificate has a issuer or details
                parts = cert_clean.split(',')
                if len(parts) > 1:
                    cert_name = parts[0].strip()
                    cert_details = ', '.join(parts[1:]).strip()
                    tailored_resume += f"- **{cert_name}** | {cert_details}\n"
                else:
                    tailored_resume += f"- {cert_clean}\n"
    
    # Extract top 5 keywords to highlight as required skills
    top_skills = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
    top_skills = [skill[0].title() for skill in top_skills if skill[1] > 0]
    
    # Add default skills if we didn't find any in the job description
    if len(top_skills) < 3:
        top_skills.extend(["Python", "JavaScript", "Data Analysis", "Cloud Computing", "Agile"])
    
    # Combine the extraction summary and tailored resume
    final_content = extracted_info + tailored_resume
    
    return {
        "content": final_content,
        "required_skills": top_skills
    }

@app.post("/upload-resume-jd")
async def upload_resume_jd(file: UploadFile = File(...), job_description: str = Form(...)):
    # Generate a unique filename
    file_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{file_id}.pdf")

    # Save the file temporarily
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Log the received job description
    if(job_description and file_id): 
        logging.info("Content received")
    else: 
        return "No Content Received"

    # Extract text from resume
    resume_text = extract_pdf_text(file_path)
    
    # Basic analysis - extract information from resume
    resume_info = analyze_resume(resume_text)
    
    # Generate tailored resume using real resume information
    jd_analysis = analyze_jd(job_description, resume_info)

    logging.info(f"Analysis complete for resume ID: {file_id}")

    return {
        "resume_id": file_id,
        "message": "Resume and Job Description processed successfully",
        "tailored_resume": jd_analysis['content']
    }

# Add a simple chat endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint that accepts message and history fields in the JSON payload."""
    message = request.message
    history = request.history
    
    return {
        "response": f"You asked: '{message}'. I'm a simple chat assistant. In the full implementation, I would provide advice about resumes and job applications based on your query."
    }
