#!/usr/bin/env python3
"""
Core benchmark that tests parsing algorithms directly, isolating the performance
differences between serial and parallel approaches.
"""

import time
import json
import re
import multiprocessing
from functools import partial
from collections import defaultdict


def create_test_data(num_lines, proteins_per_response=5):
    """Create test data directly in memory."""
    proteins = ['A1BG', 'A1CF', 'A2M', 'AAMP', 'AANAT', 'ABCA1', 'ABCB1', 'ABCC1', 'ACAA1', 'ACAD8']
    
    test_lines = []
    for i in range(num_lines):
        query_protein = proteins[i % len(proteins)]
        
        # Create protein interaction content
        other_proteins = [p for p in proteins if p != query_protein][:proteins_per_response]
        content = f"Proteins that interact with {query_protein}:\n"
        content += "\n".join([f"- {p} - interaction type" for p in other_proteins])
        
        # Create vLLM response format
        response = {
            "custom_id": f"protein-{query_protein}-iter-{i % 3 + 1}-req-{i+1}",
            "response": {
                "choices": [{
                    "message": {"content": content}
                }]
            }
        }
        
        test_lines.append(json.dumps(response))
    
    return test_lines, set(proteins)


def parse_serial_algorithm(lines, proteins_set):
    """Serial parsing algorithm from parse_llm_output.py."""
    interactions = set()
    processed = 0
    
    for line in lines:
        try:
            data = json.loads(line)
            
            if 'response' in data and 'choices' in data['response']:
                content = data['response']['choices'][0]['message']['content']
                
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
                
                processed += 1
                        
        except Exception:
            continue
    
    return interactions, processed


def parse_parallel_chunk(lines_chunk, proteins_set):
    """Process a chunk of lines for parallel processing."""
    chunk_interactions = []
    
    for line in lines_chunk:
        try:
            data = json.loads(line)
            
            # Extract query protein from custom_id
            custom_id = data.get('custom_id', '')
            if not custom_id.startswith('protein-'):
                continue
                
            parts = custom_id.split('-')
            if len(parts) < 4:
                continue
            query_protein = parts[1].upper()
            
            # Extract content
            if 'response' in data and 'choices' in data['response']:
                content = data['response']['choices'][0]['message']['content']
                
                # Extract interacting proteins
                interacting_proteins = []
                for protein in proteins_set:
                    if protein != query_protein and re.search(r'\b' + re.escape(protein) + r'\b', content, re.IGNORECASE):
                        interacting_proteins.append(protein)
                
                if interacting_proteins:
                    chunk_interactions.append((query_protein, interacting_proteins))
                    
        except Exception:
            continue
    
    return chunk_interactions


def parse_parallel_algorithm(lines, proteins_set, num_workers=4, chunk_size=1000):
    """Parallel parsing algorithm from parse_llm_output_parallel.py."""
    
    # Create chunks
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunks.append(lines[i:i + chunk_size])
    
    # Process in parallel
    process_func = partial(parse_parallel_chunk, proteins_set=proteins_set)
    
    all_interactions = []
    with multiprocessing.Pool(num_workers) as pool:
        for chunk_result in pool.map(process_func, chunks):
            all_interactions.extend(chunk_result)
    
    # Convert to pairwise interactions
    interactions = set()
    for query_protein, interacting_proteins in all_interactions:
        for target_protein in interacting_proteins:
            interactions.add((query_protein, target_protein))
    
    return interactions, len(all_interactions)


