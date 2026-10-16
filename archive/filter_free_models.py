# Script to filter free models from openrouter-models.csv

import csv
import os

# !!! VERY IMPORTANT NOTE !!!
# This file is currently in the ROOT directory.
# It ideally belongs in a 'scripts' or 'tools' directory.
# Please move it to an appropriate location once the directory structure is resolved.

INPUT_CSV_FILENAME = "openrouter-models.csv"
OUTPUT_TXT_FILENAME = "openrouter-free-models.txt"

def filter_and_save_free_models(input_filename, output_filename):
    """Reads the input CSV, filters for models ending in ':free', and saves their IDs to a TXT file."""
    free_model_ids = []
    input_filepath = os.path.join(os.getcwd(), input_filename)
    output_filepath = os.path.join(os.getcwd(), output_filename)

    try:
        with open(input_filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'id' not in reader.fieldnames:
                print(f"Error: CSV file '{input_filename}' does not contain an 'id' column.")
                return
            
            for row in reader:
                model_id = row.get('id')
                if model_id and model_id.endswith(':free'):
                    free_model_ids.append(model_id)
        
        if not free_model_ids:
            print(f"No models ending with ':free' found in {input_filename}.")
            # Create an empty output file if no free models are found
            with open(output_filepath, 'w', encoding='utf-8') as txtfile:
                txtfile.write("# No models ending with ':free' found.\n")
            print(f"Created empty file (with comment): {output_filepath}")
            return

        with open(output_filepath, 'w', encoding='utf-8') as txtfile:
            for model_id in free_model_ids:
                txtfile.write(model_id + '\n')
        print(f"Successfully saved {len(free_model_ids)} free model IDs to {output_filepath}")

    except FileNotFoundError:
        print(f"Error: Input CSV file '{input_filepath}' not found.")
    except IOError as e:
        print(f"Error reading or writing file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print(f"Filtering free models from {INPUT_CSV_FILENAME}...")
    filter_and_save_free_models(INPUT_CSV_FILENAME, OUTPUT_TXT_FILENAME)

