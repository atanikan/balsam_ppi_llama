#!/usr/bin/env python3
"""
Generate fake LLM batch outputs for testing the protein interaction parsers.
Creates realistic protein interaction responses in vLLM batch format.
"""

import json
import pandas as pd
import random
import argparse
from datetime import datetime
import os


class FakeLLMOutputGenerator:
    def __init__(self, proteins_csv_path):
        """Initialize with protein dataset."""
        self.proteins_df = pd.read_csv(proteins_csv_path)
        self.all_proteins = self.proteins_df['search_words'].tolist()
        
        # Common protein interaction templates
        self.interaction_templates = [
            "{protein} - forms protein complex",
            "{protein} - enzymatic substrate", 
            "{protein} - binding partner",
            "{protein} - regulatory interaction",
            "{protein} - signaling pathway component",
            "{protein} - co-expression in tissue",
            "{protein} - structural interaction",
            "{protein} - metabolic pathway interaction"
        ]
        
        # Introduction phrases for variety
        self.intro_phrases = [
            "Here are some proteins that are known to interact with {query_protein}:",
            "Based on available data, {query_protein} may interact with:",
            "Proteins that potentially interact with {query_protein} include:",
            "The following proteins have been reported to interact with {query_protein}:",
            "{query_protein} is known to interact with several proteins:",
            "Literature suggests that {query_protein} interacts with:",
        ]
    
    def generate_protein_interactions(self, query_protein, num_interactions=None):
        """Generate fake protein interactions for a query protein."""
        if num_interactions is None:
            num_interactions = random.randint(2, 8)
        
        # Select random proteins for interactions (excluding self)
        available_proteins = [p for p in self.all_proteins if p != query_protein]
        selected_proteins = random.sample(
            available_proteins, 
            min(num_interactions, len(available_proteins))
        )
        
        # Generate interaction descriptions
        interactions = []
        for protein in selected_proteins:
            template = random.choice(self.interaction_templates)
            interaction = template.format(protein=protein)
            interactions.append(interaction)
        
        # Create full response content
        intro = random.choice(self.intro_phrases).format(query_protein=query_protein)
        content = intro + "\n\n" + "\n".join([f"{i+1}. **{interaction}**" for i, interaction in enumerate(interactions)])
        
        # Sometimes add a disclaimer
        if random.random() < 0.3:
            content += "\n\nThese interactions are based on computational predictions and literature mining. Please refer to databases like STRING, BioGRID, or IntAct for experimental validation."
        
        return content
    
    def generate_batch_response(self, custom_id, query_protein, model_name="meta-llama/Meta-Llama-3.1-8B-Instruct"):
        """Generate a single batch response in vLLM format."""
        content = self.generate_protein_interactions(query_protein)
        
        # Calculate approximate token counts
        prompt_tokens = random.randint(150, 200)
        completion_tokens = len(content.split()) * 1.3  # Rough token estimate
        total_tokens = prompt_tokens + completion_tokens
        
        response = {
            "id": f"vllm-{random.randint(100000000000000000000000000000000, 999999999999999999999999999999999):032x}",
            "custom_id": custom_id,
            "response": {
                "id": f"cmpl-{random.randint(100000000000000000000000000000000, 999999999999999999999999999999999):032x}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": content
                        },
                        "logprobs": None,
                        "finish_reason": "stop",
                        "stop_reason": None
                    }
                ],
                "usage": {
                    "prompt_tokens": int(prompt_tokens),
                    "total_tokens": int(total_tokens),
                    "completion_tokens": int(completion_tokens)
                }
            },
            "error": None
        }
        
        return response
    
    def generate_batch_file(self, output_file, num_proteins=50, iterations_per_protein=3):
        """Generate a complete batch output file with multiple proteins and iterations."""
        
        # Select random proteins for testing
        test_proteins = random.sample(self.all_proteins, min(num_proteins, len(self.all_proteins)))
        
        responses = []
        request_counter = 1
        
        for protein in test_proteins:
            for iteration in range(iterations_per_protein):
                custom_id = f"protein-{protein}-iter-{iteration+1}-req-{request_counter}"
                
                response = self.generate_batch_response(custom_id, protein)
                responses.append(response)
                request_counter += 1
        
        # Write to JSONL file
        with open(output_file, 'w', encoding='utf-8') as f:
            for response in responses:
                f.write(json.dumps(response) + '\n')
        
        print(f"Generated {len(responses)} fake responses for {num_proteins} proteins")
        print(f"Output written to: {output_file}")
        print(f"Iterations per protein: {iterations_per_protein}")
        
        return responses


def main():
    parser = argparse.ArgumentParser(
        description="Generate fake LLM batch outputs for testing protein interaction parsers"
    )
    parser.add_argument(
        "--proteins-csv",
        default="data/proteins.csv",
        help="Path to proteins.csv file (default: data/proteins.csv)"
    )
    parser.add_argument(
        "--output-file",
        default="fake_batch_responses.jsonl",
        help="Output JSONL file path (default: fake_batch_responses.jsonl)"
    )
    parser.add_argument(
        "--num-proteins",
        type=int,
        default=20,
        help="Number of proteins to generate responses for (default: 20)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per protein (default: 3)"
    )
    parser.add_argument(
        "--model",
        default="meta-llama/Meta-Llama-3.1-8B-Instruct",
        help="Model name to use in responses (default: meta-llama/Meta-Llama-3.1-8B-Instruct)"
    )
    
    args = parser.parse_args()
    
    # Check if proteins file exists
    if not os.path.exists(args.proteins_csv):
        print(f"Error: Proteins file '{args.proteins_csv}' not found.")
        return 1
    
    try:
        # Initialize generator
        generator = FakeLLMOutputGenerator(args.proteins_csv)
        print(f"Loaded {len(generator.all_proteins)} proteins from {args.proteins_csv}")
        
        # Generate fake batch responses
        generator.generate_batch_file(
            args.output_file,
            num_proteins=args.num_proteins,
            iterations_per_protein=args.iterations
        )
        
        # Show sample content
        print(f"\nSample response content:")
        sample_content = generator.generate_protein_interactions("A1BG")
        print("=" * 50)
        print(sample_content)
        print("=" * 50)
        
    except Exception as e:
        print(f"Error generating fake outputs: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 