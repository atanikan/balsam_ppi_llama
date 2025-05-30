#!/usr/bin/env python3
"""
Benchmark script to compare performance of serial vs parallel parsers.
Tests different data sizes to find the crossover point where parallel processing becomes beneficial.
"""

import time
import os
import subprocess
import argparse
import json
from pathlib import Path


def run_parser(parser_script, batch_file, output_file, use_parallel=False, workers=None):
    """
    Run a parser and measure execution time.
    
    Args:
        parser_script (str): Path to parser script
        batch_file (str): Input batch file
        output_file (str): Output DOT file
        use_parallel (bool): Whether to use parallel processing
        workers (int): Number of workers for parallel processing
        
    Returns:
        tuple: (execution_time_seconds, success)
    """
    cmd = [
        "python", parser_script,
        "--batch-output", batch_file,
        "--output-dot", output_file,
        "--verbose"
    ]
    
    if use_parallel:
        cmd.extend(["--parallel"])
        if workers:
            cmd.extend(["--workers", str(workers)])
    
    print(f"Running: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        if result.returncode == 0:
            # Extract statistics from output
            output_lines = result.stdout.split('\n')
            stats = {}
            for line in output_lines:
                if "Total unique interactions:" in line:
                    stats['interactions'] = int(line.split(':')[1].strip().replace(',', ''))
                elif "Processing time:" in line and "lines/sec" in line:
                    parts = line.split()
                    stats['processing_time'] = float(parts[2])
                    stats['lines_per_sec'] = float(parts[4].replace('(', '').replace(')', ''))
            
            return execution_time, True, stats
        else:
            print(f"Error: {result.stderr}")
            return execution_time, False, {}
            
    except subprocess.TimeoutExpired:
        print("Parser timed out after 5 minutes")
        return 300, False, {}
    except Exception as e:
        print(f"Error running parser: {e}")
        return 0, False, {}


def generate_test_data(num_proteins, iterations, output_file):
    """Generate test data using the fake output generator."""
    cmd = [
        "python", "Sophia/test/generate_fake_outputs.py",
        "--num-proteins", str(num_proteins),
        "--iterations", str(iterations),
        "--output-file", output_file
    ]
    
    print(f"Generating test data: {num_proteins} proteins x {iterations} iterations")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        # Count lines in generated file
        with open(output_file, 'r') as f:
            lines = sum(1 for _ in f)
        return lines
    else:
        print(f"Error generating test data: {result.stderr}")
        return 0


def run_benchmark():
    """Run comprehensive benchmark comparing serial vs parallel parsers."""
    
    # Test configurations: (proteins, iterations, description)
    test_configs = [
        (10, 2, "Small (20 responses)"),
        (25, 3, "Medium (75 responses)"),
        (50, 3, "Large (150 responses)"),
        (100, 3, "Very Large (300 responses)"),
        (200, 2, "Huge (400 responses)")
    ]
    
    results = []
    
    print("="*80)
    print("PROTEIN PARSER BENCHMARK")
    print("="*80)
    
    for proteins, iterations, description in test_configs:
        print(f"\n📊 Testing {description}")
        print("-" * 60)
        
        # Generate test data
        test_file = f"Sophia/test/benchmark_{proteins}p_{iterations}i.jsonl"
        lines = generate_test_data(proteins, iterations, test_file)
        
        if lines == 0:
            print(f"❌ Failed to generate test data for {description}")
            continue
        
        print(f"Generated {lines:,} lines of test data")
        
        # Test serial parser
        print("\n🔄 Testing serial parser...")
        serial_time, serial_success, serial_stats = run_parser(
            "Sophia/parse_llm_output.py",
            test_file,
            f"Sophia/test/benchmark_serial_{proteins}p.dot"
        )
        
        # Test parallel parser (serial mode)
        print("\n🔄 Testing parallel parser (serial mode)...")
        parallel_serial_time, parallel_serial_success, parallel_serial_stats = run_parser(
            "Sophia/parse_llm_output_parallel.py",
            test_file,
            f"Sophia/test/benchmark_parallel_serial_{proteins}p.dot"
        )
        
        # Test parallel parser (parallel mode with different worker counts)
        parallel_results = []
        for workers in [2, 4, 8]:
            print(f"\n🚀 Testing parallel parser ({workers} workers)...")
            parallel_time, parallel_success, parallel_stats = run_parser(
                "Sophia/parse_llm_output_parallel.py",
                test_file,
                f"Sophia/test/benchmark_parallel_{workers}w_{proteins}p.dot",
                use_parallel=True,
                workers=workers
            )
            
            parallel_results.append({
                'workers': workers,
                'time': parallel_time,
                'success': parallel_success,
                'stats': parallel_stats
            })
        
        # Find best parallel result
        best_parallel = min(parallel_results, key=lambda x: x['time'] if x['success'] else float('inf'))
        
        # Store results
        result = {
            'config': description,
            'proteins': proteins,
            'iterations': iterations,
            'lines': lines,
            'serial': {
                'time': serial_time,
                'success': serial_success,
                'stats': serial_stats
            },
            'parallel_serial': {
                'time': parallel_serial_time,
                'success': parallel_serial_success,
                'stats': parallel_serial_stats
            },
            'best_parallel': best_parallel,
            'all_parallel': parallel_results
        }
        
        results.append(result)
        
        # Clean up test files
        for f in [test_file] + [f"Sophia/test/benchmark_*_{proteins}p*.dot"]:
            if os.path.exists(f):
                os.remove(f)
    
    # Print summary
    print("\n" + "="*80)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*80)
    
    print(f"{'Config':<20} {'Lines':<8} {'Serial':<10} {'Par(Serial)':<12} {'Best Par':<12} {'Speedup':<10}")
    print("-" * 80)
    
    for result in results:
        if result['serial']['success'] and result['best_parallel']['success']:
            speedup = result['serial']['time'] / result['best_parallel']['time']
            speedup_str = f"{speedup:.2f}x"
            
            if speedup > 1.1:
                speedup_str += " 🚀"
            elif speedup < 0.9:
                speedup_str += " 🐌"
            else:
                speedup_str += " ≈"
        else:
            speedup_str = "N/A"
        
        print(f"{result['config']:<20} {result['lines']:<8,} "
              f"{result['serial']['time']:<10.2f} "
              f"{result['parallel_serial']['time']:<12.2f} "
              f"{result['best_parallel']['time']:<12.2f} "
              f"{speedup_str:<10}")
    
    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    print("-" * 40)
    
    crossover_point = None
    for result in results:
        if (result['serial']['success'] and result['best_parallel']['success'] and
            result['best_parallel']['time'] < result['serial']['time'] * 0.9):
            crossover_point = result['lines']
            break
    
    if crossover_point:
        print(f"✅ Parallel processing becomes beneficial at ~{crossover_point:,} lines")
        print(f"✅ Use parse_llm_output.py for < {crossover_point:,} lines")
        print(f"✅ Use parse_llm_output_parallel.py --parallel for >= {crossover_point:,} lines")
    else:
        print("⚠️  Serial parser was faster or equivalent for all test sizes")
        print("⚠️  Consider using serial parser for current data sizes")
        print("⚠️  Parallel processing may help with larger datasets")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark serial vs parallel protein interaction parsers"
    )
    parser.add_argument(
        "--output-json",
        help="Save detailed results to JSON file"
    )
    
    args = parser.parse_args()
    
    # Check if required files exist
    if not os.path.exists("Sophia/parse_llm_output.py"):
        print("Error: Sophia/parse_llm_output.py not found")
        return 1
    
    if not os.path.exists("Sophia/parse_llm_output_parallel.py"):
        print("Error: Sophia/parse_llm_output_parallel.py not found")
        return 1
    
    if not os.path.exists("Sophia/test/generate_fake_outputs.py"):
        print("Error: Sophia/test/generate_fake_outputs.py not found")
        return 1
    
    # Run benchmark
    results = run_benchmark()
    
    # Save detailed results if requested
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to {args.output_json}")
    
    return 0


if __name__ == "__main__":
    exit(main()) 