def benchmark_parsing_algorithms():
    """Benchmark the core parsing algorithms."""
    
    print("🔬 CORE PARSING ALGORITHM BENCHMARK")
    print("=" * 60)
    print("Testing parsing algorithms in isolation")
    print()
    
    # Test different scales
    test_sizes = [
        (100, "Small"),
        (500, "Medium"),
        (1000, "Large"),
        (2000, "Very Large"),
        (5000, "Massive")
    ]
    
    results = []
    
    for num_lines, size_name in test_sizes:
        print(f"🧪 Testing {size_name}: {num_lines:,} lines")
        print("-" * 40)
        
        # Create test data
        print("   📝 Generating test data...")
        test_lines, proteins_set = create_test_data(num_lines)
        print(f"   📊 {len(test_lines):,} lines, {len(proteins_set)} proteins")
        
        # Test serial algorithm
        print("   ⚡ Testing serial algorithm...")
        start_time = time.time()
        serial_interactions, serial_processed = parse_serial_algorithm(test_lines, proteins_set)
        serial_time = time.time() - start_time
        
        print(f"      Time: {serial_time:.3f}s")
        print(f"      Processed: {serial_processed:,}")
        print(f"      Interactions: {len(serial_interactions):,}")
        print(f"      Rate: {serial_processed/serial_time:.1f} items/sec")
        
        # Test parallel algorithm (only for larger datasets)
        if num_lines >= 500:
            workers = min(4, multiprocessing.cpu_count())
            print(f"   🔄 Testing parallel algorithm ({workers} workers)...")
            start_time = time.time()
            parallel_interactions, parallel_processed = parse_parallel_algorithm(
                test_lines, proteins_set, num_workers=workers
            )
            parallel_time = time.time() - start_time
            
            print(f"      Time: {parallel_time:.3f}s")
            print(f"      Processed: {parallel_processed:,}")
            print(f"      Interactions: {len(parallel_interactions):,}")
            print(f"      Rate: {parallel_processed/parallel_time:.1f} items/sec")
            
            # Calculate speedup
            if serial_time > 0 and parallel_time > 0:
                speedup = serial_time / parallel_time
                if speedup > 1.1:
                    speedup_str = f"{speedup:.2f}x faster 🚀"
                elif speedup < 0.9:
                    speedup_str = f"{1/speedup:.2f}x slower 🐌"
                else:
                    speedup_str = "~same speed ≈"
            else:
                speedup_str = "N/A"
            
            print(f"      Speedup: {speedup_str}")
            
        else:
            parallel_time = 0
            parallel_interactions = set()
            parallel_processed = 0
            speedup_str = "Not tested (too small)"
        
        results.append({
            'size': size_name,
            'lines': num_lines,
            'serial_time': serial_time,
            'parallel_time': parallel_time,
            'serial_interactions': len(serial_interactions),
            'parallel_interactions': len(parallel_interactions),
            'speedup': speedup_str
        })
        
        print()
    
    # Summary table
    print("=" * 80)
    print("CORE ALGORITHM BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'Size':<12} {'Lines':<8} {'Serial(s)':<10} {'Parallel(s)':<12} {'S.Ints':<8} {'P.Ints':<8} {'Speedup':<15}")
    print("-" * 80)
    
    for r in results:
        parallel_str = f"{r['parallel_time']:.3f}" if r['parallel_time'] > 0 else "N/A"
        print(f"{r['size']:<12} {r['lines']:<8} {r['serial_time']:<10.3f} {parallel_str:<12} "
              f"{r['serial_interactions']:<8} {r['parallel_interactions']:<8} {r['speedup']:<15}")
    
    # Analysis
    print("\n🔍 ANALYSIS:")
    print("-" * 40)
    
    crossover_found = False
    for r in results:
        if "faster" in r['speedup'] and "🚀" in r['speedup']:
            print(f"✅ Parallel becomes beneficial at {r['size']} size ({r['lines']:,} lines)")
            crossover_found = True
            break
    
    if not crossover_found:
        print("⚠️  Parallel processing shows limited benefit for these data sizes")
        print("⚠️  Serial algorithm may be sufficient for typical workloads")
    
    print("\n💡 Key insights:")
    print("   • Small datasets: Serial algorithm dominates due to no setup overhead")
    print("   • Large datasets: Parallel may help if CPU-bound processing outweighs overhead")
    print("   • Real performance depends on I/O, memory, and actual CSV database sizes")


if __name__ == "__main__":
    benchmark_parsing_algorithms() 