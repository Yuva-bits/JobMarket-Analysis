import json

# Load the data
with open('tech_jobs_data.json') as f:
    data = json.load(f)
    
# Print summary
print(f"Total jobs in JSON file: {len(data['jobs'])}")
print(f"First job title: {data['jobs'][0].get('title', 'No title')}")
print(f"Last job title: {data['jobs'][-1].get('title', 'No title')}")
