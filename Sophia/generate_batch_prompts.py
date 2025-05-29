#!/usr/bin/env python3
"""
Script to generate batch API prompts for protein-protein interaction queries.
Reads protein names from data/proteins.csv and creates JSONL format prompts
for vLLM batch API processing.
"""

import argparse
import json
import pandas as pd
import os
from pathlib import Path


def create_system_prompt():
    """
    Create the system prompt for protein interaction queries.
    This could be enhanced with additional context or instructions.
    """
    return "You are a helpful assistant specialized in molecular biology and protein interactions. When asked about protein interactions, provide clear, concise lists of interacting proteins with brief explanations. Focus on generating accurate protein names that are commonly used in databases and literature."


def create_user_prompt(protein_name):
    """
    Create the user prompt for a specific protein.
    
    Args:
        protein_name (str): The name of the protein to query about
        
    Returns:
        str: The formatted user prompt
    """
    base_prompt = (
        "List proteins that might interact with {protein}. "
        "Please provide a simple list of protein names (gene symbols/names) "
        "that could potentially interact with {protein}, along with a brief "
        "reason for each interaction (e.g., forms complex, enzymatic substrate, "
        "signaling pathway, binding partner). "
        "Focus on well-known, documented interactions. "
        "Format your response as: PROTEIN_NAME - brief description of interaction type."
    )
    return base_prompt.format(protein=protein_name)


def generate_batch_request(custom_id, protein_name, model_name="meta-llama/Meta-Llama-3.1-8B-Instruct", max_tokens=1000):
    """
    Generate a single batch request in the required format.
    
    Args:
        custom_id (str): Unique identifier for this request
        protein_name (str): The protein to query about
        model_name (str): The model to use for the request
        max_tokens (int): Maximum tokens to generate
        
    Returns:
        dict: The batch request object
    """
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": create_system_prompt()
                },
                {
                    "role": "user",
                    "content": create_user_prompt(protein_name)
                }
            ],
            "max_tokens": max_tokens
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate batch API prompts for protein-protein interaction queries"
    )
    parser.add_argument(
        "--input-file",
        default="data/proteins.csv",
        help="Path to the proteins CSV file (default: data/proteins.csv)"
    )
    parser.add_argument(
        "--output-file",
        default="protein_interaction_batch_prompts.jsonl",
        help="Output JSONL file path (default: protein_interaction_batch_prompts.jsonl)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per protein to reduce hallucination (default: 3)"
    )
    parser.add_argument(
        "--max-proteins",
        type=int,
        help="Maximum number of proteins to process (for testing)"
    )
    parser.add_argument(
        "--model",
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        help="Model name to use for batch requests"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1000,
        help="Maximum tokens per response (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        return 1
    
    # Read the proteins CSV
    try:
        df = pd.read_csv(args.input_file)
        print(f"Loaded {len(df)} proteins from {args.input_file}")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 1
    
    # Validate that the expected column exists
    if 'search_words' not in df.columns:
        print(f"Error: Expected column 'search_words' not found in {args.input_file}")
        print(f"Available columns: {list(df.columns)}")
        return 1
    
    # Limit proteins if specified
    if args.max_proteins:
        df = df.head(args.max_proteins)
        print(f"Limited to first {args.max_proteins} proteins")
    
    # Generate batch requests
    batch_requests = []
    request_counter = 1
    
    for index, row in df.iterrows():
        protein_name = row['search_words'].strip()
        
        # Skip empty protein names
        if not protein_name:
            continue
            
        # Generate multiple iterations for each protein
        for iteration in range(args.iterations):
            custom_id = f"protein-{protein_name}-iter-{iteration+1}-req-{request_counter}"
            
            batch_request = generate_batch_request(
                custom_id=custom_id,
                protein_name=protein_name,
                model_name=args.model,
                max_tokens=args.max_tokens
            )
            
            batch_requests.append(batch_request)
            request_counter += 1
    
    # Write to JSONL file
    try:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n')
        
        print(f"Successfully generated {len(batch_requests)} batch requests")
        print(f"Output written to: {args.output_file}")
        print(f"Total proteins processed: {len(df)}")
        print(f"Iterations per protein: {args.iterations}")
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 