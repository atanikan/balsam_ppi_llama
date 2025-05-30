#!/usr/bin/env python3
"""
Enhanced parser with optional parallel processing for large LLM batch outputs.
Optimized for CPU-bound text processing tasks using multiprocessing.
"""

import argparse
import json
import pandas as pd
import os
import re
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial
import time


def process_batch_lines(lines_batch, proteins_set):
    """
    Process a batch of lines in parallel.
    
    Args:
        lines_batch: List of (line_number, json_line) tuples
        proteins_set: Set of valid protein names
        
    Returns:
        List of (query_protein, interacting_proteins) tuples
    """
    batch_interactions = []
    
    for line_num, line in lines_batch:
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
            content = None
            if 'response' in response:
                resp = response['response']
                
                # Handle real vLLM format with 'body' layer
                if 'body' in resp and 'choices' in resp['body']:
                    choices = resp['body']['choices']
                    if choices and 'message' in choices[0]:
                        content = choices[0]['message'].get('content', '')
                
                # Fallback to direct format (for test data)
                elif 'choices' in resp:
                    choices = resp['choices']
                    if choices and 'message' in choices[0]:
                        content = choices[0]['message'].get('content', '')
            
            if content:
                # Extract interacting proteins from the content
                interacting_proteins = extract_proteins_from_text(content, proteins_set)
                
                # Filter out self-interactions
                valid_interactions = [p for p in interacting_proteins if p != query_protein]
                
                if valid_interactions:
                    batch_interactions.append((query_protein, valid_interactions))
                        
        except json.JSONDecodeError:
            print(f"Warning: Could not parse line {line_num}")
            continue
        except Exception as e:
            print(f"Warning: Error processing line {line_num}: {e}")
            continue
    
    return batch_interactions


def extract_proteins_from_text(text, proteins_set):
    """
    Extract protein names from LLM response text.
    Optimized version with compiled regex patterns.
    
    Args:
        text (str): LLM response text
        proteins_set (set): Set of valid protein names
        
    Returns:
        list: List of protein names found in the text
    """
    found_proteins = []
    
    # Split text into lines and process each line
    lines = text.split('\n')
    
    # Compiled regex for better performance
    word_pattern = re.compile(r'\b[A-Za-z0-9]+\b')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to extract protein name from various formats
        # Format: "PROTEIN_NAME - description"
        if ' - ' in line:
            potential_protein = line.split(' - ')[0].strip().upper()
            if potential_protein in proteins_set:
                found_proteins.append(potential_protein)
        
        # Look for any words in the line that match our protein set
        words = word_pattern.findall(line)
        for word in words:
            word_upper = word.upper()
            if word_upper in proteins_set and len(word_upper) > 2:  # Avoid very short matches
                found_proteins.append(word_upper)
    
    return list(set(found_proteins))  # Remove duplicates


