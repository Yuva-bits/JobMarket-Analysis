# Populating Neo4j Database from Jooble

This guide explains how to fetch job data from the Jooble API, process it, and load it into a Neo4j database for use with the Job RAG system.

## Prerequisites

1. **Python 3.8+**
2. **Neo4j Database**: Running locally or in the cloud
3. **Jooble API key**: Available from Jooble for developers (example key in the `test.py` file)
4. **Environment Setup**: Configure your `.env` file with Neo4j connection details

## Environment Setup

Create a `.env` file with the following variables:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
HUGGINGFACEHUB_API_TOKEN=your_huggingface_token
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/your-username/jobextraction.git
cd jobextraction
```

2. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Populating the Neo4j Database

### Option 1: Using the pipeline script

The easiest way to populate the Neo4j database is to use the provided pipeline script:

```bash
python jooble_to_neo4j.py
```

This script will:

1. Fetch jobs from the Jooble API
2. Process them with the job extraction model
3. Load the data into Neo4j

### Option 2: Step-by-step process

Alternatively, you can run the process step by step:

#### Step 1: Fetch jobs from Jooble

This will fetch job listings from Jooble and save them to `tech_jobs_data.json`:

```bash
python test.py
```

#### Step 2: Process jobs with the extraction model

This will process the job listings and extract structured information into a SQLite database (`jooble_jobs.db`):

```bash
# If not already processed by test.py
python job_extraction_model.py
```

#### Step 3: Build Neo4j graph from SQLite database

This will build a Neo4j graph from the processed job data:

```bash
python build_neo4j_graph.py
```

## Modifying Search Parameters

To modify the job search parameters (keywords, locations, etc.), edit the `test.py` file:

```python
# Define technical keywords to search for
tech_keywords = [
    "software engineer",
    "developer",
    "data scientist",
    "full stack",
    "devops",
    "cloud engineer",
    "machine learning"
]

# Define locations to search in
locations = ["", "Remote", "Switzerland"]  # Empty string means any location
```

## Verifying the Data

After populating the Neo4j database, you can verify the data using:

```bash
python check_neo4j.py
```

## Using the RAG System

Once the Neo4j database is populated, you can use the RAG system to query job information:

```bash
python job_rag_system.py
```

## Troubleshooting

### Common Issues

1. **Neo4j Connection Issues**: 
   - Verify Neo4j is running
   - Check your credentials in the `.env` file
   - Ensure your Neo4j database allows bolt connections

2. **Jooble API Issues**:
   - Check if the API key in `test.py` is valid
   - Be aware of rate limits when making multiple requests

3. **spaCy Model Issues**:
   - If you encounter issues with spaCy models, try installing them manually:
     ```bash
     python -m spacy download en_core_web_md
     ```

4. **Python Dependencies**:
   - If you encounter import errors, verify all dependencies are installed:
     ```bash
     pip install -r requirements.txt
     ```

## Advanced: Customizing the Extraction Process

To customize how job data is extracted and processed, you can modify:

1. `job_extraction_model.py` - For changing how job data is parsed and structured
2. `build_neo4j_graph.py` - For changing how data is loaded into Neo4j
3. `job_rag_system.py` - For changing how the RAG system queries and processes data 