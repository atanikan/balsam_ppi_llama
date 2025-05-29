#!/usr/bin/env python3
"""
Parser script to process LLM batch output and generate protein interaction network.
Reads LLM responses, extracts protein interactions, validates against proteins.csv,
and generates a DOT file using the color scheme from parallel_dot_construction.py.
"""

import argparse
import json
import pandas as pd
import os
import re
from pathlib import Path


class ProteinInteractionParser:
    def __init__(self, proteins_csv_path, big_table_csv_path, string_csv_path):
        """
        Initialize the parser with required data files.
        
        Args:
            proteins_csv_path (str): Path to proteins.csv
            big_table_csv_path (str): Path to big_table.csv
            string_csv_path (str): Path to string.csv
        """
        self.proteins_set = self.load_proteins(proteins_csv_path)
        
        # Pre-process CSV files into dictionaries for faster lookup
        print("Loading and indexing big_table.csv...")
        self.bt_dict = self.load_big_table_dict(big_table_csv_path) if os.path.exists(big_table_csv_path) else {}
        
        print("Loading and indexing string.csv...")
        self.st_dict, self.st_proteins = self.load_string_dict(string_csv_path) if os.path.exists(string_csv_path) else ({}, set())
        
        self.interactions = set()
        
    def load_proteins(self, proteins_csv_path):
        """Load protein names from proteins.csv into a set for fast lookup."""
        df = pd.read_csv(proteins_csv_path)
        return set(df['search_words'].str.strip().str.upper())
    
    def load_big_table_dict(self, big_table_csv_path):
        """Load big_table.csv into a dictionary for O(1) lookup."""
        bt_dict = {}
        if os.path.exists(big_table_csv_path):
            bt = pd.read_csv(big_table_csv_path)
            for _, row in bt.iterrows():
                key = (row['col1'], row['col2'])
                bt_dict[key] = int(row['score'])
        return bt_dict
    
    def load_string_dict(self, string_csv_path):
        """Load string.csv into a dictionary for O(1) lookup and protein set."""
        st_dict = {}
        st_proteins = set()
        if os.path.exists(string_csv_path):
            st = pd.read_csv(string_csv_path)
            for _, row in st.iterrows():
                key = (row['col1'], row['col2'])
                st_dict[key] = int(row['score'])
                st_proteins.add(row['col1'])
                st_proteins.add(row['col2'])
        return st_dict, st_proteins
    
    def extract_proteins_from_text(self, text):
        """
        Extract protein names from LLM response text.
        
        Args:
            text (str): LLM response text
            
        Returns:
            list: List of protein names found in the text
        """
        # Look for protein names that match our known proteins
        found_proteins = []
        
        # Split text into lines and process each line
        lines = text.split('\n')
        for line in lines:
            # Look for patterns like "PROTEIN_NAME - description" or just protein names
            line = line.strip()
            if not line:
                continue
                
            # Try to extract protein name from various formats
            # Format: "PROTEIN_NAME - description"
            if ' - ' in line:
                potential_protein = line.split(' - ')[0].strip().upper()
                if potential_protein in self.proteins_set:
                    found_proteins.append(potential_protein)
            
            # Look for any words in the line that match our protein set
            words = re.findall(r'\b[A-Za-z0-9]+\b', line)
            for word in words:
                word_upper = word.upper()
                if word_upper in self.proteins_set and len(word_upper) > 2:  # Avoid very short matches
                    found_proteins.append(word_upper)
        
        return list(set(found_proteins))  # Remove duplicates
    
    def parse_batch_output(self, batch_output_file):
        """
        Parse the batch output JSONL file and extract protein interactions.
        
        Args:
            batch_output_file (str): Path to the batch output JSONL file
        """
        print(f"Parsing batch output from {batch_output_file}...")
        
        # Count lines for progress tracking
        with open(batch_output_file, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
        
        processed_lines = 0
        interactions_found = 0
        
        with open(batch_output_file, 'r', encoding='utf-8') as f:
            for line in f:
                processed_lines += 1
                
                # Progress tracking
                if processed_lines % 1000 == 0 or processed_lines == total_lines:
                    print(f"Processed {processed_lines}/{total_lines} lines, found {interactions_found} interactions")
                
                try:
                    response = json.loads(line.strip())
                    
                    # Extract query protein from custom_id
                    custom_id = response.get('custom_id', '')
                    if not custom_id.startswith('protein-'):
                        continue
                        
                    # Parse custom_id: "protein-PROTEINNAME-iter-X-req-Y"
                    parts = custom_id.split('-')
                    if len(parts) < 4:
                        continue
                    query_protein = parts[1].upper()
                    
                    # Extract response content
                    if 'response' in response and 'choices' in response['response']:
                        choices = response['response'].get('choices', [])
                        if choices and 'message' in choices[0]:
                            content = choices[0]['message'].get('content', '')
                            
                            # Extract interacting proteins from the content
                            interacting_proteins = self.extract_proteins_from_text(content)
                            
                            # Add interactions (excluding self-interactions)
                            initial_count = len(self.interactions)
                            for interacting_protein in interacting_proteins:
                                if interacting_protein != query_protein:
                                    self.interactions.add((query_protein, interacting_protein))
                            
                            # Track new interactions found
                            interactions_found += len(self.interactions) - initial_count
                                    
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line {processed_lines}: {line[:100]}...")
                    continue
                except Exception as e:
                    print(f"Warning: Error processing line {processed_lines}: {e}")
                    continue
        
        print(f"Parsing complete! Found {len(self.interactions)} unique interactions from {total_lines} responses.")
    
    def validate_and_generate_dot_content(self, protein1, protein2):
        """
        Generate DOT file content for an interaction using the color scheme.
        Based on the logic from parallel_dot_construction.py.
        
        Args:
            protein1 (str): Source protein
            protein2 (str): Target protein
            
        Returns:
            str: DOT file edge content with appropriate styling
        """
        edge = f"{protein1} -> {protein2}"
        
        # Default values
        stri = -1
        lpkg = -1
        
        # Check big_table.csv - O(1) lookup
        if (protein1, protein2) in self.bt_dict:
            lpkg = self.bt_dict[(protein1, protein2)]
        
        # Check string.csv
        target = 0
        if protein2 in self.st_proteins:
            target = target + 1

        stri = 0
                
        if target == 0:
            stri = -1
        elif (protein1, protein2) in self.st_dict:
            stri = self.st_dict[(protein1, protein2)]
        else:
            stri = 0
        
        # Apply color scheme based on scores
        if lpkg == -1 and stri == -1:
            return edge + ' [color=red, penwidth=5.0];\n'  # Not found in either
        elif lpkg >= 1 and stri == 0:
            return edge + ' [color=orange, penwidth=5.0];\n'  # Found in big_table only
        elif lpkg == -1 and stri > 0:
            return edge + ' [color=blue, penwidth=2.0];\n'  # Found in string only
        elif lpkg > 500 and stri > 500:
            return edge + ' [color=green, penwidth=2.0];\n'  # High confidence in both
        else:
            return edge + ';\n'  # Default
    
    def generate_dot_file(self, output_file):
        """
        Generate a DOT file from the extracted interactions.
        Build content in memory first for faster IO.
        
        Args:
            output_file (str): Path to the output DOT file
        """
        print(f"Generating DOT file with {len(self.interactions)} unique interactions...")
        
        # Sort interactions for consistent output
        sorted_interactions = sorted(list(self.interactions), key=lambda x: (x[0], x[1]))
        
        # Build entire content in memory first
        dot_content_parts = ['digraph G {']
        
        for i, (protein1, protein2) in enumerate(sorted_interactions):
            if i % 1000 == 0 and i > 0:
                print(f"Processing interaction {i}/{len(sorted_interactions)}")
            
            dot_content = self.validate_and_generate_dot_content(protein1, protein2)
            dot_content_parts.append(dot_content)
        
        dot_content_parts.append('}')
        
        # Write all content at once for faster IO
        full_content = ''.join(dot_content_parts)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"DOT file generated: {output_file}")
    
    def print_statistics(self):
        """Print statistics about the extracted interactions."""
        print("\n" + "="*50)
        print("PROTEIN INTERACTION NETWORK STATISTICS")
        print("="*50)
        
        total_interactions = len(self.interactions)
        unique_proteins = set(p for interaction in self.interactions for p in interaction)
        
        print(f"Total unique interactions: {total_interactions:,}")
        print(f"Unique proteins involved: {len(unique_proteins):,}")
        print(f"Proteins in dataset: {len(self.proteins_set):,}")
        print(f"Coverage: {len(unique_proteins)/len(self.proteins_set)*100:.1f}% of proteins have interactions")
        
        # Count interactions by source protein - more efficient
        source_counts = {}
        target_counts = {}
        
        for protein1, protein2 in self.interactions:
            source_counts[protein1] = source_counts.get(protein1, 0) + 1
            target_counts[protein2] = target_counts.get(protein2, 0) + 1
        
        avg_out = sum(source_counts.values()) / len(source_counts) if source_counts else 0
        avg_in = sum(target_counts.values()) / len(target_counts) if target_counts else 0
        
        print(f"Average outgoing interactions per protein: {avg_out:.2f}")
        print(f"Average incoming interactions per protein: {avg_in:.2f}")
        
        print(f"\nTop 5 proteins by outgoing interactions:")
        for protein, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {protein}: {count:,} interactions")
            
        print(f"\nTop 5 proteins by incoming interactions:")
        for protein, count in sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {protein}: {count:,} interactions")
        
        print("="*50)


