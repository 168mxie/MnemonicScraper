import csv
import json
import os
def add_mnemonic_counts(input_csv, output_csv):
    count = 1  # Start counting from 1
    updated_rows = []

    with open(input_csv, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            json_blob = row['concept_and_mnemonic']
            try:
                # Strip triple backticks and optional 'json'
                cleaned = json_blob.strip().strip('```').replace('json', '').strip()
                data = json.loads(cleaned)

                if isinstance(data, list):
                    for item in data:
                        item['count'] = count
                        count += 1
                    # Rewrap JSON with code fence
                    row['concept_and_mnemonic'] = f'```json\n{json.dumps(data, indent=4)}\n```'
                    updated_rows.append(row)
                else:
                    print(f"⚠️ Unexpected JSON format at {row['url']}")
            except Exception as e:
                print(f"❌ Failed to parse JSON at {row['url']}: {e}")
                updated_rows.append(row)  # Optionally keep row untouched

    # Write updated rows to a new CSV
    with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['url', 'concept_and_mnemonic']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in updated_rows:
            writer.writerow(row)

    print(f"\n✅ Done! {count - 1} mnemonics indexed and written to: {output_csv}")

script_dir = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(script_dir, "mammoth_memory_main_mnemonics.csv")
# Example usage
add_mnemonic_counts(filename, "mammoth_memory_with_counts.csv")