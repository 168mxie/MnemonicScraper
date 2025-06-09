import csv
import json
from typing import List, Dict, Any
import time
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests

load_dotenv()
api_key = os.getenv("API_KEY")
client = OpenAI(
    # This is the default and can be omitted
    api_key=api_key
)

class FlashcardProcessor:
    def __init__(self, client=None):
        """
        Initialize the processor with your client
        """
        if client is None:
            raise ValueError("Client must be provided for API calls")
        self.client = client
    
    def generate_question(self, term: str, definition: str, mnemonic: str = "") -> str:
        """
        Generate an appropriate question for the given term and definition using LLM
        """
        input_data = f"""
Term: "{term}"
Definition: "{definition}"
{f'Mnemonic: "{mnemonic}"' if mnemonic else ''}
"""

        try:
            response = self.client.responses.create(
                model="gpt-4o",
                instructions=f"""
                Given a term and its definition, generate an appropriate question where the definition would be the answer. The term should be present in the question. Imagine the question being the front of a flashcard, with the definition being on the back, where the mnemonic is used to remember the answer to the question.

                Examples:
                - Term: "France", Definition: "Paris" → Question: "What is the capital of France?"
                - Term: "Photosynthesis", Definition: "Process by which plants convert sunlight into energy" → Question: "What is photosynthesis?"
                - Term: "Alberto Giacometti", Definition: "Swiss artist known for creating abstract, tall, slender sculptures" → Question: "Who was Alberto Giacometti?"

                Generate only the question, nothing else. Make it natural and appropriate for a flashcard.
                """,
                input=input_data,
            )
            
            question = response.output_text.strip()
            # Remove quotes if the LLM added them
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]
            print(question)
            return question
            
        except Exception as e:
            print(f"Error generating question for term '{term}': {e}")
            # Fallback question
            return f"What is {term}?"
    
    def process_json_entry(self, json_str: str) -> str:
        """
        Process a single JSON string and add questions to each entry
        """
        # Check if json_str is empty or None
        if not json_str or json_str.strip() == '':
            print("Warning: Empty JSON string found, skipping...")
            return json_str
        
        try:
            # Clean the JSON string - remove any leading/trailing whitespace
            cleaned_json = json_str.strip()
            
            # Remove markdown code block formatting if present
            if cleaned_json.startswith('```json'):
                # Remove ```json from the beginning
                cleaned_json = cleaned_json[7:].strip()
                
            if cleaned_json.endswith('```'):
                # Remove ``` from the end
                cleaned_json = cleaned_json[:-3].strip()
            
            # Check if it starts with expected JSON characters after cleaning
            if not (cleaned_json.startswith('[') or cleaned_json.startswith('{')):
                print(f"Warning: JSON doesn't start with [ or {{, content: {cleaned_json[:100]}...")
                return json_str
            
            # Parse the JSON
            entries = json.loads(cleaned_json)
            
            # Handle case where entries is not a list
            if not isinstance(entries, list):
                print(f"Warning: JSON is not a list, type: {type(entries)}")
                return json_str
            
            # Process each entry
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    print(f"Warning: Entry {i} is not a dictionary, skipping...")
                    continue
                    
                term = entry.get('term', '')
                definition = entry.get('definition', '')
                mnemonic = entry.get('mnemonic', '')
                
                # Skip if no term
                if not term:
                    print(f"Warning: Entry {i} has no term, skipping...")
                    continue
                
                # Skip if no definition (like the "Alberto (first name)" entry)
                if not definition or definition is None:
                    # For name-only entries, create a simple question
                    entry['question'] = f"What is the first name associated with {term.split('(')[0].strip()}?"
                else:
                    # Generate question using LLM
                    question = self.generate_question(term, definition, mnemonic)
                    entry['question'] = question
                
                print(f"  Processed: {term}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            # Return the updated JSON with markdown formatting preserved
            updated_json = json.dumps(entries, indent=4)  # Use 4 spaces like original
            return f"```json\n{updated_json}\n```"
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"Problematic JSON content (first 200 chars): {json_str[:200]}")
            return json_str  # Return original if parsing fails
        except Exception as e:
            print(f"Error processing entry: {e}")
            return json_str
    
    def process_csv_file(self, input_file: str, output_file: str):
        """
        Process the entire CSV file
        """
        processed_rows = []
        total_rows = 0
        processed_count = 0
        error_count = 0
        
        try:
            # First pass: count total rows
            with open(input_file, 'r', encoding='utf-8') as file:
                total_rows = sum(1 for _ in csv.reader(file))
            
            # Second pass: process rows
            with open(input_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                
                for row_num, row in enumerate(reader, 1):
                    print(f"Processing row {row_num}/{total_rows}...")
                    
                    if len(row) >= 2:
                        url = row[0]
                        concept_and_mnemonic = row[1]
                        
                        # Check if second column is empty
                        if not concept_and_mnemonic or concept_and_mnemonic.strip() == '':
                            print(f"  Row {row_num}: Empty concept_and_mnemonic, keeping as-is")
                            processed_rows.append(row)
                            continue
                        
                        # Process the JSON in the second column
                        updated_json = self.process_json_entry(concept_and_mnemonic)
                        
                        # Check if processing was successful (JSON changed)
                        if updated_json != concept_and_mnemonic:
                            processed_count += 1
                            print(f"  Row {row_num}: Successfully processed")
                        else:
                            error_count += 1
                            print(f"  Row {row_num}: No changes made (likely error)")
                        
                        # Create new row with updated JSON
                        new_row = [url, updated_json] + row[2:] if len(row) > 2 else [url, updated_json]
                        processed_rows.append(new_row)
                    else:
                        # Keep row as-is if it doesn't have the expected format
                        print(f"  Row {row_num}: Insufficient columns, keeping as-is")
                        processed_rows.append(row)
            
            # Write the processed data to output file
            with open(output_file, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(processed_rows)
            
            print(f"\nProcessing complete!")
            print(f"Total rows: {total_rows}")
            print(f"Successfully processed: {processed_count}")
            print(f"Errors/skipped: {error_count}")
            print(f"Output saved to {output_file}")
            
        except FileNotFoundError:
            print(f"Input file '{input_file}' not found.")
        except Exception as e:
            print(f"Error processing CSV file: {e}")


# Usage example
def main():
    """
    Example usage of the FlashcardProcessor
    """
    # Initialize your client here
    # client = YourClientClass()  # Replace with your actual client
    
    # Initialize processor with your client
    processor = FlashcardProcessor(client)
    
    # Process the CSV file
    input_file = "cleaned.csv"  # Your input CSV file
    output_file = "cleaned_questions.csv"  # Output file
    
    processor.process_csv_file(input_file, output_file)
    
    print("Please configure your client before running the processor")

if __name__ == "__main__":
    # Before running, make sure to:
    # 1. Initialize your client properly
    # 2. Update the input_file and output_file paths
    
    main()