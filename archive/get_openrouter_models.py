# Script to fetch available models from OpenRouter API and save to CSV

import requests
import csv
import os

# !!! VERY IMPORTANT NOTE !!!
# This file is currently in the ROOT directory due to issues creating files in subdirectories.
# It ideally belongs in a 'scripts' or 'tools' directory, or within the 'llm_evaluation' feature 
# if it's considered part of that feature's tooling.
# Please move it to an appropriate location once the directory structure is resolved.

OPENROUTER_MODELS_API_URL = "https://openrouter.ai/api/v1/models"
OUTPUT_CSV_FILENAME = "openrouter-models.csv"

def fetch_models():
    """Fetches the list of models from the OpenRouter API."""
    try:
        response = requests.get(OPENROUTER_MODELS_API_URL)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()  # Returns a dictionary
    except requests.exceptions.RequestException as e:
        print(f"Error fetching models from OpenRouter: {e}")
        return None

def save_models_to_csv(models_data, filename):
    """Saves model data to a CSV file."""
    if not models_data or 'data' not in models_data or not isinstance(models_data['data'], list):
        print("No model data to save or data is in unexpected format.")
        return

    models_list = models_data['data']
    
    # Define the headers for the CSV file
    # We'll try to get common useful fields. The API might return more.
    headers = ['id', 'name', 'description', 'pricing_prompt', 'pricing_completion', 'context_length', 'top_provider_name']

    # Create a path in the current directory for the CSV file
    filepath = os.path.join(os.getcwd(), filename)

    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            for model in models_list:
                # Prepare a row with data, handling potentially missing keys gracefully
                row = {
                    'id': model.get('id'),
                    'name': model.get('name'),
                    'description': model.get('description'),
                    'pricing_prompt': model.get('pricing', {}).get('prompt'),
                    'pricing_completion': model.get('pricing', {}).get('completion'),
                    'context_length': model.get('context_length'),
                    'top_provider_name': model.get('top_provider', {}).get('name')
                }
                writer.writerow(row)
        print(f"Successfully saved model list to {filepath}")
    except IOError as e:
        print(f"Error writing to CSV file {filepath}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while writing to CSV: {e}")

if __name__ == "__main__":
    print(f"Fetching available models from {OPENROUTER_MODELS_API_URL}...")
    models_data = fetch_models()
    if models_data:
        save_models_to_csv(models_data, OUTPUT_CSV_FILENAME)
    else:
        print("Could not fetch model data.")

