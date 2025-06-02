import csv
import json
import re
import os
def clean_json_field(json_str):
    # Remove triple backtick code block and 'json' marker if present
    cleaned = re.sub(r"^```json\s*|\s*```$", "", json_str.strip(), flags=re.IGNORECASE)
    # Replace double double-quotes with single double-quotes
    cleaned = cleaned.replace('""', '"')
    # Optional: Validate that it's valid JSON
    try:
        json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("⚠️ Invalid JSON detected:", e)
    return cleaned

def reformat_csv(input_path, output_path):
    with open(input_path, newline='', encoding='utf-8') as infile, \
         open(output_path, 'w', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            row['concept_and_mnemonic'] = clean_json_field(row['concept_and_mnemonic'])
            writer.writerow(row)

# Example usage

script_dir = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(script_dir, "mammoth_memory_main_mnemonics.csv")
reformat_csv(filename, 'cleaned_mnemonics.csv')
