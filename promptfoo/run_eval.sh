#!/bin/bash
# Helper script to run promptfoo evaluations with .env file

# Load .env file
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

# Run promptfoo with all arguments passed to this script
promptfoo eval -c configs/seo_writing.yaml  --output results/seo_writing_results.html --env-file .env
promptfoo eval -c configs/seo_writing.yaml  --output results/seo_writing_results.json --env-file .env

promptfoo eval -c configs/basic_text_quick.yaml  --output results/basic_text_quick_results.html --env-file .env
promptfoo eval -c configs/basic_text_quick.yaml  --output results/basic_text_quick_results.json --env-file .env

promptfoo eval -c configs/basic_text.yaml  --output results/basic_text_results.html --env-file .env
promptfoo eval -c configs/basic_text.yaml  --output results/basic_text_results.json --env-file .env

promptfoo eval -c configs/code_generation.yaml  --output results/code_generation_results.html --env-file .env
promptfoo eval -c configs/code_generation.yaml  --output results/code_generation_results.json --env-file .env

promptfoo eval -c configs/reasoning.yaml  --output results/reasoning_results.html --env-file .env
promptfoo eval -c configs/reasoning.yaml  --output results/reasoning_results.json --env-file .env