class ProteinInteractionParserParallel:
    def __init__(self, proteins_csv_path, big_table_csv_path, string_csv_path):
        """
        Initialize the parser with required data files.
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

    def parse_batch_output_parallel(self, batch_output_file, num_workers=None, batch_size=1000):
        """
        Parse the batch output JSONL file using parallel processing.
        
        Args:
            batch_output_file (str): Path to the batch output JSONL file
            num_workers (int): Number of worker processes (default: CPU count)
            batch_size (int): Lines per batch for parallel processing
        """
        if num_workers is None:
            num_workers = min(cpu_count(), 8)  # Cap at 8 to avoid overwhelming
        
        print(f"Parsing batch output using {num_workers} workers with batch size {batch_size}...")
        
        start_time = time.time()
        
        # Read all lines first
        with open(batch_output_file, 'r', encoding='utf-8') as f:
            lines = [(i+1, line) for i, line in enumerate(f)]
        
        total_lines = len(lines)
        print(f"Loaded {total_lines:,} lines, creating batches...")
        
        # Create batches for parallel processing
        batches = []
        for i in range(0, len(lines), batch_size):
            batch = lines[i:i + batch_size]
            batches.append(batch)
        
        print(f"Created {len(batches)} batches for parallel processing...")
        
        # Process batches in parallel
        process_func = partial(process_batch_lines, proteins_set=self.proteins_set)
        
        all_batch_results = []
        processed_batches = 0
        
        with Pool(num_workers) as pool:
            for batch_result in pool.imap(process_func, batches):
                all_batch_results.extend(batch_result)
                processed_batches += 1
                
                if processed_batches % 10 == 0 or processed_batches == len(batches):
                    print(f"Processed {processed_batches}/{len(batches)} batches...")
        
        # Merge results into interactions set
        for query_protein, interacting_proteins in all_batch_results:
            for interacting_protein in interacting_proteins:
                self.interactions.add((query_protein, interacting_protein))
        
        elapsed_time = time.time() - start_time
        print(f"Parallel parsing complete! Found {len(self.interactions):,} unique interactions")
        print(f"Processing time: {elapsed_time:.2f} seconds ({total_lines/elapsed_time:.0f} lines/sec)")

    def parse_batch_output_serial(self, batch_output_file):
        """
        Parse the batch output JSONL file using serial processing (original method).
        """
        print(f"Parsing batch output serially...")
        
        start_time = time.time()
        
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
                    print(f"Processed {processed_lines:,}/{total_lines:,} lines, found {interactions_found:,} interactions")
                
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
                    content = None
                    if 'response' in response:
                        resp = response['response']
                        
                        # Handle real vLLM format with 'body' layer
                        if 'body' in resp and 'choices' in resp['body']:
                            choices = resp['body']['choices']
                            if choices and 'message' in choices[0]:
                                content = choices[0]['message'].get('content', '')
                        
                        # Fallback to direct format (for test data)
                        elif 'choices' in resp:
                            choices = resp['choices']
                            if choices and 'message' in choices[0]:
                                content = choices[0]['message'].get('content', '')
                    
                    if content:
                        # Extract interacting proteins from the content
                        interacting_proteins = extract_proteins_from_text(content, self.proteins_set)
                        
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
        
        elapsed_time = time.time() - start_time
        print(f"Serial parsing complete! Found {len(self.interactions):,} unique interactions")
        print(f"Processing time: {elapsed_time:.2f} seconds ({total_lines/elapsed_time:.0f} lines/sec)")

    def validate_and_generate_dot_content(self, protein1, protein2):
        """Generate DOT file content for an interaction using the color scheme."""
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
            return edge + ' [color=red, penwidth=5.0];\n'
        elif lpkg >= 1 and stri == 0:
            return edge + ' [color=orange, penwidth=5.0];\n'
        elif lpkg == -1 and stri > 0:
            return edge + ' [color=blue, penwidth=2.0];\n'
        elif lpkg > 500 and stri > 500:
            return edge + ' [color=green, penwidth=2.0];\n'
        else:
            return edge + ';\n'

    def generate_dot_file(self, output_file):
        """Generate a DOT file from the extracted interactions."""
        print(f"Generating DOT file with {len(self.interactions):,} unique interactions...")
        
        # Sort interactions for consistent output
        sorted_interactions = sorted(list(self.interactions), key=lambda x: (x[0], x[1]))
        
        # Build entire content in memory first
        dot_content_parts = ['digraph G {']
        
        for i, (protein1, protein2) in enumerate(sorted_interactions):
            if i % 1000 == 0 and i > 0:
                print(f"Processing interaction {i:,}/{len(sorted_interactions):,}")
            
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
        
        # Count interactions by source protein
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
    parser = argparse.ArgumentParser(description='Parse vLLM batch output for protein interactions (with optional parallel processing)')
    parser.add_argument('--batch-output', required=True, help='vLLM batch output JSONL file')
    parser.add_argument('--output-dot', required=True, help='Output DOT file path')
    parser.add_argument('--proteins-csv', default='data/proteins.csv', help='Proteins CSV file')
    parser.add_argument('--big-table-csv', default='data/big_table.csv', help='Big table CSV file')
    parser.add_argument('--string-csv', default='data/string.csv', help='String CSV file')
    parser.add_argument('--parallel', action='store_true', help='Enable parallel processing')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes (default: CPU count, max 8)')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Lines per chunk for parallel processing')
    parser.add_argument('--verbose', action='store_true', help='Print detailed statistics')
    
    args = parser.parse_args()
    
    # Check if required files exist
    for file_path, name in [(args.batch_output, "batch output"), (args.proteins_csv, "proteins CSV")]:
        if not os.path.exists(file_path):
            print(f"Error: {name} file '{file_path}' not found.")
            return 1
    
    # Initialize parser
    try:
        parser_instance = ProteinInteractionParserParallel(args.proteins_csv, args.big_table_csv, args.string_csv)
        print(f"Loaded {len(parser_instance.proteins_set):,} proteins from {args.proteins_csv}")
    except Exception as e:
        print(f"Error initializing parser: {e}")
        return 1
    
    # Parse batch output
    try:
        if args.parallel:
            parser_instance.parse_batch_output_parallel(
                args.batch_output,
                num_workers=args.workers,
                batch_size=args.chunk_size
            )
        else:
            parser_instance.parse_batch_output_serial(args.batch_output)
    except Exception as e:
        print(f"Error parsing batch output: {e}")
        return 1
    
    # Generate DOT file
    try:
        parser_instance.generate_dot_file(args.output_dot)
    except Exception as e:
        print(f"Error generating DOT file: {e}")
        return 1
    
    # Print statistics
    if args.verbose:
        parser_instance.print_statistics()
    
    return 0


if __name__ == "__main__":
    exit(main()) 