import streamlit as st
import requests
import time
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import markdown
import re

# Configure page
st.set_page_config(
    page_title="AI Resume Tailoring",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoints
API_ENDPOINT = "http://localhost:8000/upload-resume-jd"
CHAT_ENDPOINT = "http://localhost:8000/chat"  # Assuming this is your chat endpoint

# App title
st.title("🚀 AI Resume Tailoring System")
st.markdown("### Transform your resume to match job requirements using multi-agent AI")

# Create tabs for the different functionalities
tab1, tab2 = st.tabs(["Resume Tailoring", "Chat Assistant"])

# Session state initialization
if "resume_file" not in st.session_state:
    st.session_state.resume_file = None
if "processing" not in st.session_state:
    st.session_state.processing = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_input" not in st.session_state:
    st.session_state.chat_input = ""
if "tailored_resume_text" not in st.session_state:
    st.session_state.tailored_resume_text = ""
if "extraction_summary" not in st.session_state:
    st.session_state.extraction_summary = ""

def extract_tailored_resume(full_content):
    """Extract just the tailored resume part from the combined content."""
    parts = full_content.split("# TAILORED RESUME")
    if len(parts) > 1:
        return "# TAILORED RESUME" + parts[1]
    return full_content  # fallback to full content if separation not found

def markdown_to_pdf(markdown_text, filename="Tailored_Resume.pdf"):
    """Convert markdown text to PDF using ReportLab with improved professional formatting."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=30, bottomMargin=30, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    
    # Create professional styles for resume
    styles.add(ParagraphStyle(
        name='ResumeTitle',
        parent=styles['Heading1'],
        fontSize=22,
        spaceAfter=16,
        spaceBefore=20,
        alignment=1,  # Center alignment
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=10,
        spaceBefore=16,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
        borderColor=colors.darkblue,
        borderRadius=None
    ))
    
    styles.add(ParagraphStyle(
        name='SubSectionHeader',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        spaceBefore=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='ContactInfo',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,  # Center
        spaceAfter=12,
    ))
    
    styles.add(ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8,
        leading=14  # Line spacing
    ))
    
    styles.add(ParagraphStyle(
        name='BulletPoint',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leftIndent=20,
        firstLineIndent=0,
        leading=14,
    ))
    
    styles.add(ParagraphStyle(
        name='TechnologyStack',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        textColor=colors.darkslategray,
        fontName='Helvetica-Oblique'
    ))
    
    # Process markdown to create paragraph elements
    elements = []
    lines = markdown_text.split('\n')
    
    # Skip extraction summary if present
    in_resume_section = False
    if "# TAILORED RESUME" in markdown_text:
        for i, line in enumerate(lines):
            if line.strip() == "# TAILORED RESUME":
                in_resume_section = True
                lines = lines[i:]  # Only include lines from the resume section
                break
    
    # Track current section for better context
    current_section = None
    in_skills_section = False
    in_experience_section = False
    in_education_section = False
    in_projects_section = False
    in_certifications_section = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
        
        # Handle title (TAILORED RESUME)
        if line.startswith('# '):
            text = line[2:]
            elements.append(Paragraph(text, styles["ResumeTitle"]))
            elements.append(Spacer(1, 10))
            
        # Handle contact info line
        elif i > 0 and line.startswith('**') and ('Email' in line or '@' in line):
            # Clean up formatting of contact info line
            text = line.replace('**', '<b>', 1)
            text = text.replace('**', '</b>', 1)
            text = text.replace(' | ', ' &nbsp;&nbsp;|&nbsp;&nbsp; ')
            elements.append(Paragraph(text, styles["ContactInfo"]))
            elements.append(Spacer(1, 12))
            
        # Handle section headers (SKILLS, EXPERIENCE, etc.)
        elif line.startswith('## '):
            text = line[3:].upper()  # Make section headers uppercase for professional look
            current_section = text
            
            # Add a horizontal line before each section except the first one
            if elements:
                elements.append(Spacer(1, 5))
                from reportlab.platypus import HRFlowable
                elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=5, spaceAfter=10))
                elements.append(Spacer(1, 5))
            
            # Set section flags for context
            in_skills_section = 'SKILL' in text.upper()
            in_experience_section = 'EXPERIENCE' in text.upper() or 'WORK' in text.upper()
            in_education_section = 'EDUCATION' in text.upper()
            in_projects_section = 'PROJECT' in text.upper()
            in_certifications_section = 'CERTIF' in text.upper()
            
            elements.append(Paragraph(text, styles["SectionHeader"]))
            elements.append(Spacer(1, 6))
            
        # Handle job titles, education degrees, or project titles
        elif line.startswith('### '):
            text = line[4:]
            elements.append(Paragraph(text, styles["SubSectionHeader"]))
            
        # Handle skills with checkmarks or bolded items
        elif line.startswith('- **') and '✓' in line:
            text = line[2:].replace('**', '<b>', 1).replace('**', '</b>', 1)
            text = '• ' + text.replace('✓', '<font color="green">✓</font>')
            elements.append(Paragraph(text, styles["BulletPoint"]))
            
        # Handle technology stack or institution lines
        elif line.startswith('**Technologies:**') or (in_education_section and line.startswith('**')):
            text = line.replace('**', '<b>', 1).replace('**', '</b>', 1)
            if 'Technologies' in text:
                elements.append(Paragraph(text, styles["TechnologyStack"]))
            else:
                elements.append(Paragraph(text, styles["NormalText"]))
            
        # Handle regular bullet points
        elif line.startswith('- '):
            text = '• ' + line[2:]
            elements.append(Paragraph(text, styles["BulletPoint"]))
            
        # Handle skill category headers (e.g., "Programming & Technical:")
        elif line.startswith('**') and 'Skills' in line:
            text = '<b>' + line.replace('**', '') + '</b>'
            elements.append(Paragraph(text, styles["NormalText"]))
            
        # Handle horizontal rule
        elif line.startswith('---'):
            from reportlab.platypus import HRFlowable
            elements.append(Spacer(1, 5))
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey, spaceBefore=0, spaceAfter=5))
            elements.append(Spacer(1, 5))
            
        # Handle regular paragraphs (like summary)
        elif line.strip() and not line.startswith('<!--'):
            elements.append(Paragraph(line, styles["NormalText"]))
        
        i += 1
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def create_download_links(markdown_text):
    """Create download links for PDF and text versions of the resume."""
    # Extract only the tailored resume part for the download
    tailored_resume_only = extract_tailored_resume(markdown_text)
    
    # Create PDF download link
    pdf_buffer = markdown_to_pdf(tailored_resume_only, "Tailored_Resume.pdf")
    pdf_b64 = base64.b64encode(pdf_buffer.read()).decode()
    pdf_link = f'<a href="data:application/pdf;base64,{pdf_b64}" download="Tailored_Resume.pdf" class="download-button" style="text-decoration:none; padding:10px 15px; background-color:#4CAF50; color:white; border-radius:4px; margin-right:10px;">📥 Download as PDF</a>'
    
    # Create text download link
    text_buffer = BytesIO()
    text_buffer.write(tailored_resume_only.encode("utf-8"))
    text_buffer.seek(0)
    text_b64 = base64.b64encode(text_buffer.read()).decode()
    text_link = f'<a href="data:text/plain;base64,{text_b64}" download="Tailored_Resume.txt" class="download-button" style="text-decoration:none; padding:10px 15px; background-color:#2196F3; color:white; border-radius:4px;">📄 Download as Text</a>'
    
    return pdf_link + " " + text_link

# Tab 1: Resume Tailoring
with tab1:
    # Create two columns
    col1, col2 = st.columns([1, 1])

    # Resume upload section
    with col1:
        st.markdown("### 📄 Upload Your Resume")
        uploaded_file = st.file_uploader("Upload PDF resume", type=["pdf"], key="resume_uploader")
        if uploaded_file:
            st.session_state.resume_file = uploaded_file
            st.success(f"✅ Resume `{uploaded_file.name}` uploaded successfully!")

    # Job description section
    with col2:
        st.markdown("### 📋 Paste Job Description")
        job_description = st.text_area(
            "Paste the job description here",
            height=200,
            max_chars=5000,
            key="job_description"
        )

    # Submit button section
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    submit_button = st.button("✨ Generate Tailored Resume")
    if submit_button:
        if not st.session_state.resume_file or not job_description:
            st.warning("⚠️ Please upload a resume and enter the job description before submitting.")
        else:
            st.session_state.processing = True
            
            # Show a spinner while processing
            with st.spinner("Processing your resume..."):
                # Prepare request payload
                bytes_data = st.session_state.resume_file.getvalue()
                files = {"file": (st.session_state.resume_file.name, bytes_data, "application/pdf")}
                data = {"job_description": job_description}
                
                try:
                    response = requests.post(API_ENDPOINT, files=files, data=data)
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Resume tailoring complete!")
                        
                        # Store tailored resume in session state
                        full_content = result.get("tailored_resume", "No tailored resume found.")
                        st.session_state.tailored_resume_text = full_content
                        
                        # Split the content into extraction summary and tailored resume
                        parts = full_content.split("# TAILORED RESUME")
                        if len(parts) > 1:
                            extraction_summary = parts[0]
                            tailored_resume = "# TAILORED RESUME" + parts[1]
                        else:
                            extraction_summary = ""
                            tailored_resume = full_content
                        
                        # Display extraction summary in an expandable section
                        with st.expander("👁️ View Extraction Summary", expanded=False):
                            st.markdown(extraction_summary)
                        
                        # Display the tailored resume
                        st.markdown("### Your Tailored Resume")
                        st.markdown(tailored_resume)
                        
                        # Create download links - only for the tailored resume part
                        st.markdown(create_download_links(full_content), unsafe_allow_html=True)
                        
                    else:
                        st.error(f"🚨 Error processing request. Status code: {response.status_code}")
                        if response.text:
                            st.error(f"Error details: {response.text}")
                except Exception as e:
                    st.error(f"🚨 Exception occurred: {str(e)}")
            
            st.session_state.processing = False
    st.markdown("</div>", unsafe_allow_html=True)

# Tab 2: Chat Functionality
with tab2:
    st.markdown("### 💬 Chat with our AI Assistant")
    st.markdown("Ask questions about resume preparation, job applications, or career advice.")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        # Display previous messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 10px;'><strong>You:</strong> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin-bottom: 10px;'><strong>AI Assistant:</strong> {message['content']}</div>", unsafe_allow_html=True)
    
    # Chat input
    user_input = st.text_input("Type your message here...", key="user_input")
    
    # Send button
    if st.button("Send", key="send_button"):
        if user_input:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Send request to chat endpoint
            try:
                payload = {
                    "message": user_input,
                    "history": st.session_state.messages[:-1]  # Send previous messages as context
                }
                
                with st.spinner("Thinking..."):
                    response = requests.post(CHAT_ENDPOINT, json=payload)
                    
                    if response.status_code == 200:
                        result = response.json()
                        assistant_response = result.get("response", "I'm sorry, I couldn't process your request.")
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                        
                        # Force rerun to update the UI
                        st.rerun()
                    else:
                        st.error(f"Error in chat response. Status code: {response.status_code}")
            except Exception as e:
                st.error(f"Exception in chat: {str(e)}")
    
    # Clear chat button
    if st.button("Clear Chat", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

# Add footer
st.markdown("---")
st.markdown("© 2025 AI Resume Tailoring System | Powered by Multi-Agent AI")