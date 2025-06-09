import csv
import json
import os
import re
from urllib.parse import urlparse
from collections import defaultdict

def extract_subject_from_url(url):
    """
    Extract the subject from a mammothmemory.net URL.
    Format: https://mammothmemory.net/{subject}/...
    """
    try:
        # Parse the URL and get the path
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # The subject should be the first part after the domain
        if len(path_parts) >= 1 and path_parts[0]:
            return path_parts[0]
        else:
            return 'unknown'
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        return 'unknown'

def process_csv_file(csv_filename):
    """
    Process the CSV file and organize JSON data by subject.
    """
    # Dictionary to store data organized by subject
    subjects_data = defaultdict(list)
    
    try:
        with open(csv_filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                url = row.get('url', '').strip()
                concept_json = row.get('concept_and_mnemonic', '').strip()
                
                if not url or not concept_json:
                    print(f"Skipping row with missing data: {row}")
                    continue
                
                # Extract subject from URL
                subject = extract_subject_from_url(url)
                
                try:
                    # Clean the JSON data - remove markdown code block markers
                    cleaned_json = concept_json.strip()
                    
                    # Remove ```json and ``` markers if present
                    if cleaned_json.startswith('```json'):
                        cleaned_json = cleaned_json[7:]  # Remove ```json
                    elif cleaned_json.startswith('```'):
                        cleaned_json = cleaned_json[3:]   # Remove ```
                    
                    if cleaned_json.endswith('```'):
                        cleaned_json = cleaned_json[:-3]  # Remove trailing ```
                    
                    cleaned_json = cleaned_json.strip()
                    
                    # Parse the cleaned JSON data
                    json_data = json.loads(cleaned_json)
                    
                    # Handle both single objects and arrays
                    if isinstance(json_data, list):
                        # Add all items in the list to the subject
                        subjects_data[subject].extend(json_data)
                    else:
                        # Single object, add it to the list
                        subjects_data[subject].append(json_data)
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON for URL {url}: {e}")
                    continue
    
    except FileNotFoundError:
        print(f"Error: Could not find CSV file '{csv_filename}'")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Create categories directory if it doesn't exist
    categories_dir = 'categories'
    os.makedirs(categories_dir, exist_ok=True)
    
    # Write JSON files for each subject
    for subject, data in subjects_data.items():
        filename = f"{subject}.json"
        filepath = os.path.join(categories_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Created {filepath} with {len(data)} items")
            
        except Exception as e:
            print(f"Error writing file {filepath}: {e}")
    
    # Create the all_subjects.json file organized by category
    all_subjects_data = dict(subjects_data)  # Convert defaultdict to regular dict
    
    try:
        all_subjects_filepath = os.path.join(categories_dir, 'all_subjects.json')
        with open(all_subjects_filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(all_subjects_data, jsonfile, indent=2, ensure_ascii=False)
        
        total_items = sum(len(data) for data in subjects_data.values())
        print(f"Created {all_subjects_filepath} with all {total_items} items organized by category")
        
    except Exception as e:
        print(f"Error writing all_subjects.json file: {e}")
    
    print(f"\nProcessing complete! Created {len(subjects_data)} category files:")
    for subject, data in subjects_data.items():
        print(f"  - {subject}: {len(data)} items")

def main():
    """
    Main function to run the CSV processor.
    Update the filename below to match your CSV file.
    """
    csv_filename = 'cleaned_questions.csv'  # Change this to your actual CSV filename
    
    print(f"Processing CSV file: {csv_filename}")
    print("="*50)
    
    process_csv_file(csv_filename)

if __name__ == "__main__":
    main()