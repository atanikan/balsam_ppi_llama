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
import time
from collections import defaultdict


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


def read_csv_to_dict(csv_path, col1='col1', col2='col2', score='score'):
    """Read CSV file into dictionary for fast lookups."""
    result = {}
    try:
        with open(csv_path, 'r') as f:
            header = f.readline().strip().split(',')
            col1_idx = header.index(col1)
            col2_idx = header.index(col2)
            score_idx = header.index(score)
            
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > max(col1_idx, col2_idx, score_idx):
                    key = (parts[col1_idx], parts[col2_idx])
                    result[key] = int(parts[score_idx])
        return result
    except Exception as e:
        print(f"Warning: Could not read {csv_path}: {e}")
        return {}


def load_proteins(proteins_csv):
    """Load protein names from CSV."""
    proteins = set()
    try:
        with open(proteins_csv, 'r') as f:
            # Skip header
            next(f)
            for line in f:
                protein = line.strip()
                if protein:
                    proteins.add(protein)
        return proteins
    except Exception as e:
        print(f"Warning: Could not read {proteins_csv}: {e}")
        return set()


def parse_batch_output(batch_file, proteins_set):
    """Parse vLLM batch output and extract protein interactions."""
    interactions = set()
    processed_responses = 0
    
    with open(batch_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                
                # Extract content from vLLM batch response format
                if 'response' in data and 'choices' in data['response']:
                    content = data['response']['choices'][0]['message']['content']
                else:
                    print(f"Warning: Unexpected format at line {line_num}")
                    continue
                
                # Extract mentioned proteins using word boundaries
                mentioned_proteins = set()
                for protein in proteins_set:
                    if re.search(r'\b' + re.escape(protein) + r'\b', content, re.IGNORECASE):
                        mentioned_proteins.add(protein)
                
                # Create pairwise interactions
                proteins_list = list(mentioned_proteins)
                for i in range(len(proteins_list)):
                    for j in range(i+1, len(proteins_list)):
                        interactions.add((proteins_list[i], proteins_list[j]))
                
                processed_responses += 1
                
                if processed_responses % 100 == 0:
                    print(f"Processed {processed_responses:,} responses, found {len(interactions):,} unique interactions")
                    
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON at line {line_num}")
                continue
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")
                continue
    
    return interactions, processed_responses


def validate_interaction(protein1, protein2, big_table_dict, string_dict):
    """Validate interaction and determine edge color."""
    # Check both directions in the databases
    lpkg_score = big_table_dict.get((protein1, protein2), big_table_dict.get((protein2, protein1), -1))
    string_score = string_dict.get((protein1, protein2), string_dict.get((protein2, protein1), -1))
    
    # Apply validation logic from original parallel_dot_construction.py
    if lpkg_score == -1 and string_score == -1:
        return "red", 5.0  # Novel LLM prediction
    elif lpkg_score >= 1 and string_score == 0:
        return "orange", 5.0  # In big_table only
    elif lpkg_score == -1 and string_score > 0:
        return "blue", 2.0  # In string only
    elif lpkg_score > 500 and string_score > 500:
        return "green", 2.0  # High confidence in both
    else:
        return "black", 1.0  # Default


def generate_dot_file(interactions, big_table_dict, string_dict, output_file):
    """Generate DOT file with color-coded edges."""
    print(f"Generating DOT file: {output_file}")
    
    with open(output_file, 'w') as f:
        f.write('digraph G {\n')
        
        edge_count = 0
        for protein1, protein2 in sorted(interactions):
            color, width = validate_interaction(protein1, protein2, big_table_dict, string_dict)
            f.write(f'  "{protein1}" -> "{protein2}" [color={color}, penwidth={width}];\n')
            edge_count += 1
        
        f.write('}\n')
    
    print(f"Generated DOT file with {edge_count:,} edges")


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
    
    start_time = time.time()
    
    print("🧬 vLLM Protein Interaction Parser (Serial)")
    print("=" * 50)
    
    # Load validation databases
    print("📊 Loading validation databases...")
    load_start = time.time()
    big_table_dict = read_csv_to_dict(args.big_table_csv)
    string_dict = read_csv_to_dict(args.string_csv)
    proteins_set = load_proteins(args.proteins_csv)
    load_time = time.time() - load_start
    
    print(f"   Proteins: {len(proteins_set):,}")
    print(f"   Big table entries: {len(big_table_dict):,}")
    print(f"   String entries: {len(string_dict):,}")
    print(f"   Load time: {load_time:.2f}s")
    
    # Parse batch output
    print(f"\n🔍 Parsing batch output: {args.batch_output}")
    parse_start = time.time()
    interactions, processed_responses = parse_batch_output(args.batch_output, proteins_set)
    parse_time = time.time() - parse_start
    
    print(f"   Processed responses: {processed_responses:,}")
    print(f"   Total unique interactions: {len(interactions):,}")
    print(f"   Parse time: {parse_time:.2f}s")
    print(f"   Rate: {processed_responses/parse_time:.1f} responses/sec")
    
    # Generate DOT file
    print(f"\n📝 Generating visualization...")
    dot_start = time.time()
    generate_dot_file(interactions, big_table_dict, string_dict, args.output_dot)
    dot_time = time.time() - dot_start
    
    total_time = time.time() - start_time
    
    print(f"\n🎉 Complete!")
    print(f"   DOT generation time: {dot_time:.2f}s") 
    print(f"   Total execution time: {total_time:.2f}s")
    print(f"   Output: {args.output_dot}")


if __name__ == "__main__":
    exit(main()) 