def main():
    parser = argparse.ArgumentParser(
        description="Parse LLM batch output and generate protein interaction network DOT file"
    )
    parser.add_argument(
        "--batch-output",
        required=True,
        help="Path to the batch output JSONL file from vLLM"
    )
    parser.add_argument(
        "--proteins-csv",
        default="data/proteins.csv",
        help="Path to proteins.csv file (default: data/proteins.csv)"
    )
    parser.add_argument(
        "--big-table-csv",
        default="data/big_table.csv",
        help="Path to big_table.csv file (default: data/big_table.csv)"
    )
    parser.add_argument(
        "--string-csv",
        default="data/string.csv",
        help="Path to string.csv file (default: data/string.csv)"
    )
    parser.add_argument(
        "--output-dot",
        default="llm_protein_interactions.dot",
        help="Output DOT file path (default: llm_protein_interactions.dot)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed statistics"
    )
    
    args = parser.parse_args()
    
    # Check if required files exist
    for file_path, name in [(args.batch_output, "batch output"), (args.proteins_csv, "proteins CSV")]:
        if not os.path.exists(file_path):
            print(f"Error: {name} file '{file_path}' not found.")
            return 1
    
    # Initialize parser
    try:
        parser = ProteinInteractionParser(args.proteins_csv, args.big_table_csv, args.string_csv)
        print(f"Loaded {len(parser.proteins_set)} proteins from {args.proteins_csv}")
    except Exception as e:
        print(f"Error initializing parser: {e}")
        return 1
    
    # Parse batch output
    try:
        parser.parse_batch_output(args.batch_output)
        print(f"Parsed batch output from {args.batch_output}")
    except Exception as e:
        print(f"Error parsing batch output: {e}")
        return 1
    
    # Generate DOT file
    try:
        parser.generate_dot_file(args.output_dot)
        print(f"Generated DOT file: {args.output_dot}")
    except Exception as e:
        print(f"Error generating DOT file: {e}")
        return 1
    
    # Print statistics
    if args.verbose:
        parser.print_statistics()
    
    return 0


if __name__ == "__main__":
    exit(main()) 